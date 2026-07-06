import base64
import logging
import os

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _call_groq(image_paths: list) -> str:
    """Отправляет изображения в Groq API и возвращает текстовый ответ."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    system_prompt = (
        "You are a concise solver. Read the task from the provided images. "
        "Answer ONLY with the final result or a very brief solution. "
        "IMPORTANT: Use the SAME LANGUAGE as the question in the image. "
        "No greetings, no explanations."
    )

    content_parts = [
        {"type": "text", "text": "Solve the task from these images. Give only the answer."}
    ]

    for path in image_paths:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
            content_parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                }
            )

    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content_parts},
        ],
        "temperature": 0.1,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    data = response.json()

    if response.status_code == 200:
        return data["choices"][0]["message"]["content"]

    error_msg = data.get("error", {}).get("message", "Unknown error")
    raise RuntimeError(f"Groq API error: {error_msg}")


def _broadcast_telegram(text: str) -> None:
    """Рассылает сообщение всем активным пользователям из whitelist."""
    from apps.screener.models import WhitelistUser

    active_users = WhitelistUser.objects.filter(is_active=True).values_list(
        "telegram_id", flat=True
    )

    bot_token = settings.TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    for telegram_id in active_users:
        try:
            resp = requests.post(
                url,
                json={"chat_id": telegram_id, "text": text},
                timeout=10,
            )
            if not resp.ok:
                logger.warning("Telegram send failed for %s: %s", telegram_id, resp.text)
        except Exception as e:
            logger.error("Telegram error for %s: %s", telegram_id, e)


def analyze_screenshots(screenshot_ids: list) -> None:
    """
    Основная задача: берёт скриншоты из БД, анализирует через Groq,
    сохраняет результат и рассылает в Telegram.
    Вызывается через Django Q2: async_task('apps.screener.tasks.analyze_screenshots', ids)
    """
    from apps.screener.models import AnalysisResult, Screenshot

    screenshots = Screenshot.objects.filter(id__in=screenshot_ids)
    if not screenshots.exists():
        logger.warning("No screenshots found for ids: %s", screenshot_ids)
        return

    screenshots.update(status="processing")

    image_paths = []
    for s in screenshots:
        abs_path = s.image.path
        if os.path.exists(abs_path):
            image_paths.append(abs_path)

    if not image_paths:
        screenshots.update(status="error")
        return

    try:
        _broadcast_telegram(f"📸 Получил {len(image_paths)} скриншот(а). Анализирую...")

        answer = _call_groq(image_paths)

        primary = screenshots.first()
        AnalysisResult.objects.update_or_create(
            screenshot=primary,
            defaults={
                "answer": answer,
                "model_used": "meta-llama/llama-4-scout-17b-16e-instruct",
            },
        )
        screenshots.update(status="done")
        _broadcast_telegram(f"🎯 ОТВЕТ:\n\n{answer}")
        logger.info("Task done for screenshots: %s", screenshot_ids)

    except Exception as exc:
        logger.error("analyze_screenshots failed: %s", exc)
        screenshots.update(status="error")
        _broadcast_telegram(f"❌ Ошибка при анализе: {exc}")
        raise
