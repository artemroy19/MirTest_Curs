from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models import Q
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.accounts.models import User
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    MirTokenObtainPairSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileSerializer,
    RegisterSerializer,
    UserSerializer,
)
from apps.groups.models import Group, GroupMembership
from apps.tests.models import TestAssignment


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-created_at")
    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user
        qs = User.objects.all().order_by("-created_at")

        ids = self.request.query_params.get("ids")
        role = self.request.query_params.get("role")

        if ids:
            ids_list = [int(pk) for pk in ids.split(",") if pk.isdigit()]
            qs = qs.filter(id__in=ids_list)

        if user.is_superuser or user.role == "admin":
            if role:
                qs = qs.filter(role=role)
            return qs

        if user.role == "teacher":
            if role == "student":
                return qs.filter(role=User.Roles.STUDENT)
            student_ids = list(GroupMembership.objects.filter(group__teacher=user).values_list("student_id", flat=True))
            if ids:
                allowed_ids = [pk for pk in ids_list if pk in student_ids]
                return qs.filter(id__in=allowed_ids)
            return User.objects.filter(id=user.id)

        return User.objects.filter(id=user.id)

    def perform_create(self, serializer):
        if not (self.request.user.is_superuser or self.request.user.role == "admin"):
            raise PermissionDenied("Создавать пользователей может только администратор.")
        serializer.save()

    def perform_update(self, serializer):
        if not (self.request.user.is_superuser or self.request.user.role == "admin"):
            raise PermissionDenied("Редактировать пользователей может только администратор.")
        serializer.save()

    def perform_destroy(self, instance):
        if not (self.request.user.is_superuser or self.request.user.role == "admin"):
            raise PermissionDenied("Удалять пользователей может только администратор.")
        instance.delete()


class MeView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user, context={"request": request})
        return Response(serializer.data)


class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user


class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = MirTokenObtainPairSerializer


class PasswordResetRequestView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email=serializer.validated_data["email"], is_active=True).first()
        if not user:
            return Response({"detail": "Если email существует, инструкция отправлена."})

        uid = urlsafe_base64_encode(str(user.pk).encode())
        token = default_token_generator.make_token(user)
        reset_link = f"/reset-password?uid={uid}&token={token}"

        send_mail(
            subject="MirTest: восстановление пароля",
            message=(
                "Для сброса пароля перейдите по ссылке:\n"
                f"{reset_link}\n\n"
                "Если вы не запрашивали смену пароля, проигнорируйте письмо."
            ),
            from_email=None,
            recipient_list=[user.email],
            fail_silently=True,
        )

        return Response({"detail": "Инструкция отправлена.", "uid": uid, "token": token})


class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid_raw = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        try:
            user_id = force_str(urlsafe_base64_decode(uid_raw))
            user = User.objects.get(pk=user_id)
        except Exception as exc:  # noqa: BLE001
            raise ValidationError({"uid": "Некорректный uid."}) from exc

        if not default_token_generator.check_token(user, token):
            raise ValidationError({"token": "Недействительный или просроченный токен."})

        user.set_password(new_password)
        user.save(update_fields=["password"])
        return Response({"detail": "Пароль обновлён."})


class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data["old_password"]):
            raise ValidationError({"old_password": "Неверный текущий пароль."})

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Пароль изменён."})
