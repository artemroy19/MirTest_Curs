from decimal import Decimal

from rest_framework import serializers

from apps.attempts.models import AttemptAnswer, TestAttempt


class AttemptAnswerSerializer(serializers.ModelSerializer):
    question_title = serializers.CharField(source="test_question.question.title", read_only=True)
    question_type = serializers.CharField(source="test_question.question.question_type", read_only=True)
    question_prompt = serializers.CharField(source="test_question.question.prompt", read_only=True)
    question_payload = serializers.JSONField(source="test_question.question.payload", read_only=True)
    question_id = serializers.IntegerField(source="test_question.question_id", read_only=True)
    order = serializers.IntegerField(source="test_question.order", read_only=True)
    max_points = serializers.SerializerMethodField()
    earned_points = serializers.SerializerMethodField()

    class Meta:
        model = AttemptAnswer
        fields = [
            "id",
            "attempt",
            "test_question",
            "question_id",
            "question_title",
            "question_type",
            "question_prompt",
            "question_payload",
            "order",
            "max_points",
            "earned_points",
            "answer_payload",
            "is_correct",
            "auto_points",
            "manual_points",
            "teacher_comment",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_correct", "auto_points", "manual_points", "teacher_comment", "reviewed_at", "created_at", "updated_at"]

    def get_max_points(self, obj):
        if obj.test_question.overridden_points is not None:
            return obj.test_question.overridden_points
        return obj.test_question.question.base_points

    def get_earned_points(self, obj):
        return (obj.auto_points or 0) + (obj.manual_points or 0)


class TestAttemptSerializer(serializers.ModelSerializer):
    answers = AttemptAnswerSerializer(many=True, read_only=True)
    test_title = serializers.CharField(source="test.title", read_only=True)
    timer_minutes = serializers.IntegerField(source="test.timer_minutes", read_only=True)
    result_visibility = serializers.CharField(source="test.result_visibility", read_only=True)
    student_name = serializers.SerializerMethodField()
    max_score = serializers.SerializerMethodField()

    class Meta:
        model = TestAttempt
        fields = [
            "id",
            "test",
            "test_title",
            "timer_minutes",
            "result_visibility",
            "student",
            "student_name",
            "status",
            "attempt_number",
            "started_at",
            "ended_at",
            "auto_score",
            "manual_score",
            "total_score",
            "is_overdue",
            "essay_review_pending",
            "max_score",
            "answers",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "test_title",
            "timer_minutes",
            "result_visibility",
            "student",
            "student_name",
            "status",
            "attempt_number",
            "started_at",
            "ended_at",
            "auto_score",
            "manual_score",
            "total_score",
            "is_overdue",
            "essay_review_pending",
            "max_score",
            "created_at",
            "updated_at",
        ]

    def get_student_name(self, obj):
        parts = [obj.student.last_name, obj.student.first_name]
        return " ".join(part for part in parts if part).strip() or obj.student.email

    def get_max_score(self, obj):
        total = Decimal("0")
        for answer in obj.answers.all():
            if answer.test_question.overridden_points is not None:
                total += answer.test_question.overridden_points
            else:
                total += answer.test_question.question.base_points
        return total


class SaveAnswerSerializer(serializers.Serializer):
    test_question = serializers.IntegerField()
    answer_payload = serializers.JSONField(default=dict)


class EssayReviewSerializer(serializers.Serializer):
    answer_id = serializers.IntegerField()
    manual_points = serializers.DecimalField(max_digits=8, decimal_places=2)
    teacher_comment = serializers.CharField(required=False, allow_blank=True, default="")
