from decimal import Decimal
from time import sleep

from django.db import OperationalError, transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.attempts.models import AttemptAnswer, TestAttempt
from apps.attempts.scoring import score_question
from apps.attempts.serializers import EssayReviewSerializer, SaveAnswerSerializer, TestAttemptSerializer
from apps.groups.models import GroupMembership
from apps.tests.models import Test, TestAssignment


class AttemptViewSet(viewsets.ModelViewSet):
    queryset = TestAttempt.objects.select_related("test", "student").prefetch_related("answers__test_question__question").all().order_by("-started_at")
    serializer_class = TestAttemptSerializer

    def _is_admin(self):
        user = self.request.user
        return user.is_superuser or user.role == "admin"

    def get_queryset(self):
        user = self.request.user
        qs = TestAttempt.objects.select_related("test", "student").prefetch_related("answers__test_question__question").all().order_by("-started_at")

        if self._is_admin():
            scoped = qs
        elif user.role == "teacher":
            scoped = qs.filter(test__owner=user)
        else:
            scoped = qs.filter(student=user)

        params = self.request.query_params
        if params.get("student"):
            scoped = scoped.filter(student_id=params["student"])
        if params.get("test"):
            scoped = scoped.filter(test_id=params["test"])
        if params.get("attempt_number"):
            scoped = scoped.filter(attempt_number=params["attempt_number"])
        if params.get("is_overdue") in {"true", "false"}:
            scoped = scoped.filter(is_overdue=params["is_overdue"] == "true")
        if params.get("essay_review_pending") in {"true", "false"}:
            scoped = scoped.filter(essay_review_pending=params["essay_review_pending"] == "true")

        return scoped

    def create(self, request, *args, **kwargs):
        raise ValidationError("Создание попытки доступно только через /api/attempts/start/.")

    @action(detail=False, methods=["post"], url_path="start")
    def start_attempt(self, request):
        if request.user.role != "student":
            raise PermissionDenied("Начать попытку может только студент.")

        test_id = request.data.get("test")
        if not test_id:
            raise ValidationError({"test": "Укажите id теста."})

        test = Test.objects.prefetch_related("test_questions").filter(id=test_id).first()
        if not test:
            raise ValidationError({"test": "Тест не найден."})

        group_ids = GroupMembership.objects.filter(student=request.user).values_list("group_id", flat=True)
        has_access = TestAssignment.objects.filter(test=test).filter(Q(student=request.user) | Q(group_id__in=group_ids)).exists()
        if not has_access:
            raise PermissionDenied("Этот тест вам не назначен.")

        now = timezone.now()
        if test.deadline and now > test.deadline:
            raise ValidationError("Дедлайн истёк, начать тест нельзя.")

        in_progress = TestAttempt.objects.filter(test=test, student=request.user, status=TestAttempt.Status.IN_PROGRESS).first()
        if in_progress:
            return Response(self.get_serializer(in_progress).data)

        used_attempts = TestAttempt.objects.filter(test=test, student=request.user).count()
        if test.attempts_limit is not None and used_attempts >= test.attempts_limit:
            raise ValidationError("Доступные попытки исчерпаны.")

        with transaction.atomic():
            attempt = TestAttempt.objects.create(
                test=test,
                student=request.user,
                attempt_number=used_attempts + 1,
                status=TestAttempt.Status.IN_PROGRESS,
            )

            answers = [AttemptAnswer(attempt=attempt, test_question=tq, answer_payload={}) for tq in test.test_questions.all()]
            AttemptAnswer.objects.bulk_create(answers)

            if not test.is_frozen:
                test.is_frozen = True
                test.save(update_fields=["is_frozen"])

        return Response(self.get_serializer(attempt).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="save-answer")
    def save_answer(self, request, pk=None):
        attempt = self.get_object()
        if attempt.student_id != request.user.id:
            raise PermissionDenied("Вы не можете редактировать эту попытку.")
        if attempt.status != TestAttempt.Status.IN_PROGRESS:
            raise ValidationError("Попытка уже завершена.")

        serializer = SaveAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        test_question_id = serializer.validated_data["test_question"]
        answer_payload = serializer.validated_data["answer_payload"]

        answer = AttemptAnswer.objects.filter(attempt=attempt, test_question_id=test_question_id).select_related("test_question").first()
        if not answer:
            raise ValidationError({"test_question": "Вопрос не принадлежит этой попытке."})

        answer.answer_payload = answer_payload
        answer.save(update_fields=["answer_payload", "updated_at"])
        return Response({"detail": "Ответ сохранён."})

    @action(detail=True, methods=["post"], url_path="submit")
    def submit_attempt(self, request, pk=None):
        attempt = self.get_object()
        if attempt.student_id != request.user.id and not self._is_admin():
            raise PermissionDenied("Вы не можете завершить эту попытку.")
        if attempt.status == TestAttempt.Status.COMPLETED:
            return Response(self.get_serializer(attempt).data)

        max_retries = 3
        for retry_index in range(max_retries):
            try:
                now = timezone.now()
                auto_score = Decimal("0")
                manual_score = Decimal("0")
                essay_pending = False

                with transaction.atomic():
                    locked_attempt = TestAttempt.objects.select_for_update().select_related("test").get(pk=attempt.pk)
                    answers = (
                        locked_attempt.answers.select_related("test_question__question")
                        .all()
                        .order_by("test_question__order", "id")
                    )

                    for answer in answers:
                        question = answer.test_question.question
                        max_points = (
                            answer.test_question.overridden_points
                            if answer.test_question.overridden_points is not None
                            else question.base_points
                        )

                        if question.question_type == question.QuestionType.EXTENDED:
                            essay_pending = True
                            answer.is_correct = None
                            answer.auto_points = Decimal("0")
                        else:
                            is_correct, points = score_question(
                                question_type=question.question_type,
                                answer_payload=answer.answer_payload or {},
                                question_payload=question.payload or {},
                                max_points=max_points,
                            )
                            answer.is_correct = is_correct
                            answer.auto_points = points
                            auto_score += points

                        manual_score += answer.manual_points
                        answer.save(update_fields=["is_correct", "auto_points", "updated_at"])

                    locked_attempt.status = TestAttempt.Status.COMPLETED
                    locked_attempt.ended_at = now
                    locked_attempt.auto_score = auto_score
                    locked_attempt.manual_score = manual_score
                    locked_attempt.total_score = auto_score + manual_score
                    locked_attempt.is_overdue = bool(locked_attempt.test.deadline and now > locked_attempt.test.deadline)
                    locked_attempt.essay_review_pending = essay_pending
                    locked_attempt.save(
                        update_fields=[
                            "status",
                            "ended_at",
                            "auto_score",
                            "manual_score",
                            "total_score",
                            "is_overdue",
                            "essay_review_pending",
                            "updated_at",
                        ]
                    )
                attempt.refresh_from_db()
                break
            except OperationalError:
                if retry_index == max_retries - 1:
                    raise
                sleep(0.1 * (retry_index + 1))

        return Response(self.get_serializer(attempt).data)

    @action(detail=True, methods=["post"], url_path="review-essay")
    def review_essay(self, request, pk=None):
        attempt = self.get_object()
        user = request.user
        if not (self._is_admin() or (user.role == "teacher" and attempt.test.owner_id == user.id)):
            raise PermissionDenied("Проверять развёрнутые вопросы может только преподаватель-владелец теста.")
        if attempt.status != TestAttempt.Status.COMPLETED:
            raise ValidationError("Развёрнутые вопросы проверяются только после завершения попытки.")

        serializer = EssayReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        answer = (
            AttemptAnswer.objects.select_related("test_question__question")
            .filter(id=serializer.validated_data["answer_id"], attempt=attempt)
            .first()
        )
        if not answer:
            raise ValidationError({"answer_id": "Ответ не найден в этой попытке."})

        if answer.test_question.question.question_type != answer.test_question.question.QuestionType.EXTENDED:
            raise ValidationError({"answer_id": "Этот ответ не является развёрнутым вопросом."})

        max_points = (
            answer.test_question.overridden_points
            if answer.test_question.overridden_points is not None
            else answer.test_question.question.base_points
        )
        manual_points = serializer.validated_data["manual_points"]
        if manual_points < 0 or manual_points > max_points:
            raise ValidationError({"manual_points": f"Баллы должны быть в диапазоне 0..{max_points}."})

        with transaction.atomic():
            answer.manual_points = manual_points
            answer.teacher_comment = serializer.validated_data.get("teacher_comment", "")
            answer.reviewed_at = timezone.now()
            answer.save(update_fields=["manual_points", "teacher_comment", "reviewed_at", "updated_at"])

            manual_sum = attempt.answers.aggregate(v=Sum("manual_points"))["v"] or Decimal("0")
            attempt.manual_score = manual_sum
            attempt.total_score = (attempt.auto_score or Decimal("0")) + manual_sum

            pending_essays = attempt.answers.filter(
                test_question__question__question_type="extended",
                reviewed_at__isnull=True,
            ).exists()
            attempt.essay_review_pending = pending_essays
            attempt.save(update_fields=["manual_score", "total_score", "essay_review_pending", "updated_at"])

        return Response(self.get_serializer(attempt).data)


class EssayReviewQueueView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TestAttemptSerializer

    def get_queryset(self):
        user = self.request.user
        qs = TestAttempt.objects.filter(essay_review_pending=True).select_related("test", "student").order_by("started_at")
        if user.is_superuser or user.role == "admin":
            return qs
        if user.role == "teacher":
            return qs.filter(test__owner=user)
        return qs.none()

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)


class EssayReviewSummaryView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.role not in {"teacher", "admin"} and not user.is_superuser:
            raise PermissionDenied("Доступно только преподавателю/администратору.")

        qs = TestAttempt.objects.filter(essay_review_pending=True)
        if not (user.is_superuser or user.role == "admin"):
            qs = qs.filter(test__owner=user)

        grouped = qs.values("test_id", "test__title").annotate(pending=Count("id")).order_by("-pending")
        return Response(list(grouped))
