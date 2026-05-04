from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import (
    ChangePasswordView,
    LoginView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    ProfileView,
    RegisterView,
    UserViewSet,
)
from apps.attempts.views import AttemptViewSet, EssayReviewQueueView, EssayReviewSummaryView
from apps.groups.views import GroupMembershipViewSet, GroupViewSet
from apps.questions.views import MediaAssetViewSet, QuestionBankCategoryViewSet, QuestionViewSet
from apps.tests.views import TestAssignmentViewSet, TestViewSet


router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("groups", GroupViewSet, basename="group")
router.register("group-memberships", GroupMembershipViewSet, basename="group-membership")
router.register("categories", QuestionBankCategoryViewSet, basename="category")
router.register("media-assets", MediaAssetViewSet, basename="media-asset")
router.register("questions", QuestionViewSet, basename="question")
router.register("tests", TestViewSet, basename="test")
router.register("assignments", TestAssignmentViewSet, basename="assignment")
router.register("attempts", AttemptViewSet, basename="attempt")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/auth/password-reset/request/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("api/auth/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("api/auth/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("api/auth/password/change/", ChangePasswordView.as_view(), name="change-password-alias"),
    path("api/auth/profile/", ProfileView.as_view(), name="profile"),
    path("api/me/", MeView.as_view(), name="me"),
    path("api/essay-review-queue/", EssayReviewQueueView.as_view(), name="essay-review-queue"),
    path("api/essay-review-summary/", EssayReviewSummaryView.as_view(), name="essay-review-summary"),
    path("api/", include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
