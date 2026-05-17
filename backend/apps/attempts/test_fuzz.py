from decimal import Decimal

from django.test import SimpleTestCase
from hypothesis import given, settings
from hypothesis import strategies as st

from apps.attempts.scoring import score_question


json_scalar = st.one_of(st.none(), st.booleans(), st.integers(), st.text(max_size=40))
json_value = st.recursive(
    json_scalar,
    lambda children: st.one_of(
        st.lists(children, max_size=5),
        st.dictionaries(st.text(max_size=20), children, max_size=5),
    ),
    max_leaves=20,
)
json_object = st.dictionaries(st.text(max_size=20), json_value, max_size=8)


class ScoringFuzzTests(SimpleTestCase):
    @settings(max_examples=120, deadline=None)
    @given(
        question_type=st.text(max_size=30),
        answer_payload=json_object,
        question_payload=json_object,
        max_points=st.decimals(min_value=0, max_value=100, places=2, allow_nan=False, allow_infinity=False),
    )
    def test_scoring_handles_random_payload_without_crashing(
        self,
        question_type,
        answer_payload,
        question_payload,
        max_points,
    ):
        is_correct, points = score_question(question_type, answer_payload, question_payload, max_points)

        self.assertIn(is_correct, [True, False, None])
        self.assertIsInstance(points, Decimal)
        self.assertGreaterEqual(points, Decimal("0"))

    @settings(max_examples=80, deadline=None)
    @given(
        selected=st.text(min_size=1, max_size=20),
        correct=st.text(min_size=1, max_size=20),
        max_points=st.decimals(min_value=0, max_value=100, places=2, allow_nan=False, allow_infinity=False),
    )
    def test_single_scoring_is_all_or_nothing(self, selected, correct, max_points):
        is_correct, points = score_question(
            "single",
            {"selected": selected},
            {"correct_option": correct},
            max_points,
        )

        expected_points = Decimal(str(max_points)) if selected == correct else Decimal("0")
        self.assertEqual(is_correct, selected == correct)
        self.assertEqual(points, expected_points)

    @settings(max_examples=80, deadline=None)
    @given(
        correct=st.lists(st.text(min_size=1, max_size=10), unique=True, min_size=1, max_size=5),
        extra=st.lists(st.text(min_size=1, max_size=10), unique=True, max_size=3),
    )
    def test_multiple_scoring_ignores_selection_order(self, correct, extra):
        selected = list(reversed(correct))
        is_correct, points = score_question(
            "multiple",
            {"selected": selected},
            {"correct_options": correct},
            Decimal("3.00"),
        )

        self.assertTrue(is_correct)
        self.assertEqual(points, Decimal("3.00"))

        if set(extra) - set(correct):
            is_correct_with_extra, points_with_extra = score_question(
                "multiple",
                {"selected": selected + extra},
                {"correct_options": correct},
                Decimal("3.00"),
            )
            self.assertFalse(is_correct_with_extra)
            self.assertEqual(points_with_extra, Decimal("0"))

    @settings(max_examples=80, deadline=None)
    @given(answer=st.text(alphabet=st.characters(min_codepoint=48, max_codepoint=122), min_size=1, max_size=40))
    def test_text_scoring_normalizes_case_and_outer_spaces(self, answer):
        is_correct, points = score_question(
            "text",
            {"value": f"  {answer.upper()}  "},
            {"correct_answers": [answer.lower()]},
            Decimal("2.00"),
        )

        self.assertTrue(is_correct)
        self.assertEqual(points, Decimal("2.00"))
