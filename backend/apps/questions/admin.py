from django.contrib import admin

from apps.questions.models import Question, QuestionBankCategory


admin.site.register(QuestionBankCategory)
admin.site.register(Question)
