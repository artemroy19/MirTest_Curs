from django.contrib import admin

from apps.groups.models import Group, GroupMembership


admin.site.register(Group)
admin.site.register(GroupMembership)
