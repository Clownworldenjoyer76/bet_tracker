import decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_userpreferences"),
    ]

    operations = [
        migrations.AddField(
            model_name="userpreferences",
            name="bankroll",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(decimal.Decimal("0.00"))
                ],
            ),
        ),
        migrations.AddField(
            model_name="userpreferences",
            name="kelly_fraction",
            field=models.DecimalField(
                choices=[
                    (decimal.Decimal("1.00"), "Full"),
                    (decimal.Decimal("0.50"), "Half"),
                    (decimal.Decimal("0.25"), "Quarter"),
                ],
                decimal_places=2,
                default=decimal.Decimal("1.00"),
                max_digits=4,
            ),
        ),
    ]
