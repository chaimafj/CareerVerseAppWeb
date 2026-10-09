import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("academy", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="lab",
            name="level",
            field=models.PositiveSmallIntegerField(
                choices=[(1, "Beginner"), (2, "Intermediate"), (3, "Advanced")],
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(3),
                ],
            ),
        ),
    ]
