from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0007_message_reference_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="concept_graph",
            field=models.TextField(blank=True),
        ),
    ]
