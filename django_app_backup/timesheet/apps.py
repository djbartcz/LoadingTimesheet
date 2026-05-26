from django.apps import AppConfig
import os
import logging
from pathlib import Path
from .excel_client import ExcelClient


class TimesheetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'timesheet'
    
    def ready(self):
        """Initialize Excel client when app is ready"""
        # Environment variables are already loaded by settings.py
        excel_file_path = os.environ.get('EXCEL_FILE_PATH', '').strip()
        
        # Remove quotes if present
        excel_file_path = excel_file_path.strip('"').strip("'")
        
        # Handle line breaks in .env file - join all lines and clean up
        if excel_file_path:
            # Remove all newlines and carriage returns, then strip
            excel_file_path = excel_file_path.replace('\n', '').replace('\r', '').strip()
            # Fix Windows path escape sequence issues
            # The \a in \admsoc gets interpreted as \x07 (bell character)
            # Replace it back to \a, then reconstruct the path properly
            if '\x07' in excel_file_path or '\\x07' in excel_file_path:
                # Path was corrupted by escape sequence - reconstruct it
                excel_file_path = excel_file_path.replace('\x07', 'a').replace('\\x07', 'a')
                # Reconstruct the path - look for pattern like Users\x07dmsoc and fix it
                import re
                excel_file_path = re.sub(r'Users[\\/]\x07?dmsoc', r'Users\admsoc', excel_file_path)
                excel_file_path = excel_file_path.replace('\\x07', 'a')
        
        # If empty, try to find Excel file in django_app directory
        if not excel_file_path:
            BASE_DIR = Path(__file__).resolve().parent.parent  # django_app directory
            # Look for Excel files in django_app directory
            excel_files = list(BASE_DIR.glob('*.xlsx'))
            if excel_files:
                excel_file_path = excel_files[0].name  # Just the filename for relative path
                logging.info(f"Auto-detected Excel file: {excel_file_path}")
        
        if excel_file_path:
            try:
                # Get base directory (django_app folder)
                BASE_DIR = Path(__file__).resolve().parent.parent
                
                # First, try to find Excel file in django_app directory (simplest approach)
                excel_files_in_dir = list(BASE_DIR.glob('*.xlsx'))
                if excel_files_in_dir:
                    # Use the first Excel file found in django_app directory
                    file_path = excel_files_in_dir[0]
                    logging.info(f"Using Excel file found in django_app directory: {file_path}")
                else:
                    # Handle the path from .env file
                    # Check if path looks absolute (starts with drive letter)
                    is_absolute = len(excel_file_path) > 1 and excel_file_path[1] == ':'
                    
                    if is_absolute:
                        # Absolute path - fix escape sequences
                        clean_path = excel_file_path.replace('\x07', 'a').replace('\\x07', 'a')
                        clean_path = clean_path.replace('Usersadmsoc', 'Users\\admsoc')
                        # Fix double backslashes
                        clean_path = clean_path.replace('\\\\', '\\')
                        file_path = Path(clean_path)
                    else:
                        # Relative path - resolve from django_app directory
                        file_path = (BASE_DIR / excel_file_path).resolve()
                
                logging.info(f"Resolved Excel file path: {file_path}")
                logging.info(f"File exists: {file_path.exists()}")
                
                if not file_path.exists():
                    logging.warning(f"Excel file not found at: {file_path}")
                    # List available Excel files for debugging
                    all_excel_files = list(BASE_DIR.glob('*.xlsx'))
                    if all_excel_files:
                        logging.info(f"Available Excel files in django_app: {[str(f.name) for f in all_excel_files]}")
                    self.excel_client = None
                else:
                    self.excel_client = ExcelClient(str(file_path))
                    logging.info(f"✓ Excel client initialized successfully with file: {file_path}")
            except Exception as e:
                logging.error(f"Failed to initialize Excel client: {e}", exc_info=True)
                self.excel_client = None
        else:
            logging.warning("EXCEL_FILE_PATH not set in environment variables")
            logging.warning("Excel features will be disabled. Set EXCEL_FILE_PATH in django_app/.env file")
            self.excel_client = None
