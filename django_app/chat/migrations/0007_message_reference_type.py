from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0006_message_llm_score_relevance_score"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="reference_type",
            field=models.CharField(
                blank=True,
                help_text="참고자료 종류 (internal/external 등)",
                max_length=20,
            ),
        ),
    ]
