from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0004_messagefeedback"),
    ]

    operations = [
        migrations.AlterField(
            model_name="messagefeedback",
            name="reason_code",
            field=models.CharField(
                blank=True,
                choices=[
                    ("positive", "좋아요"),
                    ("incorrect_fact", "사실과 다름"),
                    ("wrong_reference", "참고문헌 오기"),
                    ("too_vague", "모호함"),
                    ("misunderstood", "질문을 이해 못함"),
                    ("other", "기타"),
                ],
                max_length=32,
            ),
        ),
    ]
