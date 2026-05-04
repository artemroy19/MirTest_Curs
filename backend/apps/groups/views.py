from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.groups.models import Group, GroupMembership
from apps.groups.serializers import GroupMembershipSerializer, GroupSerializer


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all().order_by("-created_at")
    serializer_class = GroupSerializer

    def _is_admin(self):
        user = self.request.user
        return user.is_superuser or user.role == "admin"

    def get_queryset(self):
        user = self.request.user
        if self._is_admin():
            return Group.objects.all().order_by("-created_at")
        if user.role == "teacher":
            return Group.objects.filter(teacher=user).order_by("-created_at")
        return Group.objects.filter(memberships__student=user).distinct().order_by("-created_at")

    def perform_create(self, serializer):
        if self.request.user.role not in {"teacher", "admin"} and not self.request.user.is_superuser:
            raise PermissionDenied("Создавать группы может только преподаватель или администратор.")
        serializer.save()

    def perform_update(self, serializer):
        group = self.get_object()
        user = self.request.user
        if not (self._is_admin() or group.teacher_id == user.id):
            raise PermissionDenied("Редактировать группу может только владелец.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if not (self._is_admin() or instance.teacher_id == user.id):
            raise PermissionDenied("Удалять группу может только владелец.")
        instance.delete()

    @action(detail=False, methods=["post"], url_path="join")
    def join_by_code(self, request):
        invite_code = request.data.get("invite_code", "").strip().upper()
        if not invite_code:
            raise serializers.ValidationError({"invite_code": "Укажите код приглашения."})
        if request.user.role != "student":
            raise PermissionDenied("Вступать в группу по коду может только студент.")

        group = get_object_or_404(Group, invite_code=invite_code)
        membership, created = GroupMembership.objects.get_or_create(group=group, student=request.user)
        serializer = GroupMembershipSerializer(membership)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="regenerate-code")
    def regenerate_code(self, request, pk=None):
        group = self.get_object()
        user = request.user
        if not (self._is_admin() or group.teacher_id == user.id):
            raise PermissionDenied("Код группы может обновить только владелец.")

        serializer = self.get_serializer(group, data={"title": group.title, "description": group.description}, partial=True)
        serializer.is_valid(raise_exception=True)
        new_code = serializer._generate_invite_code(group.title)  # noqa: SLF001
        group.invite_code = new_code
        group.save(update_fields=["invite_code"])
        return Response({"invite_code": new_code})


class GroupMembershipViewSet(viewsets.ModelViewSet):
    queryset = GroupMembership.objects.all().order_by("-joined_at")
    serializer_class = GroupMembershipSerializer

    def _is_admin(self):
        user = self.request.user
        return user.is_superuser or user.role == "admin"

    def get_queryset(self):
        user = self.request.user
        qs = GroupMembership.objects.select_related("group", "student").all().order_by("-joined_at")
        if self._is_admin():
            pass
        elif user.role == "teacher":
            qs = qs.filter(group__teacher=user)
        else:
            qs = qs.filter(student=user)

        group_id = self.request.query_params.get("group")
        student_id = self.request.query_params.get("student")

        if group_id and group_id.isdigit():
            qs = qs.filter(group_id=int(group_id))
        if student_id and student_id.isdigit():
            qs = qs.filter(student_id=int(student_id))

        return qs

    def perform_create(self, serializer):
        user = self.request.user
        group = serializer.validated_data["group"]
        student = serializer.validated_data["student"]

        if not (self._is_admin() or (user.role == "teacher" and group.teacher_id == user.id)):
            raise PermissionDenied("Вы не можете добавлять студентов в эту группу.")
        if student.role != "student":
            raise serializers.ValidationError({"student": "Добавлять можно только пользователей с ролью student."})
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        can_delete = self._is_admin() or (user.role == "teacher" and instance.group.teacher_id == user.id) or instance.student_id == user.id
        if not can_delete:
            raise PermissionDenied("Вы не можете удалить этого участника.")
        instance.delete()

    @action(detail=False, methods=["post"], url_path="leave")
    def leave_group(self, request):
        group_id = request.data.get("group")
        if not group_id:
            raise serializers.ValidationError({"group": "Укажите id группы."})

        membership = GroupMembership.objects.filter(group_id=group_id, student=request.user).first()
        if not membership:
            raise serializers.ValidationError({"group": "Вы не состоите в этой группе."})

        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
