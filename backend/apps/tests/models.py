from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.groups.models import Group
from apps.questions.models import Question


class Test(TimeStampedModel):
    class ResultVisibility(models.TextChoices):
        SCORE_ONLY = "score_only", "Score Only"
        SCORE_WITH_REVIEW = "score_with_review", "Score With Review"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tests")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    timer_minutes = models.PositiveIntegerField(null=True, blank=True)
    attempts_limit = models.PositiveIntegerField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    result_visibility = models.CharField(max_length=32, choices=ResultVisibility.choices, default=ResultVisibility.SCORE_ONLY)
    is_frozen = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.title


class TestQuestion(TimeStampedModel):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="test_questions")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="test_entries")
    order = models.PositiveIntegerField(default=1)
    overridden_points = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ("test", "question")
        ordering = ["order", "id"]


class TestAssignment(TimeStampedModel):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="assignments")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True, related_name="assigned_tests")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="assigned_tests")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_assignments")

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(group__isnull=False) | models.Q(student__isnull=False),
                name="assignment_requires_target",
            )
        ]
