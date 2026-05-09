from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_rename_user_table"),
        ("groups", "0002_rename_group_tables"),
        ("questions", "0004_rename_question_tables"),
        ("tests_app", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="test",
            table="tests",
        ),
        migrations.AlterModelTable(
            name="testquestion",
            table="test_questions",
        ),
        migrations.AlterModelTable(
            name="testassignment",
            table="test_assignments",
        ),
    ]
