"""
Django management command to create initial admin and regular user accounts.

NOTE: This command is optional. Users can be managed through Django Admin at /admin/

Usage:
    python manage.py create_users

This creates two users:
- Admin user (is_staff=True) - can access admin features
- Regular user (is_staff=False) - can only access regular features

Credentials are read from environment variables (optional):
- ADMIN_USERNAME (default: 'admin')
- ADMIN_PASSWORD (default: 'admin')
- REGULAR_USERNAME (default: 'user')
- REGULAR_PASSWORD (default: 'user')

If users already exist, they will be updated with new passwords.

For ongoing user management, use Django Admin at /admin/ instead.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import os


class Command(BaseCommand):
    help = 'Create initial admin and regular user accounts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-username',
            type=str,
            help='Admin username (overrides ADMIN_USERNAME env var)',
        )
        parser.add_argument(
            '--admin-password',
            type=str,
            help='Admin password (overrides ADMIN_PASSWORD env var)',
        )
        parser.add_argument(
            '--regular-username',
            type=str,
            help='Regular user username (overrides REGULAR_USERNAME env var)',
        )
        parser.add_argument(
            '--regular-password',
            type=str,
            help='Regular user password (overrides REGULAR_PASSWORD env var)',
        )

    def handle(self, *args, **options):
        # Get credentials from arguments or environment variables
        admin_username = (
            options.get('admin_username') or
            os.environ.get('ADMIN_USERNAME', 'admin')
        )
        admin_password = (
            options.get('admin_password') or
            os.environ.get('ADMIN_PASSWORD', 'admin')
        )
        regular_username = (
            options.get('regular_username') or
            os.environ.get('REGULAR_USERNAME', 'user')
        )
        regular_password = (
            options.get('regular_password') or
            os.environ.get('REGULAR_PASSWORD', 'user')
        )

        self.stdout.write('Creating user accounts...\n')

        # Create or update admin user
        admin_user, created = User.objects.get_or_create(
            username=admin_username,
            defaults={
                'is_staff': True,
                'is_superuser': False,  # Not superuser, just staff
            }
        )
        if not created:
            # User exists, update it
            admin_user.is_staff = True
            admin_user.is_superuser = False
            admin_user.set_password(admin_password)
            admin_user.save()
            self.stdout.write(
                self.style.WARNING(
                    f'  Admin user "{admin_username}" already exists. '
                    f'Password updated.'
                )
            )
        else:
            admin_user.set_password(admin_password)
            admin_user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'  ✓ Created admin user: "{admin_username}" '
                    f'(is_staff=True)'
                )
            )

        # Create or update regular user
        regular_user, created = User.objects.get_or_create(
            username=regular_username,
            defaults={
                'is_staff': False,
                'is_superuser': False,
            }
        )
        if not created:
            # User exists, update it
            regular_user.is_staff = False
            regular_user.is_superuser = False
            regular_user.set_password(regular_password)
            regular_user.save()
            self.stdout.write(
                self.style.WARNING(
                    f'  Regular user "{regular_username}" already exists. '
                    f'Password updated.'
                )
            )
        else:
            regular_user.set_password(regular_password)
            regular_user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'  ✓ Created regular user: "{regular_username}" '
                    f'(is_staff=False)'
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                '\n✓ User accounts created successfully!\n'
            )
        )
        self.stdout.write('Login credentials:')
        self.stdout.write(f'  Admin:   {admin_username} / {admin_password}')
        self.stdout.write(f'  Regular: {regular_username} / {regular_password}')
        self.stdout.write(
            '\nNote: Multiple people can login with the same credentials.'
        )
