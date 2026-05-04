from rest_framework import serializers

from apps.questions.models import MediaAsset, Question, QuestionBankCategory


class QuestionBankCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionBankCategory
        fields = ["id", "owner", "parent", "title", "description", "created_at"]
        read_only_fields = ["id", "owner", "created_at"]

    def validate_parent(self, value):
        if not value:
            return value

        # Ограничиваем вложенность до 2 уровней: root -> child
        if value.parent_id is not None:
            raise serializers.ValidationError("Максимальная вложенность категорий: 2 уровня.")

        request = self.context.get("request")
        if request and not request.user.is_superuser and value.owner_id != request.user.id:
            raise serializers.ValidationError("Родительская категория должна принадлежать вам.")

        return value


class MediaAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaAsset
        fields = ["id", "owner", "media_type", "file", "original_name", "size_bytes", "created_at"]
        read_only_fields = ["id", "owner", "original_name", "size_bytes", "created_at"]

    def validate(self, attrs):
        uploaded_file = attrs.get("file")
        media_type = attrs.get("media_type")
        if not uploaded_file or not media_type:
            return attrs

        content_type = (uploaded_file.content_type or "").lower()
        name = (uploaded_file.name or "").lower()

        limits = {
            MediaAsset.MediaType.IMAGE: 5 * 1024 * 1024,
            MediaAsset.MediaType.AUDIO: 20 * 1024 * 1024,
            MediaAsset.MediaType.VIDEO: 100 * 1024 * 1024,
        }
        allowed_content_types = {
            MediaAsset.MediaType.IMAGE: {"image/jpeg", "image/png", "image/webp", "image/gif"},
            MediaAsset.MediaType.AUDIO: {"audio/mpeg", "audio/aac", "audio/ogg"},
            MediaAsset.MediaType.VIDEO: {"video/mp4", "video/webm"},
        }
        allowed_ext = {
            MediaAsset.MediaType.IMAGE: {".jpg", ".jpeg", ".png", ".webp", ".gif"},
            MediaAsset.MediaType.AUDIO: {".mp3", ".aac", ".ogg"},
            MediaAsset.MediaType.VIDEO: {".mp4", ".webm"},
        }

        if uploaded_file.size > limits[media_type]:
            raise serializers.ValidationError("Файл превышает допустимый размер.")

        if content_type not in allowed_content_types[media_type] and not any(name.endswith(ext) for ext in allowed_ext[media_type]):
            raise serializers.ValidationError("Недопустимый формат файла для выбранного типа медиа.")

        return attrs

    def create(self, validated_data):
        f = validated_data["file"]
        validated_data["owner"] = self.context["request"].user
        validated_data["original_name"] = f.name
        validated_data["size_bytes"] = f.size
        return super().create(validated_data)


class QuestionSerializer(serializers.ModelSerializer):
    category = QuestionBankCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=QuestionBankCategory.objects.all(),
        source="category",
        allow_null=True,
        required=False,
        write_only=True,
    )
    media_assets = MediaAssetSerializer(many=True, read_only=True)
    media_asset_ids = serializers.PrimaryKeyRelatedField(
        queryset=MediaAsset.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source="media_assets",
    )

    class Meta:
        model = Question
        fields = [
            "id",
            "owner",
            "category",
            "category_id",
            "question_type",
            "title",
            "prompt",
            "base_points",
            "payload",
            "is_bank_question",
            "media_assets",
            "media_asset_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]

    def validate_category_id(self, value):
        if not value:
            return value
        request = self.context.get("request")
        if request and not request.user.is_superuser and value.owner_id != request.user.id:
            raise serializers.ValidationError("Категория должна принадлежать вам.")
        return value

    def validate_media_assets(self, media_assets):
        request = self.context.get("request")
        if request and not request.user.is_superuser:
            invalid = [asset.id for asset in media_assets if asset.owner_id != request.user.id]
            if invalid:
                raise serializers.ValidationError(f"Недопустимые media asset ids: {invalid}")
        return media_assets

    def create(self, validated_data):
        validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        qtype = attrs.get("question_type") or getattr(self.instance, "question_type", None)
        payload = attrs.get("payload") or getattr(self.instance, "payload", {}) or {}

        if not qtype:
            return attrs

        if qtype == Question.QuestionType.SINGLE:
            options = payload.get("options", [])
            correct = payload.get("correct_option")
            option_ids = {opt.get("id") for opt in options if isinstance(opt, dict)}
            if len(options) < 2:
                raise serializers.ValidationError({"payload": "Для single нужно минимум 2 варианта."})
            if correct is None or correct not in option_ids:
                raise serializers.ValidationError({"payload": "Укажите корректный correct_option для single."})

        elif qtype == Question.QuestionType.MULTIPLE:
            options = payload.get("options", [])
            correct = payload.get("correct_options", [])
            option_ids = {opt.get("id") for opt in options if isinstance(opt, dict)}
            if len(options) < 2:
                raise serializers.ValidationError({"payload": "Для multiple нужно минимум 2 варианта."})
            if not isinstance(correct, list) or len(correct) == 0:
                raise serializers.ValidationError({"payload": "Для multiple укажите список correct_options."})
            if any(item not in option_ids for item in correct):
                raise serializers.ValidationError({"payload": "Все элементы correct_options должны быть в options[].id."})

        elif qtype == Question.QuestionType.TEXT:
            answers = payload.get("correct_answers")
            if not isinstance(answers, list) or len(answers) == 0:
                raise serializers.ValidationError({"payload": "Для text нужен непустой correct_answers."})

        elif qtype == Question.QuestionType.EXTENDED:
            pass

        return attrs
