from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0005_alter_messagefeedback_reason_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="llm_score",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=4,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="message",
            name="relevance_score",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=4,
                null=True,
            ),
        ),
    ]
