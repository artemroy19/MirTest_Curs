from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.tests.models import Test, TestQuestion


class TestAttempt(TimeStampedModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    attempt_number = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    auto_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    manual_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_overdue = models.BooleanField(default=False)
    essay_review_pending = models.BooleanField(default=False)

    class Meta:
        unique_together = ("test", "student", "attempt_number")


class AttemptAnswer(TimeStampedModel):
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name="answers")
    test_question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE, related_name="attempt_answers")
    answer_payload = models.JSONField(default=dict)
    is_correct = models.BooleanField(null=True, blank=True)
    auto_points = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    manual_points = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    teacher_comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
