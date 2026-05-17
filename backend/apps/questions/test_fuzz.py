from types import SimpleNamespace

from django.contrib.auth import get_user_model
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase

from apps.questions.serializers import QuestionSerializer


User = get_user_model()

json_scalar = st.one_of(st.none(), st.booleans(), st.integers(), st.text(max_size=40))
json_value = st.recursive(
    json_scalar,
    lambda children: st.one_of(
        st.lists(children, max_size=5),
        st.dictionaries(st.text(max_size=20), children, max_size=5),
    ),
    max_leaves=20,
)


class QuestionSerializerFuzzTests(HypothesisTestCase):
    def setUp(self):
        self.teacher, _ = User.objects.get_or_create(
            email="teacher@example.com",
            defaults={
                "username": "teacher",
                "role": User.Roles.TEACHER,
            },
        )
        self.teacher.set_password("StrongPass123!")
        self.teacher.save(update_fields=["password"])
        self.request = SimpleNamespace(user=self.teacher)

    @settings(max_examples=120, deadline=None)
    @given(
        question_type=st.sampled_from(["single", "multiple", "text", "extended", "essay", "", "unknown"]),
        payload=json_value,
        title=st.text(min_size=1, max_size=80),
        prompt=st.text(min_size=1, max_size=160),
    )
    def test_question_serializer_handles_random_payload_without_crashing(self, question_type, payload, title, prompt):
        serializer = QuestionSerializer(
            data={
                "question_type": question_type,
                "title": title,
                "prompt": prompt,
                "base_points": "1.00",
                "payload": payload,
            },
            context={"request": self.request},
        )

        self.assertIsInstance(serializer.is_valid(), bool)

    @settings(max_examples=80, deadline=None)
    @given(
        option_a=st.text(min_size=1, max_size=30),
        option_b=st.text(min_size=1, max_size=30),
        correct_id=st.sampled_from(["a", "b"]),
    )
    def test_single_question_valid_payload_is_accepted(self, option_a, option_b, correct_id):
        serializer = QuestionSerializer(
            data={
                "question_type": "single",
                "title": "Generated single question",
                "prompt": "Choose one option",
                "base_points": "1.00",
                "payload": {
                    "options": [{"id": "a", "text": option_a}, {"id": "b", "text": option_b}],
                    "correct_option": correct_id,
                },
            },
            context={"request": self.request},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    @settings(max_examples=80, deadline=None)
    @given(answers=st.lists(st.text(min_size=1, max_size=30), min_size=1, max_size=5))
    def test_text_question_valid_payload_is_accepted(self, answers):
        serializer = QuestionSerializer(
            data={
                "question_type": "text",
                "title": "Generated text question",
                "prompt": "Write an answer",
                "base_points": "1.00",
                "payload": {"correct_answers": answers},
            },
            context={"request": self.request},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
