from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_rename_user_table"),
        ("groups", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="group",
            table="student_groups",
        ),
        migrations.AlterModelTable(
            name="groupmembership",
            table="group_memberships",
        ),
    ]
