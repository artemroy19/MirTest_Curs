from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.groups.models import Group, GroupMembership


User = get_user_model()


class GroupsApiTests(APITestCase):
    password = "StrongPass123!"

    def create_user(self, email, role):
        return User.objects.create_user(
            email=email,
            username=email.split("@", 1)[0],
            password=self.password,
            role=role,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def create_group(self, teacher, title="Group"):
        return Group.objects.create(teacher=teacher, title=title, description="Description")

    def test_teacher_can_create_group(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        self.authenticate(teacher)

        response = self.client.post("/api/groups/", {"title": "Math", "description": "Grade 5"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Group.objects.get().teacher, teacher)

    def test_student_cannot_create_group(self):
        student = self.create_user("student@example.com", User.Roles.STUDENT)
        self.authenticate(student)

        response = self.client.post("/api/groups/", {"title": "Math"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Group.objects.count(), 0)

    def test_group_has_invite_code(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        self.authenticate(teacher)

        response = self.client.post("/api/groups/", {"title": "Physics"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["invite_code"])
        self.assertEqual(Group.objects.get().invite_code, response.data["invite_code"])

    def test_student_can_join_group_by_code(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        student = self.create_user("student@example.com", User.Roles.STUDENT)
        group = self.create_group(teacher)
        self.authenticate(student)

        response = self.client.post("/api/groups/join/", {"invite_code": group.invite_code}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(GroupMembership.objects.filter(group=group, student=student).exists())

    def test_student_cannot_join_same_group_twice(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        student = self.create_user("student@example.com", User.Roles.STUDENT)
        group = self.create_group(teacher)
        self.authenticate(student)

        first = self.client.post("/api/groups/join/", {"invite_code": group.invite_code}, format="json")
        second = self.client.post("/api/groups/join/", {"invite_code": group.invite_code}, format="json")

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(GroupMembership.objects.filter(group=group, student=student).count(), 1)

    def test_teacher_sees_only_own_groups(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        other_teacher = self.create_user("other@example.com", User.Roles.TEACHER)
        own_group = self.create_group(teacher, "Own")
        self.create_group(other_teacher, "Other")
        self.authenticate(teacher)

        response = self.client.get("/api/groups/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(ids, {own_group.id})

    def test_student_sees_joined_groups(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        student = self.create_user("student@example.com", User.Roles.STUDENT)
        joined_group = self.create_group(teacher, "Joined")
        self.create_group(teacher, "Not joined")
        GroupMembership.objects.create(group=joined_group, student=student)
        self.authenticate(student)

        response = self.client.get("/api/groups/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(ids, {joined_group.id})

    def test_teacher_can_regenerate_invite_code(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        group = self.create_group(teacher, "Math")
        old_code = group.invite_code
        self.authenticate(teacher)

        response = self.client.post(f"/api/groups/{group.id}/regenerate-code/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        group.refresh_from_db()
        self.assertNotEqual(group.invite_code, old_code)

    def test_student_can_leave_group(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        student = self.create_user("student@example.com", User.Roles.STUDENT)
        group = self.create_group(teacher)
        GroupMembership.objects.create(group=group, student=student)
        self.authenticate(student)

        response = self.client.post("/api/group-memberships/leave/", {"group": group.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(GroupMembership.objects.filter(group=group, student=student).exists())
