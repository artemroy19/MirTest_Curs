from django.utils import timezone
from rest_framework import serializers

from apps.attempts.models import TestAttempt
from apps.questions.serializers import QuestionSerializer
from apps.tests.models import Test, TestAssignment, TestQuestion


class TestQuestionSerializer(serializers.ModelSerializer):
    question_data = QuestionSerializer(source="question", read_only=True)

    class Meta:
        model = TestQuestion
        fields = ["id", "test", "question", "question_data", "order", "overridden_points", "created_at"]
        read_only_fields = ["id", "created_at"]


class TestSerializer(serializers.ModelSerializer):
    test_questions = TestQuestionSerializer(many=True, read_only=True)
    questions_count = serializers.SerializerMethodField()
    max_score = serializers.SerializerMethodField()
    availability = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = [
            "id",
            "owner",
            "title",
            "description",
            "timer_minutes",
            "attempts_limit",
            "deadline",
            "result_visibility",
            "is_frozen",
            "test_questions",
            "questions_count",
            "max_score",
            "availability",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "is_frozen", "created_at", "updated_at"]

    def get_questions_count(self, obj):
        return obj.test_questions.count()

    def get_max_score(self, obj):
        return sum(
            (
                test_question.overridden_points
                if test_question.overridden_points is not None
                else test_question.question.base_points
            )
            for test_question in obj.test_questions.select_related("question")
        )

    def get_availability(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False) or user.role != "student":
            return None

        attempts_qs = TestAttempt.objects.filter(test=obj, student=user)
        used_attempts = attempts_qs.count()
        attempts_limit = obj.attempts_limit

        if obj.deadline and timezone.now() > obj.deadline:
            code = "deadline_passed"
            label = "Дедлайн просрочен"
            can_start = False
        elif attempts_limit is not None and used_attempts >= attempts_limit:
            code = "attempts_exhausted"
            label = "Попытки исчерпаны"
            can_start = False
        else:
            code = "available"
            label = "Пройти"
            can_start = True

        return {
            "code": code,
            "label": label,
            "can_start": can_start,
            "attempts_used": used_attempts,
            "attempts_limit": attempts_limit,
        }


class TestAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAssignment
        fields = ["id", "test", "group", "student", "assigned_by", "created_at"]
        read_only_fields = ["id", "assigned_by", "created_at"]

    def validate(self, attrs):
        if not attrs.get("group") and not attrs.get("student"):
            raise serializers.ValidationError("Нужно выбрать группу или студента.")
        return attrs
