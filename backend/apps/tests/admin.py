from django.contrib import admin

from apps.tests.models import Test, TestAssignment, TestQuestion


admin.site.register(Test)
admin.site.register(TestQuestion)
admin.site.register(TestAssignment)
