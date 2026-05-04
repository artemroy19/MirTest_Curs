from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q, Sum
from django.utils import timezone
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.attempts.models import AttemptAnswer, TestAttempt
from apps.accounts.models import User
from apps.groups.models import Group, GroupMembership
from apps.questions.models import Question
from apps.questions.serializers import QuestionSerializer
from apps.tests.models import Test, TestAssignment, TestQuestion
from apps.tests.serializers import TestAssignmentSerializer, TestQuestionSerializer, TestSerializer


class TestViewSet(viewsets.ModelViewSet):
    queryset = Test.objects.prefetch_related("test_questions__question").all().order_by("-updated_at")
    serializer_class = TestSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["title", "description"]

    def _is_admin(self):
        user = self.request.user
        return user.is_superuser or user.role == "admin"

    def _assert_can_edit(self, test: Test, user):
        if not (self._is_admin() or test.owner_id == user.id):
            raise PermissionDenied("Редактировать тест может только владелец.")

    def _assert_editable(self, test: Test):
        if test.is_frozen or test.attempts.exists():
            raise ValidationError("Тест заморожен и не может редактироваться.")

    def _normalize_orders(self, test: Test):
        entries = list(test.test_questions.all().order_by("order", "id"))
        for idx, item in enumerate(entries, start=1):
            item.order = idx
        if entries:
            TestQuestion.objects.bulk_update(entries, ["order"])

    def get_queryset(self):
        user = self.request.user
        qs = Test.objects.prefetch_related("test_questions__question").all().order_by("-updated_at")

        if self._is_admin():
            return qs
        if user.role == "teacher":
            return qs.filter(owner=user)

        group_ids = GroupMembership.objects.filter(student=user).values_list("group_id", flat=True)
        assigned_test_ids = TestAssignment.objects.filter(Q(student=user) | Q(group_id__in=group_ids)).values_list("test_id", flat=True)
        return qs.filter(id__in=assigned_test_ids).distinct()

    def perform_create(self, serializer):
        if self.request.user.role not in {"teacher", "admin"} and not self.request.user.is_superuser:
            raise PermissionDenied("Создавать тесты может только преподаватель.")
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        test = self.get_object()
        user = self.request.user
        self._assert_can_edit(test, user)
        self._assert_editable(test)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="available")
    def available(self, request):
        if request.user.role != "student":
            return Response([])

        group_ids = GroupMembership.objects.filter(student=request.user).values_list("group_id", flat=True)
        assignments = TestAssignment.objects.select_related("test").filter(Q(student=request.user) | Q(group_id__in=group_ids))

        tests_by_id = {}
        for assignment in assignments:
            tests_by_id[assignment.test_id] = assignment.test

        serializer = self.get_serializer(tests_by_id.values(), many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="clone")
    def clone_test(self, request, pk=None):
        source = self.get_object()
        user = request.user
        if not (self._is_admin() or source.owner_id == user.id):
            raise PermissionDenied("Клонировать тест может только владелец.")

        clone = Test.objects.create(
            owner=user,
            title=f"{source.title} (копия)",
            description=source.description,
            timer_minutes=source.timer_minutes,
            attempts_limit=source.attempts_limit,
            deadline=source.deadline,
            result_visibility=source.result_visibility,
            is_frozen=False,
        )

        entries = []
        for tq in source.test_questions.all():
            entries.append(
                TestQuestion(
                    test=clone,
                    question=tq.question,
                    order=tq.order,
                    overridden_points=tq.overridden_points,
                )
            )
        TestQuestion.objects.bulk_create(entries)
        return Response(self.get_serializer(clone).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="add-question")
    def add_question(self, request, pk=None):
        test = self.get_object()
        user = request.user
        self._assert_can_edit(test, user)
        self._assert_editable(test)

        question_id = request.data.get("question")
        if not question_id:
            raise ValidationError({"question": "Укажите id вопроса."})

        question = Question.objects.filter(id=question_id).first()
        if not question:
            raise ValidationError({"question": "Вопрос не найден."})
        if not self._is_admin() and question.owner_id != user.id:
            raise PermissionDenied("Можно добавлять только свои вопросы.")

        desired_order = request.data.get("order")
        if desired_order is None:
            desired_order = test.test_questions.count() + 1
        desired_order = int(desired_order)
        if desired_order < 1:
            raise ValidationError({"order": "Порядок должен быть >= 1."})

        overridden_points = request.data.get("overridden_points")
        with transaction.atomic():
            test_question, created = TestQuestion.objects.update_or_create(
                test=test,
                question=question,
                defaults={"overridden_points": overridden_points},
            )
            if created:
                test_question.order = desired_order
                test_question.save(update_fields=["order"])
            else:
                test_question.overridden_points = overridden_points
                test_question.order = desired_order
                test_question.save(update_fields=["overridden_points", "order"])
            self._normalize_orders(test)

        return Response(TestQuestionSerializer(test_question).data)

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        test = self.get_object()
        user = request.user
        self._assert_can_edit(test, user)

        group_ids = request.data.get("group_ids", []) or []
        student_ids = request.data.get("student_ids", []) or []

        if not group_ids and not student_ids:
            raise ValidationError({"detail": "Укажите хотя бы одну группу или студента."})

        with transaction.atomic():
            TestAssignment.objects.filter(test=test).delete()
            for group_id in group_ids:
                TestAssignment.objects.get_or_create(
                    test=test,
                    group_id=group_id,
                    student=None,
                    defaults={"assigned_by": request.user},
                )
            for student_id in student_ids:
                TestAssignment.objects.get_or_create(
                    test=test,
                    student_id=student_id,
                    group=None,
                    defaults={"assigned_by": request.user},
                )

        return Response({"detail": "Тест назначен."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="create-inline-question")
    def create_inline_question(self, request, pk=None):
        test = self.get_object()
        user = request.user
        self._assert_can_edit(test, user)
        self._assert_editable(test)

        data = {
            "category": None,
            "question_type": request.data.get("question_type"),
            "title": request.data.get("title"),
            "prompt": request.data.get("prompt"),
            "base_points": request.data.get("base_points", 1),
            "payload": request.data.get("payload", {}),
            "is_bank_question": False,
        }
        serializer = QuestionSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        question = serializer.save(owner=user, category=None, is_bank_question=False)

        order = test.test_questions.count() + 1
        test_question = TestQuestion.objects.create(test=test, question=question, order=order)
        return Response(TestQuestionSerializer(test_question).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="remove-question")
    def remove_question(self, request, pk=None):
        test = self.get_object()
        user = request.user
        self._assert_can_edit(test, user)
        self._assert_editable(test)

        test_question_id = request.data.get("test_question") or request.data.get("question")
        if not test_question_id:
            raise ValidationError({"test_question": "Укажите id элемента вопроса в тесте."})

        test_question = TestQuestion.objects.filter(id=test_question_id, test=test).first()
        if not test_question:
            test_question = TestQuestion.objects.filter(test=test, question_id=test_question_id).first()
        if not test_question:
            raise ValidationError({"test_question": "Вопрос не найден в этом тесте."})

        test_question.delete()
        self._normalize_orders(test)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="reorder-questions")
    def reorder_questions(self, request, pk=None):
        test = self.get_object()
        user = request.user
        self._assert_can_edit(test, user)
        self._assert_editable(test)

        order_ids = request.data.get("order", [])
        if not isinstance(order_ids, list) or len(order_ids) == 0:
            raise ValidationError({"order": "Передайте непустой список id test_questions в новом порядке."})

        current = list(test.test_questions.all())
        current_ids = {item.id for item in current}
        try:
            provided_ids = {int(item) for item in order_ids}
        except (TypeError, ValueError) as exc:
            raise ValidationError({"order": "Все элементы списка order должны быть целыми числами."}) from exc
        if current_ids != provided_ids:
            raise ValidationError({"order": "Список order должен содержать все текущие элементы теста без пропусков."})

        by_id = {item.id: item for item in current}
        for index, item_id in enumerate(order_ids, start=1):
            by_id[int(item_id)].order = index
        TestQuestion.objects.bulk_update(list(by_id.values()), ["order"])

        return Response(TestQuestionSerializer(test.test_questions.all().order_by("order", "id"), many=True).data)

    @action(detail=True, methods=["get"], url_path="stats")
    def stats(self, request, pk=None):
        test = self.get_object()
        user = request.user
        if not (self._is_admin() or test.owner_id == user.id):
            raise PermissionDenied("Статистика доступна только владельцу теста.")

        group_ids = TestAssignment.objects.filter(test=test, group__isnull=False).values_list("group_id", flat=True)
        assigned_by_group = GroupMembership.objects.filter(group_id__in=group_ids).values_list("student_id", flat=True)
        assigned_direct = TestAssignment.objects.filter(test=test, student__isnull=False).values_list("student_id", flat=True)
        assigned_students = set(assigned_by_group) | set(assigned_direct)

        completed_attempts = test.attempts.filter(status=TestAttempt.Status.COMPLETED)
        completed_students = completed_attempts.values("student_id").distinct().count()
        total_attempts = completed_attempts.count()

        max_score = sum(
            (tq.overridden_points if tq.overridden_points is not None else tq.question.base_points)
            for tq in test.test_questions.select_related("question")
        )
        max_score = Decimal(max_score or 0)

        avg_score = completed_attempts.aggregate(v=Avg("total_score"))["v"] or Decimal("0")
        avg_score_pct = float((avg_score / max_score * 100) if max_score else 0)

        duration_expr = ExpressionWrapper(F("ended_at") - F("started_at"), output_field=DurationField())
        avg_duration = completed_attempts.exclude(ended_at__isnull=True).annotate(duration=duration_expr).aggregate(v=Avg("duration"))["v"]
        avg_duration_seconds = int(avg_duration.total_seconds()) if avg_duration else None

        overdue_pct = 0.0
        if total_attempts:
            overdue_count = completed_attempts.filter(is_overdue=True).count()
            overdue_pct = overdue_count / total_attempts * 100

        question_stats = []
        for tq in test.test_questions.select_related("question"):
            answers = AttemptAnswer.objects.filter(test_question=tq, attempt__status=TestAttempt.Status.COMPLETED)
            answers_count = answers.count()
            correct_count = answers.filter(is_correct=True).count()
            avg_points = answers.aggregate(v=Avg(F("auto_points") + F("manual_points"))) ["v"] if answers_count else 0
            max_points = tq.overridden_points if tq.overridden_points is not None else tq.question.base_points
            question_stats.append(
                {
                    "test_question_id": tq.id,
                    "question_id": tq.question_id,
                    "title": tq.question.title,
                    "correct_pct": (correct_count / answers_count * 100) if answers_count else 0,
                    "avg_points": float(avg_points or 0),
                    "avg_points_pct": float((Decimal(avg_points or 0) / Decimal(max_points) * 100) if max_points else 0),
                }
            )

        return Response(
            {
                "assigned_students": len(assigned_students),
                "completed_students": completed_students,
                "used_attempts": total_attempts,
                "avg_score_pct": round(avg_score_pct, 2),
                "avg_duration_seconds": avg_duration_seconds,
                "overdue_pct": round(overdue_pct, 2),
                "question_stats": question_stats,
            }
        )


class TestAssignmentViewSet(viewsets.ModelViewSet):
    queryset = TestAssignment.objects.select_related("test", "group", "student", "assigned_by").all().order_by("-created_at")
    serializer_class = TestAssignmentSerializer

    def _is_admin(self):
        user = self.request.user
        return user.is_superuser or user.role == "admin"

    def get_queryset(self):
        user = self.request.user
        qs = TestAssignment.objects.select_related("test", "group", "student", "assigned_by").all().order_by("-created_at")
        if self._is_admin():
            scoped = qs
        elif user.role == "teacher":
            scoped = qs.filter(test__owner=user)
        else:
            scoped = qs.filter(Q(student=user) | Q(group__memberships__student=user)).distinct()

        test_id = self.request.query_params.get("test")
        if test_id:
            scoped = scoped.filter(test_id=test_id)
        return scoped

    def perform_create(self, serializer):
        user = self.request.user
        test = serializer.validated_data["test"]
        group = serializer.validated_data.get("group")
        student = serializer.validated_data.get("student")

        if not (self._is_admin() or test.owner_id == user.id):
            raise PermissionDenied("Назначать тест может только владелец.")

        if group is not None and not (self._is_admin() or group.teacher_id == user.id):
            raise PermissionDenied("Можно назначать только на свои группы.")
        if student is not None and student.role != "student":
            raise ValidationError({"student": "Назначать можно только пользователям с ролью student."})
        if student is not None and not self._is_admin():
            is_teacher_student = GroupMembership.objects.filter(group__teacher=user, student=student).exists()
            if not is_teacher_student:
                raise PermissionDenied("Можно назначать только своим студентам (из ваших групп).")

        serializer.save(assigned_by=user)

    def perform_destroy(self, instance):
        user = self.request.user
        if not (self._is_admin() or instance.test.owner_id == user.id):
            raise PermissionDenied("Удалять назначение может только владелец теста.")
        instance.delete()

    @action(detail=False, methods=["get"], url_path="targets")
    def assignment_targets(self, request):
        user = request.user

        if self._is_admin():
            groups = list(Group.objects.values("id", "title").order_by("title"))
            students = list(
                User.objects.filter(role="student", is_active=True)
                .values("id", "email", "first_name", "last_name")
                .order_by("email")
            )
            return Response(
                {
                    "groups": groups,
                    "students": students,
                }
            )

        if user.role != "teacher":
            return Response({"groups": [], "students": []})

        teacher_groups = list(
            user.owned_groups.values("id", "title").order_by("title")
        )
        students = list(
            User.objects.filter(
                role="student",
                is_active=True,
                group_memberships__group__teacher=user,
            )
            .distinct()
            .values("id", "email", "first_name", "last_name")
            .order_by("email")
        )
        return Response({"groups": teacher_groups, "students": students})
