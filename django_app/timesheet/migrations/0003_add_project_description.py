# Generated migration to add project_description field

from django.db import migrations, models


def split_project_names(apps, schema_editor):
    """Split existing project names to extract project_description"""
    Project = apps.get_model('timesheet', 'Project')
    
    for project in Project.objects.all():
        if ' - ' in project.name:
            parts = project.name.split(' - ', 1)
            project.name = parts[0].strip()
            project.project_description = parts[1].strip() if len(parts) > 1 else None
            project.save()


def reverse_split_project_names(apps, schema_editor):
    """Reverse: combine project_description back into name"""
    Project = apps.get_model('timesheet', 'Project')
    
    for project in Project.objects.all():
        if project.project_description:
            project.name = f"{project.name} - {project.project_description}"
            project.project_description = None
            project.save()


class Migration(migrations.Migration):

    dependencies = [
        ('timesheet', '0002_employee_project_task'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='project_description',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.RunPython(
            code=split_project_names,
            reverse_code=reverse_split_project_names,
        ),
    ]
