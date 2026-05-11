from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.attempts.models import AttemptAnswer, TestAttempt
from apps.groups.models import Group, GroupMembership
from apps.questions.models import Question
from apps.tests.models import Test, TestAssignment, TestQuestion


User = get_user_model()


class AttemptsApiTests(APITestCase):
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

    def create_test(self, teacher, **extra):
        data = {"title": "Test", "description": "Description"}
        data.update(extra)
        return Test.objects.create(owner=teacher, **data)

    def create_question(self, owner, question_type=Question.QuestionType.SINGLE, title="Question", base_points=2):
        payloads = {
            Question.QuestionType.SINGLE: {
                "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
                "correct_option": "a",
            },
            Question.QuestionType.MULTIPLE: {
                "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
                "correct_options": ["a", "b"],
            },
            Question.QuestionType.TEXT: {"correct_answers": ["answer", "Ответ"]},
            Question.QuestionType.EXTENDED: {"criteria": "Full explanation"},
        }
        return Question.objects.create(
            owner=owner,
            question_type=question_type,
            title=title,
            prompt="Prompt",
            base_points=base_points,
            payload=payloads[question_type],
        )

    def add_question(self, test, question, order=1, overridden_points=None):
        return TestQuestion.objects.create(
            test=test,
            question=question,
            order=order,
            overridden_points=overridden_points,
        )

    def assign_to_student(self, test, student, teacher):
        return TestAssignment.objects.create(test=test, student=student, assigned_by=teacher)

    def create_assigned_test(self, question_type=Question.QuestionType.SINGLE, **test_extra):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        student = self.create_user("student@example.com", User.Roles.STUDENT)
        test = self.create_test(teacher, **test_extra)
        question = self.create_question(teacher, question_type=question_type)
        test_question = self.add_question(test, question)
        self.assign_to_student(test, student, teacher)
        return teacher, student, test, question, test_question

    def start_attempt(self, student, test):
        self.authenticate(student)
        return self.client.post("/api/attempts/start/", {"test": test.id}, format="json")

    def test_student_can_start_assigned_test(self):
        _, student, test, _, _ = self.create_assigned_test()

        response = self.start_attempt(student, test)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TestAttempt.objects.get().student, student)

    def test_student_cannot_start_unassigned_test(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        student = self.create_user("student@example.com", User.Roles.STUDENT)
        test = self.create_test(teacher)
        self.add_question(test, self.create_question(teacher))

        response = self.start_attempt(student, test)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(TestAttempt.objects.count(), 0)

    def test_teacher_cannot_start_attempt(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        test = self.create_test(teacher)
        self.authenticate(teacher)

        response = self.client.post("/api/attempts/start/", {"test": test.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_start_after_deadline(self):
        _, student, test, _, _ = self.create_assigned_test(deadline=timezone.now() - timedelta(days=1))

        response = self.start_attempt(student, test)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(TestAttempt.objects.count(), 0)

    def test_attempt_limit_is_enforced(self):
        teacher, student, test, _, _ = self.create_assigned_test(attempts_limit=1)
        TestAttempt.objects.create(
            test=test,
            student=student,
            attempt_number=1,
            status=TestAttempt.Status.COMPLETED,
        )

        response = self.start_attempt(student, test)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(TestAttempt.objects.filter(test=test, student=student).count(), 1)

    def test_start_attempt_creates_answers(self):
        _, student, test, _, _ = self.create_assigned_test()

        response = self.start_attempt(student, test)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        attempt = TestAttempt.objects.get()
        self.assertEqual(attempt.answers.count(), test.test_questions.count())

    def test_student_can_save_answer(self):
        _, student, test, _, test_question = self.create_assigned_test()
        self.start_attempt(student, test)
        attempt = TestAttempt.objects.get()

        response = self.client.post(
            f"/api/attempts/{attempt.id}/save-answer/",
            {"test_question": test_question.id, "answer_payload": {"selected": "a"}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(attempt.answers.get(test_question=test_question).answer_payload, {"selected": "a"})

    def test_student_can_submit_attempt(self):
        _, student, test, _, test_question = self.create_assigned_test()
        self.start_attempt(student, test)
        attempt = TestAttempt.objects.get()
        self.client.post(
            f"/api/attempts/{attempt.id}/save-answer/",
            {"test_question": test_question.id, "answer_payload": {"selected": "a"}},
            format="json",
        )

        response = self.client.post(f"/api/attempts/{attempt.id}/submit/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], TestAttempt.Status.COMPLETED)

    def test_submit_changes_status_to_completed(self):
        _, student, test, _, _ = self.create_assigned_test()
        self.start_attempt(student, test)
        attempt = TestAttempt.objects.get()

        self.client.post(f"/api/attempts/{attempt.id}/submit/", {}, format="json")

        attempt.refresh_from_db()
        self.assertEqual(attempt.status, TestAttempt.Status.COMPLETED)
        self.assertIsNotNone(attempt.ended_at)

    def test_single_choice_scoring(self):
        _, student, test, _, test_question = self.create_assigned_test(Question.QuestionType.SINGLE)
        self.start_attempt(student, test)
        attempt = TestAttempt.objects.get()
        self.client.post(
            f"/api/attempts/{attempt.id}/save-answer/",
            {"test_question": test_question.id, "answer_payload": {"selected": "a"}},
            format="json",
        )

        self.client.post(f"/api/attempts/{attempt.id}/submit/", {}, format="json")

        attempt.refresh_from_db()
        answer = attempt.answers.get()
        self.assertTrue(answer.is_correct)
        self.assertEqual(answer.auto_points, Decimal("2.00"))
        self.assertEqual(attempt.total_score, Decimal("2.00"))

    def test_multiple_choice_scoring(self):
        _, student, test, _, test_question = self.create_assigned_test(Question.QuestionType.MULTIPLE)
        self.start_attempt(student, test)
        attempt = TestAttempt.objects.get()
        self.client.post(
            f"/api/attempts/{attempt.id}/save-answer/",
            {"test_question": test_question.id, "answer_payload": {"selected": ["b", "a"]}},
            format="json",
        )

        self.client.post(f"/api/attempts/{attempt.id}/submit/", {}, format="json")

        answer = AttemptAnswer.objects.get()
        self.assertTrue(answer.is_correct)
        self.assertEqual(answer.auto_points, Decimal("2.00"))

    def test_text_answer_scoring(self):
        _, student, test, _, test_question = self.create_assigned_test(Question.QuestionType.TEXT)
        self.start_attempt(student, test)
        attempt = TestAttempt.objects.get()
        self.client.post(
            f"/api/attempts/{attempt.id}/save-answer/",
            {"test_question": test_question.id, "answer_payload": {"value": " ANSWER "}},
            format="json",
        )

        self.client.post(f"/api/attempts/{attempt.id}/submit/", {}, format="json")

        answer = AttemptAnswer.objects.get()
        self.assertTrue(answer.is_correct)
        self.assertEqual(answer.auto_points, Decimal("2.00"))

    def test_extended_answer_requires_manual_review(self):
        _, student, test, _, test_question = self.create_assigned_test(Question.QuestionType.EXTENDED)
        self.start_attempt(student, test)
        attempt = TestAttempt.objects.get()
        self.client.post(
            f"/api/attempts/{attempt.id}/save-answer/",
            {"test_question": test_question.id, "answer_payload": {"value": "Long answer"}},
            format="json",
        )

        self.client.post(f"/api/attempts/{attempt.id}/submit/", {}, format="json")

        attempt.refresh_from_db()
        answer = AttemptAnswer.objects.get()
        self.assertIsNone(answer.is_correct)
        self.assertEqual(answer.auto_points, Decimal("0.00"))
        self.assertTrue(attempt.essay_review_pending)

    def test_teacher_can_review_extended_answer(self):
        teacher, student, test, _, test_question = self.create_assigned_test(Question.QuestionType.EXTENDED)
        self.start_attempt(student, test)
        attempt = TestAttempt.objects.get()
        self.client.post(
            f"/api/attempts/{attempt.id}/save-answer/",
            {"test_question": test_question.id, "answer_payload": {"value": "Long answer"}},
            format="json",
        )
        self.client.post(f"/api/attempts/{attempt.id}/submit/", {}, format="json")
        answer = AttemptAnswer.objects.get()
        self.authenticate(teacher)

        response = self.client.post(
            f"/api/attempts/{attempt.id}/review-essay/",
            {"answer_id": answer.id, "manual_points": "1.50", "teacher_comment": "Good"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        attempt.refresh_from_db()
        answer.refresh_from_db()
        self.assertEqual(answer.manual_points, Decimal("1.50"))
        self.assertEqual(answer.teacher_comment, "Good")
        self.assertIsNotNone(answer.reviewed_at)
        self.assertFalse(attempt.essay_review_pending)
        self.assertEqual(attempt.total_score, Decimal("1.50"))

    def test_teacher_cannot_review_another_teacher_answer(self):
        other_teacher = self.create_user("other@example.com", User.Roles.TEACHER)
        _, student, test, _, test_question = self.create_assigned_test(Question.QuestionType.EXTENDED)
        self.start_attempt(student, test)
        attempt = TestAttempt.objects.get()
        self.client.post(
            f"/api/attempts/{attempt.id}/save-answer/",
            {"test_question": test_question.id, "answer_payload": {"value": "Long answer"}},
            format="json",
        )
        self.client.post(f"/api/attempts/{attempt.id}/submit/", {}, format="json")
        answer = AttemptAnswer.objects.get()
        self.authenticate(other_teacher)

        response = self.client.post(
            f"/api/attempts/{attempt.id}/review-essay/",
            {"answer_id": answer.id, "manual_points": "1.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_cannot_submit_another_student_attempt(self):
        _, student, test, _, _ = self.create_assigned_test()
        other_student = self.create_user("other-student@example.com", User.Roles.STUDENT)
        group = Group.objects.create(teacher=test.owner, title="Group")
        GroupMembership.objects.create(group=group, student=other_student)
        TestAssignment.objects.create(test=test, group=group, assigned_by=test.owner)
        self.start_attempt(student, test)
        attempt = TestAttempt.objects.get(student=student)
        self.authenticate(other_student)

        response = self.client.post(f"/api/attempts/{attempt.id}/submit/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
