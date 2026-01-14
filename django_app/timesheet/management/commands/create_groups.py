"""
Django management command to create user groups for role-based access control.

Usage:
    python manage.py create_groups

This creates two groups:
- Admin: Users with access to all features including admin panels
- Standard: Users with access to regular features only (no admin access)
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Create user groups for role-based access control'

    def handle(self, *args, **options):
        self.stdout.write('Creating user groups...\n')

        # Create Admin group
        admin_group, created = Group.objects.get_or_create(name='Admin')
        if created:
            self.stdout.write(
                self.style.SUCCESS('  ✓ Created Admin group')
            )
        else:
            self.stdout.write(
                self.style.WARNING('  Admin group already exists')
            )

        # Create Standard group
        standard_group, created = Group.objects.get_or_create(name='Standard')
        if created:
            self.stdout.write(
                self.style.SUCCESS('  ✓ Created Standard group')
            )
        else:
            self.stdout.write(
                self.style.WARNING('  Standard group already exists')
            )

        self.stdout.write(
            self.style.SUCCESS('\n✓ Groups created successfully!\n')
        )
        self.stdout.write('Usage:')
        self.stdout.write('  1. Go to Django Admin (/admin/)')
        self.stdout.write('  2. Edit a user and assign them to a group:')
        self.stdout.write('     - Admin group: Full access to all features')
        self.stdout.write('     - Standard group: Regular features only')
        self.stdout.write(
            '\nNote: Users in Admin group will have admin access. '
            'Users in Standard group will have regular access only.'
        )
