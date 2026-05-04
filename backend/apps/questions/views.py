from rest_framework import filters, viewsets
from rest_framework.exceptions import PermissionDenied

from apps.questions.models import MediaAsset, Question, QuestionBankCategory
from apps.questions.serializers import MediaAssetSerializer, QuestionBankCategorySerializer, QuestionSerializer


class OwnerScopedMixin:
    def _is_admin(self):
        user = self.request.user
        return user.is_superuser or user.role == "admin"


class QuestionBankCategoryViewSet(OwnerScopedMixin, viewsets.ModelViewSet):
    queryset = QuestionBankCategory.objects.all().order_by("title")
    serializer_class = QuestionBankCategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["title", "description"]

    def get_queryset(self):
        qs = QuestionBankCategory.objects.all().order_by("title")
        if self._is_admin():
            return qs
        return qs.filter(owner=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.role not in {"teacher", "admin"} and not self.request.user.is_superuser:
            raise PermissionDenied("Создавать категории может только преподаватель.")
        serializer.save(owner=self.request.user)


class MediaAssetViewSet(OwnerScopedMixin, viewsets.ModelViewSet):
    queryset = MediaAsset.objects.all().order_by("-created_at")
    serializer_class = MediaAssetSerializer

    def get_queryset(self):
        qs = MediaAsset.objects.all().order_by("-created_at")
        if self._is_admin():
            return qs
        return qs.filter(owner=self.request.user)


class QuestionViewSet(OwnerScopedMixin, viewsets.ModelViewSet):
    queryset = Question.objects.select_related("category", "owner").prefetch_related("media_assets").all().order_by("-updated_at")
    serializer_class = QuestionSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "prompt"]
    ordering_fields = ["created_at", "updated_at", "base_points"]

    def get_queryset(self):
        qs = Question.objects.select_related("category", "owner").prefetch_related("media_assets").all().order_by("-updated_at")

        if not self._is_admin():
            qs = qs.filter(owner=self.request.user)

        qtype = self.request.query_params.get("question_type")
        category = self.request.query_params.get("category")
        is_bank = self.request.query_params.get("is_bank_question")

        if qtype:
            qs = qs.filter(question_type=qtype)
        if category:
            qs = qs.filter(category_id=category)
        if is_bank in {"true", "false"}:
            qs = qs.filter(is_bank_question=is_bank == "true")

        return qs

    def perform_create(self, serializer):
        if self.request.user.role not in {"teacher", "admin"} and not self.request.user.is_superuser:
            raise PermissionDenied("Создавать вопросы может только преподаватель.")
        serializer.save(owner=self.request.user)
