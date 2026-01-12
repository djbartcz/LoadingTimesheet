"""
Django management command to sync timesheet data between database and Excel.

Usage:
    python manage.py sync_timesheet
"""

from django.core.management.base import BaseCommand
from timesheet.views import sync_timesheet_data
import sys


class Command(BaseCommand):
    help = (
        'Synchronize timesheet data between database and Excel '
        '(bidirectional sync)'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting timesheet synchronization...')

        result = sync_timesheet_data()

        if result['success']:
            self.stdout.write(
                self.style.SUCCESS(f"\n✓ {result['message']}")
            )
            self.stdout.write(
                f"  - Productive records: {result['productive_count']}"
            )
            self.stdout.write(
                f"  - Non-productive records: "
                f"{result['non_productive_count']}"
            )
            if result.get('upserted_from_excel', 0) > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"  - Upserted from Excel to DB: "
                        f"{result['upserted_from_excel']} "
                        f"(inserted: {result.get('inserted_count', 0)}, "
                        f"updated: {result.get('updated_count', 0)})"
                    )
                )
            self.stdout.write(
                self.style.SUCCESS(
                    '\nSynchronization completed successfully!'
                )
            )
            sys.exit(0)
        else:
            error_msg = result.get('error', 'Unknown error')
            self.stdout.write(
                self.style.ERROR(f"\n✗ Error: {error_msg}")
            )
            sys.exit(1)
