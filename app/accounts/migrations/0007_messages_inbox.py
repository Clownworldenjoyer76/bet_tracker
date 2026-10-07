import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0006_contactmessage"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="contactmessage",
            options={
                "ordering": ("-created_at",),
                "verbose_name": "contact message",
                "verbose_name_plural": "MESSAGES",
            },
        ),
        migrations.AddField(
            model_name="contactmessage",
            name="is_read",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="contactmessage",
            name="email_sent",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="contactmessage",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="contact_messages",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
