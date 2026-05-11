from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.questions.models import Question, QuestionBankCategory


User = get_user_model()


class QuestionsApiTests(APITestCase):
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

    def category(self, owner, title="Category"):
        return QuestionBankCategory.objects.create(owner=owner, title=title)

    def question(self, owner, question_type=Question.QuestionType.SINGLE, category=None, title="Question"):
        payloads = {
            Question.QuestionType.SINGLE: {
                "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
                "correct_option": "a",
            },
            Question.QuestionType.MULTIPLE: {
                "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
                "correct_options": ["a", "b"],
            },
            Question.QuestionType.TEXT: {"correct_answers": ["answer"]},
            Question.QuestionType.EXTENDED: {"criteria": "Explain"},
        }
        return Question.objects.create(
            owner=owner,
            category=category,
            question_type=question_type,
            title=title,
            prompt="Prompt",
            base_points=2,
            payload=payloads[question_type],
        )

    def test_teacher_can_create_category(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        self.authenticate(teacher)

        response = self.client.post("/api/categories/", {"title": "Algebra"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(QuestionBankCategory.objects.get().owner, teacher)

    def test_teacher_can_create_question(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        category = self.category(teacher)
        self.authenticate(teacher)

        response = self.client.post(
            "/api/questions/",
            {
                "category_id": category.id,
                "question_type": "single",
                "title": "Choose one",
                "prompt": "Prompt",
                "base_points": "2.00",
                "payload": {
                    "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
                    "correct_option": "a",
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Question.objects.get().owner, teacher)

    def test_student_cannot_create_question(self):
        student = self.create_user("student@example.com", User.Roles.STUDENT)
        self.authenticate(student)

        response = self.client.post(
            "/api/questions/",
            {
                "question_type": "text",
                "title": "Text",
                "prompt": "Prompt",
                "payload": {"correct_answers": ["answer"]},
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Question.objects.count(), 0)

    def test_supported_question_types_can_be_created(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        self.authenticate(teacher)
        payloads = {
            "single": {
                "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
                "correct_option": "a",
            },
            "multiple": {
                "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
                "correct_options": ["a"],
            },
            "text": {"correct_answers": ["answer"]},
            "extended": {"criteria": "Explain"},
        }

        for question_type, payload in payloads.items():
            with self.subTest(question_type=question_type):
                response = self.client.post(
                    "/api/questions/",
                    {
                        "question_type": question_type,
                        "title": f"{question_type} question",
                        "prompt": "Prompt",
                        "payload": payload,
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_question_payload_is_saved(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        self.authenticate(teacher)
        payload = {"correct_answers": ["Paris", "paris"]}

        response = self.client.post(
            "/api/questions/",
            {"question_type": "text", "title": "Capital", "prompt": "France?", "payload": payload},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Question.objects.get().payload, payload)

    def test_invalid_question_type_returns_error(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        self.authenticate(teacher)

        response = self.client.post(
            "/api/questions/",
            {"question_type": "essay", "title": "Old type", "prompt": "Prompt", "payload": {}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_teacher_sees_only_own_questions(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        other_teacher = self.create_user("other@example.com", User.Roles.TEACHER)
        own_question = self.question(teacher, title="Own")
        self.question(other_teacher, title="Other")
        self.authenticate(teacher)

        response = self.client.get("/api/questions/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(ids, {own_question.id})

    def test_filter_questions_by_type(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        single = self.question(teacher, Question.QuestionType.SINGLE, title="Single")
        self.question(teacher, Question.QuestionType.TEXT, title="Text")
        self.authenticate(teacher)

        response = self.client.get("/api/questions/?question_type=single")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(ids, {single.id})

    def test_filter_questions_by_category(self):
        teacher = self.create_user("teacher@example.com", User.Roles.TEACHER)
        algebra = self.category(teacher, "Algebra")
        geometry = self.category(teacher, "Geometry")
        question = self.question(teacher, category=algebra)
        self.question(teacher, category=geometry, title="Geometry question")
        self.authenticate(teacher)

        response = self.client.get(f"/api/questions/?category={algebra.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(ids, {question.id})
