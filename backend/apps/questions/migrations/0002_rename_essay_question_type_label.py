from django.db import migrations, models


def forwards(apps, schema_editor):
    Question = apps.get_model("questions", "Question")
    Question.objects.filter(question_type="essay").update(question_type="extended")


def backwards(apps, schema_editor):
    Question = apps.get_model("questions", "Question")
    Question.objects.filter(question_type="extended").update(question_type="essay")


class Migration(migrations.Migration):
    dependencies = [
        ("questions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name="question",
            name="question_type",
            field=models.CharField(
                choices=[
                    ("single", "Single Choice"),
                    ("multiple", "Multiple Choice"),
                    ("text", "Text Answer"),
                    ("extended", "Extended Question"),
                ],
                max_length=32,
            ),
        ),
    ]
