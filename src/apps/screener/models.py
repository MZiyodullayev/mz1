from django.db import models


class WhitelistUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.telegram_id})"

    class Meta:
        verbose_name = "Whitelist user"
        verbose_name_plural = "Whitelist users"


class Screenshot(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("done", "Done"),
        ("error", "Error"),
    ]

    image = models.ImageField(upload_to="screenshots/")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Screenshot #{self.pk} [{self.status}]"

    class Meta:
        verbose_name = "Screenshot"
        verbose_name_plural = "Screenshots"
        ordering = ["-created_at"]


class AnalysisResult(models.Model):
    screenshot = models.OneToOneField(
        Screenshot, on_delete=models.CASCADE, related_name="result"
    )
    answer = models.TextField()
    model_used = models.CharField(max_length=100, default="llama-4-scout-17b-16e-instruct")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result for Screenshot #{self.screenshot_id}"

    class Meta:
        verbose_name = "Analysis result"
        verbose_name_plural = "Analysis results"
        ordering = ["-created_at"]
