from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("timesheet", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="timerecord",
            name="ifs_sent",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="timerecord",
            name="ifs_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
