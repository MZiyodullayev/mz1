import base64
import logging
import os

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_image_bytes(screenshot) -> bytes:
    """
    Достаёт байты картинки. Работает в двух сценариях:
    1. Воркер и веб на одной машине (обычная локальная разработка) —
       файл реально лежит на диске, читаем его напрямую.
    2. Воркер работает отдельно (например, у тебя на компе), а веб —
       на Render: файла на диске воркера нет, скачиваем его по
       публичному URL (Render теперь отдаёт /media/ всегда, см. urls.py).
    """
    try:
        local_path = screenshot.image.path
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read()
    except NotImplementedError:
        pass  # remote storage backends (e.g. S3) don't support .path

    base_url = settings.PUBLIC_BASE_URL.rstrip("/")
    if not base_url:
        raise RuntimeError(
            "Image not found locally and PUBLIC_BASE_URL is not set — "
            "can't fetch it remotely. Set PUBLIC_BASE_URL in .env to your "
            "Render URL (e.g. https://mz1.onrender.com)."
        )
    image_url = f"{base_url}{screenshot.image.url}"
    resp = requests.get(image_url, timeout=30)
    resp.raise_for_status()
    return resp.content


def _call_groq(images: list) -> str:
    """Отправляет изображения (bytes) в Groq API и возвращает текстовый ответ."""
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

    for image_bytes in images:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
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

    images = []
    for s in screenshots:
        try:
            images.append(_get_image_bytes(s))
        except Exception as e:
            logger.error("Could not fetch image for screenshot %s: %s", s.pk, e)

    if not images:
        screenshots.update(status="error")
        _broadcast_telegram(
            "❌ Не удалось получить файл(ы) скриншота "
            "(проверь PUBLIC_BASE_URL в .env воркера)."
        )
        return

    try:
        _broadcast_telegram(f"📸 Получил {len(images)} скриншот(а). Анализирую...")

        answer = _call_groq(images)

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
