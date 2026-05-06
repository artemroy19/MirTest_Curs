from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("questions", "0002_rename_essay_question_type_label"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="question",
            name="media_assets",
        ),
        migrations.DeleteModel(
            name="MediaAsset",
        ),
    ]
