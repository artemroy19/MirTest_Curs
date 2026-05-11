from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.groups.models import Group, GroupMembership
from apps.questions.models import Question
from apps.tests.models import Test, TestAssignment, TestQuestion


User = get_user_model()


class TestsAndAssignmentsApiTests(APITestCase):
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

    def create_question(self, owner, title="Question"):
        return Question.objects.create(
            owner=owner,
            question_type=Question.QuestionType.SINGLE,
            title=title,
            prompt="Prompt",
            base_points=1,
            payload={
                "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
                "correct_option": "a",
            },
        )

    def create_test(self, owner, title="Test", **extra):
        return Test.objects.create(owner=owner, title=title, description="Description", **extra)

    def test_teacher_can_create_test(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        self.authenticate(teacher)

        response = self.client.post("/api/tests/", {"title": "Control work"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Test.objects.get().owner, teacher)

    def test_student_cannot_create_test(self):
        student = self.create_user("student@example.com", User.Roles.STUDENT)
        self.authenticate(student)

        response = self.client.post("/api/tests/", {"title": "Control work"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Test.objects.count(), 0)

    def test_teacher_can_add_question_to_test(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        test = self.create_test(teacher)
        question = self.create_question(teacher)
        self.authenticate(teacher)

        response = self.client.post(f"/api/tests/{test.id}/add-question/", {"question": question.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(TestQuestion.objects.filter(test=test, question=question).exists())

    def test_teacher_can_remove_question_from_test(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        test = self.create_test(teacher)
        question = self.create_question(teacher)
        test_question = TestQuestion.objects.create(test=test, question=question, order=1)
        self.authenticate(teacher)

        response = self.client.post(
            f"/api/tests/{test.id}/remove-question/",
            {"test_question": test_question.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TestQuestion.objects.filter(id=test_question.id).exists())

    def test_teacher_can_reorder_questions(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        test = self.create_test(teacher)
        first = TestQuestion.objects.create(test=test, question=self.create_question(teacher, "First"), order=1)
        second = TestQuestion.objects.create(test=test, question=self.create_question(teacher, "Second"), order=2)
        self.authenticate(teacher)

        response = self.client.post(
            f"/api/tests/{test.id}/reorder-questions/",
            {"order": [second.id, first.id]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.order, 2)
        self.assertEqual(second.order, 1)

    def test_teacher_can_assign_test_to_group(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        test = self.create_test(teacher)
        group = Group.objects.create(teacher=teacher, title="Group")
        self.authenticate(teacher)

        response = self.client.post(f"/api/tests/{test.id}/assign/", {"group_ids": [group.id]}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(TestAssignment.objects.filter(test=test, group=group).exists())

    def test_teacher_can_assign_test_to_student(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        student = self.create_user("student@example.com", User.Roles.STUDENT)
        group = Group.objects.create(teacher=teacher, title="Group")
        GroupMembership.objects.create(group=group, student=student)
        test = self.create_test(teacher)
        self.authenticate(teacher)

        response = self.client.post(
            "/api/assignments/",
            {"test": test.id, "student": student.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(TestAssignment.objects.filter(test=test, student=student).exists())

    def test_student_sees_available_assigned_test(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        student = self.create_user("student@example.com", User.Roles.STUDENT)
        test = self.create_test(teacher)
        TestAssignment.objects.create(test=test, student=student, assigned_by=teacher)
        self.authenticate(student)

        response = self.client.get("/api/tests/available/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data}
        self.assertEqual(ids, {test.id})

    def test_student_does_not_see_unassigned_test(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        student = self.create_user("student@example.com", User.Roles.STUDENT)
        self.create_test(teacher)
        self.authenticate(student)

        response = self.client.get("/api/tests/available/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_teacher_can_get_test_stats(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        test = self.create_test(teacher)
        TestQuestion.objects.create(test=test, question=self.create_question(teacher), order=1)
        self.authenticate(teacher)

        response = self.client.get(f"/api/tests/{test.id}/stats/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("assigned_students", response.data)
        self.assertIn("question_stats", response.data)

    def test_teacher_cannot_modify_another_teacher_test(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        other_teacher = self.create_user("other@example.com", User.Roles.TEACHER)
        test = self.create_test(other_teacher)
        question = self.create_question(teacher)
        self.authenticate(teacher)

        response = self.client.post(f"/api/tests/{test.id}/add-question/", {"question": question.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
