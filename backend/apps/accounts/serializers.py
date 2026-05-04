from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "avatar",
            "role",
            "is_active",
            "is_blocked",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_avatar(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get("request")
        url = obj.avatar.url
        return request.build_absolute_uri(url) if request else url


class ProfileSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField(read_only=True)
    avatar_file = serializers.ImageField(source="avatar", write_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "avatar",
            "role",
            "is_active",
            "is_blocked",
            "created_at",
            "avatar_file",
        ]
        read_only_fields = ["id", "email", "username", "role", "is_active", "is_blocked", "created_at"]

    def update(self, instance, validated_data):
        avatar = validated_data.get("avatar")
        if avatar is None and "avatar" in validated_data:
            if instance.avatar:
                instance.avatar.delete(save=False)
            instance.avatar = None
            validated_data.pop("avatar")
        return super().update(instance, validated_data)

    def get_avatar(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get("request")
        url = obj.avatar.url
        return request.build_absolute_uri(url) if request else url


class RegisterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "name",
            "first_name",
            "last_name",
            "role",
            "password",
        ]

    def validate_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value

    def validate_role(self, value: str) -> str:
        if value == User.Roles.ADMIN:
            raise serializers.ValidationError("Роль admin нельзя выбрать при регистрации.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        name = validated_data.pop("name", "").strip()
        if name and not validated_data.get("first_name"):
            validated_data["first_name"] = name

        username = validated_data.get("username") or name or validated_data["email"].split("@", 1)[0]
        validated_data["username"] = self._generate_username(username)

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def _generate_username(self, username: str) -> str:
        base_username = "".join([c for c in username.lower() if c.isalnum()])[:28] or "user"
        candidate = base_username
        counter = 1
        while User.objects.filter(username=candidate).exists():
            candidate = f"{base_username}{counter}"
            counter += 1
        return candidate


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    def validate_new_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    def validate_new_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value


class MirTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.is_blocked:
            raise serializers.ValidationError("Пользователь заблокирован.")
        data["user"] = UserSerializer(self.user).data
        return data
