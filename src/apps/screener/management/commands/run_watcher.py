import logging
import os
import threading
import time

from django.core.management.base import BaseCommand
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

# Сколько секунд ждать тишины после последнего события перед обработкой
BUFFER_DELAY = 5

# Сколько раз проверять стабильность файла и с каким интервалом (сек)
STABILITY_CHECKS = 3
STABILITY_INTERVAL = 2

# Мусорные расширения и префиксы, которые Google Drive создаёт временно
IGNORED_EXTENSIONS = {".tmp", ".crdownload", ".part", ".gdoc", ".gsheet", ".gslides"}
IGNORED_PREFIXES = ("~$", ".~", "._")


class ScreenshotHandler(FileSystemEventHandler):
    def __init__(self):
        self._pending: dict[str, float] = {}  # path → время последнего события
        self._processed: set[str] = set()     # уже обработанные пути (защита от дублей)
        self._lock = threading.Lock()
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

    # ------------------------------------------------------------------
    # Фильтрация
    # ------------------------------------------------------------------

    def _is_image(self, path: str) -> bool:
        return path.lower().endswith((".png", ".jpg", ".jpeg"))

    def _is_junk(self, path: str) -> bool:
        """Отсеивает временные файлы Google Drive и других программ."""
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()
        if ext in IGNORED_EXTENSIONS:
            return True
        if any(name.startswith(p) for p in IGNORED_PREFIXES):
            return True
        # Google Drive иногда создаёт файлы вида "Screenshot.png.ggdownload"
        if ".gg" in name.lower():
            return True
        return False

    # ------------------------------------------------------------------
    # Добавление в очередь
    # ------------------------------------------------------------------

    def _add(self, path: str) -> None:
        if not self._is_image(path):
            return
        if self._is_junk(path):
            logger.debug("🗑  Игнорирую мусорный файл: %s", os.path.basename(path))
            return
        if not os.path.exists(path):
            return

        with self._lock:
            if path in self._processed:
                return  # уже отправляли — пропускаем
            was_new = path not in self._pending
            self._pending[path] = time.time()

        if was_new:
            logger.info("➕ Новый файл в очереди: %s", os.path.basename(path))

    def on_created(self, event):
        if not event.is_directory:
            self._add(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._add(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._add(event.dest_path)

    # ------------------------------------------------------------------
    # Основной цикл: ждём тишины, потом проверяем стабильность файла
    # ------------------------------------------------------------------

    def _flush_loop(self) -> None:
        while True:
            time.sleep(1)
            now = time.time()
            ready = []

            with self._lock:
                for path, last_event in list(self._pending.items()):
                    if now - last_event >= BUFFER_DELAY:
                        ready.append(path)
                for path in ready:
                    del self._pending[path]

            if ready:
                self._process_batch(ready)

    # ------------------------------------------------------------------
    # Проверка что файл стабилен (Google Drive закончил запись)
    # ------------------------------------------------------------------

    def _is_stable(self, path: str) -> bool:
        """
        Читаем размер файла несколько раз с паузой.
        Если размер не меняется и файл можно открыть — Google Drive закончил запись.
        """
        try:
            prev_size = -1
            for _ in range(STABILITY_CHECKS):
                if not os.path.exists(path):
                    return False
                size = os.path.getsize(path)
                if size == 0:
                    return False
                if size != prev_size and prev_size != -1:
                    logger.debug("⏳ Файл ещё пишется: %s (%d → %d)", os.path.basename(path), prev_size, size)
                    return False
                prev_size = size
                time.sleep(STABILITY_INTERVAL)

            # Пробуем открыть — гарантия что файл не залочен Google Drive
            with open(path, "rb") as f:
                f.read(1)
            return True
        except (OSError, PermissionError) as e:
            logger.debug("⏳ Файл недоступен: %s — %s", os.path.basename(path), e)
            return False

    # ------------------------------------------------------------------
    # Обработка готовых файлов
    # ------------------------------------------------------------------

    def _process_batch(self, paths: list) -> None:
        from apps.screener.models import Screenshot
        from django.core.files import File
        from django_q.tasks import async_task

        stable_paths = []
        retry_paths = []

        for path in paths:
            if not os.path.exists(path):
                logger.warning("⚠️  Файл исчез до обработки: %s", path)
                continue
            if self._is_stable(path):
                stable_paths.append(path)
            else:
                logger.info("🔁 Файл ещё не готов, вернём в очередь: %s", os.path.basename(path))
                retry_paths.append(path)

        # Нестабильные файлы возвращаем в очередь
        if retry_paths:
            with self._lock:
                for path in retry_paths:
                    self._pending[path] = time.time()

        if not stable_paths:
            return

        logger.info("🔄 Обрабатываю %d файл(ов)", len(stable_paths))
        screenshot_ids = []

        for path in stable_paths:
            try:
                with open(path, "rb") as f:
                    filename = os.path.basename(path)
                    screenshot = Screenshot()
                    screenshot.image.save(filename, File(f), save=True)
                    screenshot_ids.append(screenshot.id)

                with self._lock:
                    self._processed.add(path)

                logger.info("💾 Сохранён: %s → id=%d", filename, screenshot.id)
            except Exception as e:
                logger.error("❌ Ошибка сохранения %s: %s", path, e)

        if screenshot_ids:
            async_task(
                "apps.screener.tasks.analyze_screenshots",
                screenshot_ids,
            )
            logger.info("📨 Задача отправлена в Django-Q: %s", screenshot_ids)


class Command(BaseCommand):
    help = "Запускает watchdog для мониторинга папки со скриншотами"

    def add_arguments(self, parser):
        parser.add_argument(
            "--folder",
            type=str,
            default=None,
            help="Папка для мониторинга (по умолчанию WATCH_FOLDER из settings)",
        )

    def handle(self, *args, **options):
        from django.conf import settings

        folder = options["folder"] or getattr(settings, "WATCH_FOLDER", None)

        if not folder:
            self.stderr.write("❌ Укажите WATCH_FOLDER в settings или передайте --folder")
            return

        if not os.path.isdir(folder):
            self.stderr.write(f"❌ Папка не существует: {folder}")
            return

        self.stdout.write(f"👁  Слежу за папкой: {folder}")

        handler = ScreenshotHandler()
        observer = Observer()
        observer.schedule(handler, folder, recursive=False)
        observer.start()

        try:
            while observer.is_alive():
                observer.join(timeout=1)
        except KeyboardInterrupt:
            self.stdout.write("\n🛑 Остановка...")
            observer.stop()

        observer.join()
        self.stdout.write("✅ Watchdog остановлен.")