from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_rename_user_table"),
        ("questions", "0003_remove_question_media_assets_delete_mediaasset"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="questionbankcategory",
            table="question_categories",
        ),
        migrations.AlterModelTable(
            name="question",
            table="questions",
        ),
    ]
