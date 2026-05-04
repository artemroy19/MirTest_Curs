from django.contrib import admin

from apps.attempts.models import AttemptAnswer, TestAttempt


admin.site.register(TestAttempt)
admin.site.register(AttemptAnswer)
