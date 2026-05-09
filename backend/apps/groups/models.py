import uuid

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


def generate_invite_code() -> str:
    prefix = "GROUP"
    suffix = uuid.uuid4().hex[:8].upper()
    return f"{prefix}-{suffix}"


class Group(TimeStampedModel):
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_groups")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    invite_code = models.CharField(max_length=32, unique=True, default=generate_invite_code)

    class Meta:
        db_table = "student_groups"

    def __str__(self) -> str:
        return self.title


class GroupMembership(TimeStampedModel):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="memberships")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_memberships")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "group_memberships"
        unique_together = ("group", "student")

    def __str__(self) -> str:
        return f"{self.student_id} in {self.group_id}"
