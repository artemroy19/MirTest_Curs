from django.contrib import admin

from apps.questions.models import MediaAsset, Question, QuestionBankCategory


admin.site.register(QuestionBankCategory)
admin.site.register(MediaAsset)
admin.site.register(Question)
