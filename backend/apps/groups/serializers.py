import secrets

from rest_framework import serializers

from apps.accounts.models import User
from apps.groups.models import Group, GroupMembership


class GroupSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True, required=False)
    members_count = serializers.IntegerField(source="memberships.count", read_only=True)
    students_count = serializers.IntegerField(source="memberships.count", read_only=True)

    class Meta:
        model = Group
        fields = ["id", "teacher", "title", "name", "description", "invite_code", "members_count", "students_count", "created_at"]
        read_only_fields = ["id", "teacher", "invite_code", "created_at"]

    def validate(self, attrs):
        if not attrs.get("title") and attrs.get("name"):
            attrs["title"] = attrs.pop("name").strip()

        title = (attrs.get("title") or "").strip()
        if not title:
            raise serializers.ValidationError({"title": "Название группы не может быть пустым."})

        attrs["title"] = title
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        title = validated_data["title"]
        invite_code = self._generate_invite_code(title or "GROUP")
        return Group.objects.create(teacher=request.user, invite_code=invite_code, **validated_data)

    def _generate_invite_code(self, title: str) -> str:
        prefix = "".join([c for c in title.upper() if c.isalnum()])[:8] or "GROUP"
        while True:
            suffix = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(4))
            code = f"{prefix}-{suffix}"
            if not Group.objects.filter(invite_code=code).exists():
                return code


class GroupMembershipSerializer(serializers.ModelSerializer):
    group_title = serializers.CharField(source="group.title", read_only=True)
    student_email = serializers.EmailField(source="student.email", read_only=True)
    student_first_name = serializers.CharField(source="student.first_name", read_only=True)
    student_last_name = serializers.CharField(source="student.last_name", read_only=True)

    class Meta:
        model = GroupMembership
        fields = [
            "id",
            "group",
            "group_title",
            "student",
            "student_email",
            "student_first_name",
            "student_last_name",
            "joined_at",
            "created_at",
        ]
        read_only_fields = ["id", "joined_at", "created_at"]

    def validate_student(self, value: User):
        if value.role != User.Roles.STUDENT:
            raise serializers.ValidationError("Добавлять можно только пользователей с ролью student.")
        return value
