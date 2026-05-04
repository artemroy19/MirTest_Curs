from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class QuestionBankCategory(TimeStampedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="question_categories")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.title


class MediaAsset(TimeStampedModel):
    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        AUDIO = "audio", "Audio"
        VIDEO = "video", "Video"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="media_assets")
    media_type = models.CharField(max_length=20, choices=MediaType.choices)
    file = models.FileField(upload_to="question-media/")
    original_name = models.CharField(max_length=255)
    size_bytes = models.PositiveBigIntegerField(default=0)


class Question(TimeStampedModel):
    class QuestionType(models.TextChoices):
        SINGLE = "single", "Single Choice"
        MULTIPLE = "multiple", "Multiple Choice"
        TEXT = "text", "Text Answer"
        EXTENDED = "extended", "Extended Question"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="questions")
    category = models.ForeignKey(QuestionBankCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="questions")
    question_type = models.CharField(max_length=32, choices=QuestionType.choices)
    title = models.CharField(max_length=255)
    prompt = models.TextField()
    base_points = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    payload = models.JSONField(default=dict)
    is_bank_question = models.BooleanField(default=True)
    media_assets = models.ManyToManyField(MediaAsset, blank=True, related_name="questions")

    def __str__(self) -> str:
        return self.title
