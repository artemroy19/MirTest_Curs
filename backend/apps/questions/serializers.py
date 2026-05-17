from rest_framework import serializers

from apps.questions.models import Question, QuestionBankCategory


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


class QuestionSerializer(serializers.ModelSerializer):
    category = QuestionBankCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=QuestionBankCategory.objects.all(),
        source="category",
        allow_null=True,
        required=False,
        write_only=True,
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

        if not isinstance(payload, dict):
            raise serializers.ValidationError({"payload": "Payload должен быть JSON-объектом."})

        if qtype == Question.QuestionType.SINGLE:
            options = payload.get("options", [])
            correct = payload.get("correct_option")
            if not isinstance(options, list):
                raise serializers.ValidationError({"payload": "Для single поле options должно быть списком."})
            option_ids = {opt.get("id") for opt in options if isinstance(opt, dict)}
            if len(options) < 2:
                raise serializers.ValidationError({"payload": "Для single нужно минимум 2 варианта."})
            if correct is None or correct not in option_ids:
                raise serializers.ValidationError({"payload": "Укажите корректный correct_option для single."})

        elif qtype == Question.QuestionType.MULTIPLE:
            options = payload.get("options", [])
            correct = payload.get("correct_options", [])
            if not isinstance(options, list):
                raise serializers.ValidationError({"payload": "Для multiple поле options должно быть списком."})
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
