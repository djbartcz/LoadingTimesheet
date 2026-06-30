from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("timesheet", "0014_add_employee_name_and_part_no_to_clocking"),
    ]

    operations = [
        migrations.AddField(
            model_name="ifsshopoperclocking",
            name="crew_size",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
    ]
