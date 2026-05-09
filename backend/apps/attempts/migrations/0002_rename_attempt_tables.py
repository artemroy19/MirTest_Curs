from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_rename_user_table"),
        ("tests_app", "0002_rename_test_tables"),
        ("attempts", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="testattempt",
            table="test_attempts",
        ),
        migrations.AlterModelTable(
            name="attemptanswer",
            table="attempt_answers",
        ),
    ]
