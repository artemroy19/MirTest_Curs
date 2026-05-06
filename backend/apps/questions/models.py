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

    def __str__(self) -> str:
        return self.title
