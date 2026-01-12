from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from datetime import timedelta, datetime
import logging
import uuid
import os
from functools import wraps
import pytz
from .models import ActiveTimer, TimeRecord
from django.apps import apps

logger = logging.getLogger(__name__)


def get_excel_timezone():
    """
    Get the timezone to use for Excel exports.
    Returns system local timezone if EXCEL_TIMEZONE is 'system',
    otherwise uses the configured timezone.
    """
    excel_tz = getattr(settings, 'EXCEL_TIMEZONE', settings.TIME_ZONE)
    
    if excel_tz.lower() == 'system':
        # Use system local timezone
        # Get local timezone from system
        from datetime import datetime, timezone as dt_timezone
        local_tz = datetime.now(dt_timezone.utc).astimezone().tzinfo
        # Convert to pytz timezone if needed
        if isinstance(local_tz, pytz.BaseTzInfo):
            return local_tz
        else:
            # Try to get timezone name and convert
            tz_name = str(local_tz)
            # Common Windows timezone mappings
            tz_mapping = {
                'Central European Standard Time': 'Europe/Prague',
                'Central European Time': 'Europe/Prague',
                'Central Europe Standard Time': 'Europe/Prague',
                'W. Europe Standard Time': 'Europe/Berlin',
                'GMT Standard Time': 'Europe/London',
                'Eastern Standard Time': 'America/New_York',
            }
            if tz_name in tz_mapping:
                return pytz.timezone(tz_mapping[tz_name])
            # Default to Django TIME_ZONE if can't determine
            logger.warning(
                f"Could not determine system timezone '{tz_name}', "
                f"using Django TIME_ZONE"
            )
            return pytz.timezone(settings.TIME_ZONE)
    else:
        # Use configured timezone
        try:
            return pytz.timezone(excel_tz)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(
                f"Unknown timezone '{excel_tz}', using Django TIME_ZONE"
            )
            return pytz.timezone(settings.TIME_ZONE)


def convert_to_excel_timezone(dt):
    """
    Convert a timezone-aware datetime to the Excel timezone for display.
    If datetime is naive, assumes it's in Django's TIME_ZONE.
    """
    if timezone.is_naive(dt):
        # Make naive datetime timezone-aware using Django's TIME_ZONE
        dt = timezone.make_aware(dt, pytz.timezone(settings.TIME_ZONE))
    
    # Convert to Excel timezone
    excel_tz = get_excel_timezone()
    return dt.astimezone(excel_tz)


# Login decorator
def login_required(view_func):
    """Decorator to require login for views"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('authenticated'):
            # Redirect to login with next parameter to return after login
            from django.urls import reverse
            login_url = reverse('login')
            current_path = request.get_full_path()
            return redirect(f"{login_url}?next={current_path}")
        return view_func(request, *args, **kwargs)
    return wrapper

# Get Excel client from app config
def get_excel_client():
    timesheet_config = apps.get_app_config('timesheet')
    return getattr(timesheet_config, 'excel_client', None)


def get_today_start():
    now = timezone.now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def get_week_start():
    now = timezone.now()
    start = now - timedelta(days=now.weekday())
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


def format_duration(seconds):
    """Format seconds to human readable duration"""
    if not seconds:
        return '0min'
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    if hrs > 0:
        return f"{hrs}h {mins}min"
    return f"{mins}min"


def format_time(seconds):
    """Format seconds to HH:MM:SS"""
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"


# Login View
def login_view(request):
    """Login page - handles authentication"""
    # Get credentials from environment variables
    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin')
    
    # If already authenticated, redirect to home
    if request.session.get('authenticated'):
        return redirect('employee_selection')
    
    # Handle POST request (login form submission)
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        
        if username == admin_username and password == admin_password:
            request.session['authenticated'] = True
            # Redirect to next page if specified, otherwise to employee selection
            next_url = request.GET.get('next', 'employee_selection')
            # Validate next_url to prevent open redirects
            if next_url and not next_url.startswith('http'):
                return redirect(next_url)
            return redirect('employee_selection')
        else:
            return render(request, 'timesheet/login.html', {
                'error': 'Nesprávné přihlašovací údaje'
            })
    
    # GET request - show login form
    return render(request, 'timesheet/login.html')


# Logout View
def logout_view(request):
    """Logout - clears session"""
    request.session.flush()
    return redirect('login')


# Employee Selection Page
@login_required
def employee_selection(request):
    """Main page - employee selection"""
    excel_client = get_excel_client()
    employees = []
    active_timers = {}
    error_message = None
    
    if not excel_client:
        logger.warning("Excel client not available - employees list will be empty")
        error_message = "Excel file not configured. Please set EXCEL_FILE_PATH in environment variables."
    else:
        try:
            excel_client.get_or_create_worksheet("Zaměstnanci", ["ID", "Jméno"])
            records = excel_client.get_worksheet_data("Zaměstnanci")
            
            if not records:
                logger.warning("No employees found in Excel file")
                error_message = "No employees found in Excel file. Please add employees to 'Zaměstnanci' worksheet."
            else:
                employees = [
                    {"id": str(r.get('ID', '')).strip(), "name": str(r.get('Jméno', '')).strip()}
                    for r in records 
                    if r.get('ID') and r.get('Jméno') and str(r.get('ID', '')).strip() and str(r.get('Jméno', '')).strip()
                ]
                employees.sort(key=lambda x: x['name'])
                logger.info(f"Loaded {len(employees)} employees from Excel")
        except Exception as e:
            logger.error(f"Error fetching employees from Excel: {e}", exc_info=True)
            error_message = f"Error loading employees: {str(e)}"
    
    # Get active timers
    try:
        timers = ActiveTimer.objects.all()
        for timer in timers:
            active_timers[timer.employee_id] = {
                'id': timer.id,
                'employee_id': timer.employee_id,
                'employee_name': timer.employee_name,
                'project_id': timer.project_id,
                'project_name': timer.project_name,
                'task': timer.task,
                'is_non_productive': timer.is_non_productive,
                'is_break': timer.is_break,
                'start_time': timer.start_time.isoformat(),
            }
        logger.debug(f"Found {len(active_timers)} active timers")
    except Exception as e:
        logger.error(f"Error fetching active timers: {e}", exc_info=True)
    
    return render(request, 'timesheet/employee_selection.html', {
        'employees': employees,
        'active_timers': active_timers,
        'error_message': error_message,
    })


# Timer Page
@login_required
def timer_page(request, employee_id):
    """Timer page for specific employee"""
    excel_client = get_excel_client()
    
    # Get employee info
    employees = []
    employee = None
    if excel_client:
        try:
            excel_client.get_or_create_worksheet("Zaměstnanci", ["ID", "Jméno"])
            records = excel_client.get_worksheet_data("Zaměstnanci")
            employees = [
                {"id": str(r.get('ID', '')), "name": str(r.get('Jméno', ''))}
                for r in records if r.get('ID') and r.get('Jméno')
            ]
            employee = next((e for e in employees if e['id'] == employee_id), None)
        except Exception as e:
            logger.error(f"Error fetching employees: {e}")
    
    if not employee:
        return redirect('employee_selection')
    
    # Get projects, tasks
    projects = []
    tasks = []
    non_productive_tasks = []
    
    if excel_client:
        try:
            # Projects
            excel_client.get_or_create_worksheet("Projekty", ["ID", "Název"])
            records = excel_client.get_worksheet_data("Projekty")
            projects = [
                {"id": str(r.get('ID', '')).strip(), "name": str(r.get('Název', '')).strip()}
                for r in records 
                if r.get('ID') and r.get('Název') and str(r.get('ID', '')).strip() and str(r.get('Název', '')).strip()
            ]
            projects.sort(key=lambda x: x['name'])
            logger.debug(f"Loaded {len(projects)} projects from Excel")
            
            # Tasks
            excel_client.get_or_create_worksheet("Úkony", ["Název"])
            records = excel_client.get_worksheet_data("Úkony")
            if not records:
                logger.info("No tasks found, creating default tasks")
                default_tasks = ["NAKLÁDKA", "VYKLÁDKA", "VYCHYSTÁVÁNÍ", "BALENÍ", "MANIPULACE"]
                for task in default_tasks:
                    excel_client.append_row("Úkony", [task])
                tasks = [{"name": t} for t in default_tasks]
            else:
                tasks = [
                    {"name": str(r.get('Název', '')).strip()} 
                    for r in records 
                    if r.get('Název') and str(r.get('Název', '')).strip()
                ]
            logger.debug(f"Loaded {len(tasks)} tasks from Excel")
            
            # Non-productive tasks
            excel_client.get_or_create_worksheet("Neproduktivní úkony", ["Název"])
            records = excel_client.get_worksheet_data("Neproduktivní úkony")
            if not records:
                logger.info("No non-productive tasks found, creating default tasks")
                default_tasks = ["ÚKLID", "ŠROT", "MANIPULACE", "PŘEVÁŽENÍ"]
                for task in default_tasks:
                    excel_client.append_row("Neproduktivní úkony", [task])
                non_productive_tasks = [{"name": t} for t in default_tasks]
            else:
                non_productive_tasks = [
                    {"name": str(r.get('Název', '')).strip()} 
                    for r in records 
                    if r.get('Název') and str(r.get('Název', '')).strip()
                ]
            logger.debug(f"Loaded {len(non_productive_tasks)} non-productive tasks from Excel")
        except Exception as e:
            logger.error(f"Error fetching projects/tasks from Excel: {e}", exc_info=True)
    else:
        logger.warning("Excel client not available - projects and tasks will be empty")
    
    # Get active timer
    active_timer = None
    try:
        timer = ActiveTimer.objects.get(employee_id=employee_id)
        active_timer = {
            'id': timer.id,
            'employee_id': timer.employee_id,
            'employee_name': timer.employee_name,
            'project_id': timer.project_id,
            'project_name': timer.project_name,
            'task': timer.task,
            'is_non_productive': timer.is_non_productive,
            'is_break': timer.is_break,
            'start_time': timer.start_time.isoformat(),
        }
    except ActiveTimer.DoesNotExist:
        pass
    
    # Get last task
    last_task = None
    try:
        record = TimeRecord.objects.filter(employee_id=employee_id, end_time__isnull=False).order_by('-end_time').first()
        if record:
            last_task = {
                'id': record.id,
                'employee_id': record.employee_id,
                'employee_name': record.employee_name,
                'project_id': record.project_id,
                'project_name': record.project_name,
                'task': record.task,
                'is_non_productive': record.is_non_productive,
                'start_time': record.start_time.isoformat(),
                'end_time': record.end_time.isoformat() if record.end_time else None,
                'duration_seconds': record.duration_seconds,
            }
    except Exception as e:
        logger.error(f"Error fetching last task: {e}")
    
    # Get summary
    today_start = get_today_start()
    week_start = get_week_start()
    
    today_records = TimeRecord.objects.filter(
        employee_id=employee_id,
        end_time__gte=today_start
    ).order_by('-end_time')[:100]
    
    week_records = TimeRecord.objects.filter(
        employee_id=employee_id,
        end_time__gte=week_start
    ).order_by('-end_time')[:500]
    
    today_prod = sum(r.duration_seconds or 0 for r in today_records if not r.is_non_productive)
    today_nonprod = sum(r.duration_seconds or 0 for r in today_records if r.is_non_productive)
    week_prod = sum(r.duration_seconds or 0 for r in week_records if not r.is_non_productive)
    week_nonprod = sum(r.duration_seconds or 0 for r in week_records if r.is_non_productive)
    
    summary = {
        'today': {
            'total_seconds': today_prod + today_nonprod,
            'productive_seconds': today_prod,
            'non_productive_seconds': today_nonprod,
            'break_seconds': 0,
            'records': [
                {
                    'id': r.id,
                    'task': r.task,
                    'project_name': r.project_name,
                    'is_non_productive': r.is_non_productive,
                    'duration_seconds': r.duration_seconds,
                }
                for r in today_records[:10]
            ]
        },
        'week': {
            'total_seconds': week_prod + week_nonprod,
            'productive_seconds': week_prod,
            'non_productive_seconds': week_nonprod,
            'break_seconds': 0,
        }
    }
    
    # Check if this is an AJAX request for timer sync
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        timer_data = None
        if active_timer:
            timer_data = {
                'id': active_timer['id'],
                'start_time': active_timer['start_time'],
                'is_non_productive': active_timer['is_non_productive'],
                'is_break': active_timer['is_break'],
                'employee_id': active_timer.get('employee_id', employee_id),
            }
        return JsonResponse({
            'has_timer': active_timer is not None,
            'timer': timer_data,
        })
    
    return render(request, 'timesheet/timer_page.html', {
        'employee': employee,
        'projects': projects,
        'tasks': [{'name': t['name']} for t in tasks],
        'non_productive_tasks': [{'name': t['name']} for t in non_productive_tasks],
        'active_timer': active_timer,
        'last_task': last_task,
        'summary': summary,
    })


# Form-based Views
@login_required
def start_timer(request, employee_id):
    """Start a new timer - handles form submission"""
    if request.method != 'POST':
        return redirect('timer_page', employee_id=employee_id)
    
    try:
        # Get employee info
        excel_client = get_excel_client()
        employee = None
        if excel_client:
            excel_client.get_or_create_worksheet("Zaměstnanci", ["ID", "Jméno"])
            records = excel_client.get_worksheet_data("Zaměstnanci")
            employees = [
                {"id": str(r.get('ID', '')), "name": str(r.get('Jméno', ''))}
                for r in records if r.get('ID') and r.get('Jméno')
            ]
            employee = next((e for e in employees if e['id'] == employee_id), None)
        
        if not employee:
            return redirect('employee_selection')
        
        mode = request.POST.get('mode', 'productive')
        project_id = request.POST.get('project_id', '')
        project_name = request.POST.get('project_name', '')
        task = request.POST.get('task', '')
        non_productive_task = request.POST.get('non_productive_task', '')
        
        # Check if already has active timer
        if ActiveTimer.objects.filter(employee_id=employee_id).exists():
            return redirect('timer_page', employee_id=employee_id)
        
        if mode == 'productive':
            if not project_id or not task:
                return redirect('timer_page', employee_id=employee_id)
            is_non_productive = False
            final_task = task
        else:
            if not non_productive_task:
                return redirect('timer_page', employee_id=employee_id)
            is_non_productive = True
            final_task = non_productive_task
            project_id = None
            project_name = None
        
        # Create active timer with timezone-aware datetime
        start_time = timezone.now()
        record = ActiveTimer(
            id=str(uuid.uuid4()),
            employee_id=employee_id,
            employee_name=employee['name'],
            project_id=project_id,
            project_name=project_name,
            task=final_task,
            is_non_productive=is_non_productive,
            is_break=False,
            start_time=start_time,  # Already timezone-aware from timezone.now()
        )
        record.save()
        logger.info(f"Started timer for {employee['name']}: {final_task} at {start_time}")
        
        return redirect('timer_page', employee_id=employee_id)
    except Exception as e:
        logger.error(f"Error starting timer: {e}")
        return redirect('timer_page', employee_id=employee_id)


@login_required
def stop_timer(request, employee_id):
    """Stop a timer and save to database, then Excel - handles form submission"""
    if request.method != 'POST':
        return redirect('timer_page', employee_id=employee_id)
    
    try:
        # Get active timer
        timer = get_object_or_404(ActiveTimer, employee_id=employee_id)
        
        # Use timezone-aware datetime for accurate calculation
        end_time = timezone.now()
        
        # Ensure both times are timezone-aware for accurate calculation
        if timezone.is_naive(timer.start_time):
            start_time = timezone.make_aware(timer.start_time)
        else:
            start_time = timer.start_time
        
        # Calculate duration accurately
        time_delta = end_time - start_time
        duration_seconds = int(time_delta.total_seconds())
        
        # Validate duration (should be positive)
        if duration_seconds < 0:
            logger.warning(f"Negative duration detected for timer {timer.id}, using 0")
            duration_seconds = 0
        
        # Format duration
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        seconds = duration_seconds % 60
        duration_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Save to database FIRST (this is the source of truth)
        # Database is primary storage - ensures data is never lost
        time_record = TimeRecord(
            id=timer.id,
            employee_id=timer.employee_id,
            employee_name=timer.employee_name,
            project_id=timer.project_id,
            project_name=timer.project_name,
            task=timer.task,
            is_non_productive=timer.is_non_productive,
            start_time=start_time,  # Use timezone-aware start_time
            end_time=end_time,
            duration_seconds=duration_seconds,
        )
        time_record.save()
        logger.info(f"✓ Saved time record to database: {timer.employee_name} - {duration_seconds}s ({duration_formatted})")
        
        # Then save to Excel (for reporting/export)
        # Excel is secondary storage - if this fails, data is still safe in database
        excel_client = get_excel_client()
        if excel_client:
            try:
                # Convert to Excel timezone (local/system time) for display
                start_dt_excel = convert_to_excel_timezone(start_time)
                end_dt_excel = convert_to_excel_timezone(end_time)
                
                if timer.is_non_productive:
                    excel_client.get_or_create_worksheet("Neproduktivní záznamy", [
                        "Datum", "Zaměstnanec ID", "Zaměstnanec", "Úkon",
                        "Začátek", "Konec", "Doba trvání", "Doba (sekundy)"
                    ])
                    row = [
                        start_dt_excel.strftime("%Y-%m-%d"),
                        timer.employee_id,
                        timer.employee_name,
                        timer.task,
                        start_dt_excel.strftime("%H:%M:%S"),
                        end_dt_excel.strftime("%H:%M:%S"),
                        duration_formatted,
                        duration_seconds
                    ]
                    excel_client.append_row("Neproduktivní záznamy", row)
                    logger.info(f"✓ Exported to Excel: Neproduktivní záznamy")
                else:
                    excel_client.get_or_create_worksheet("Záznamy", [
                        "Datum", "Zaměstnanec ID", "Zaměstnanec", "Projekt ID", "Projekt",
                        "Úkon", "Začátek", "Konec", "Doba trvání", "Doba (sekundy)"
                    ])
                    row = [
                        start_dt_excel.strftime("%Y-%m-%d"),
                        timer.employee_id,
                        timer.employee_name,
                        timer.project_id or '',
                        timer.project_name or '',
                        timer.task,
                        start_dt_excel.strftime("%H:%M:%S"),
                        end_dt_excel.strftime("%H:%M:%S"),
                        duration_formatted,
                        duration_seconds
                    ]
                    excel_client.append_row("Záznamy", row)
                    logger.info(f"✓ Exported to Excel: Záznamy")
            except Exception as excel_error:
                logger.error(f"⚠ Error exporting to Excel (record already saved to DB): {excel_error}")
                # Don't fail if Excel export fails - data is already in database
        
        # Delete active timer
        timer.delete()
        
        return redirect('timer_page', employee_id=employee_id)
    except Exception as e:
        logger.error(f"Error stopping timer: {e}")
        return redirect('timer_page', employee_id=employee_id)


# Admin Dashboard
@login_required
def admin_dashboard(request):
    """Admin dashboard"""
    
    excel_client = get_excel_client()
    employees = []
    
    if not excel_client:
        logger.warning("Excel client not available - admin dashboard will show no employees")
    else:
        try:
            excel_client.get_or_create_worksheet("Zaměstnanci", ["ID", "Jméno"])
            records = excel_client.get_worksheet_data("Zaměstnanci")
            employees = [
                {"id": str(r.get('ID', '')).strip(), "name": str(r.get('Jméno', '')).strip()}
                for r in records 
                if r.get('ID') and r.get('Jméno') and str(r.get('ID', '')).strip() and str(r.get('Jméno', '')).strip()
            ]
            logger.info(f"Admin dashboard: Loaded {len(employees)} employees from Excel")
        except Exception as e:
            logger.error(f"Error fetching employees for admin dashboard: {e}", exc_info=True)
    
    today_start = get_today_start()
    week_start = get_week_start()
    
    try:
        active_timers = ActiveTimer.objects.all()
        today_records = TimeRecord.objects.filter(end_time__gte=today_start)[:1000]
        week_records = TimeRecord.objects.filter(end_time__gte=week_start)[:5000]
        
        employee_stats = []
        active_map = {t.employee_id: t for t in active_timers}
        
        for emp in employees:
            emp_id = emp['id']
            emp_today = [r for r in today_records if r.employee_id == emp_id]
            emp_week = [r for r in week_records if r.employee_id == emp_id]
            
            today_secs = sum(r.duration_seconds or 0 for r in emp_today)
            week_secs = sum(r.duration_seconds or 0 for r in emp_week)
            
            active = active_map.get(emp_id)
            
            employee_stats.append({
                'employee_id': emp_id,
                'employee_name': emp['name'],
                'today_seconds': today_secs,
                'week_seconds': week_secs,
                'is_working': active is not None,
                'is_on_break': False,
                'is_non_productive': active.is_non_productive if active else False,
                'current_task': active.task if active else None,
                'current_project': active.project_name if active else None,
                'start_time': active.start_time.isoformat() if active else None,
            })
    except Exception as e:
        logger.error(f"Error fetching time records for admin dashboard: {e}", exc_info=True)
        employee_stats = []
    
    employee_stats.sort(key=lambda x: (not x['is_working'], x['employee_name']))
    
    total_today = sum(s['today_seconds'] for s in employee_stats)
    total_week = sum(s['week_seconds'] for s in employee_stats)
    working_count = sum(1 for s in employee_stats if s['is_working'])
    
    # Alerts for long running timers (> 4 hours)
    alerts = []
    for timer in active_timers:
        elapsed = (timezone.now() - timer.start_time).total_seconds()
        if elapsed > 4 * 3600:
            alerts.append({
                'type': 'long_running',
                'employee_name': timer.employee_name,
                'task': timer.task,
                'hours': round(elapsed / 3600, 1),
                'message': f"{timer.employee_name} pracuje už {round(elapsed/3600, 1)} hodin"
            })
    
    return render(request, 'timesheet/admin_dashboard.html', {
        'employees': employee_stats,
        'summary': {
            'total_employees': len(employees),
            'working_now': working_count,
            'on_break': 0,
            'today_total_seconds': total_today,
            'week_total_seconds': total_week,
        },
        'alerts': alerts,
    })


def parse_excel_datetime(date_str, time_str):
    """
    Parse date and time strings from Excel and convert to timezone-aware datetime.
    Excel stores dates as YYYY-MM-DD and times as HH:MM:SS in Excel timezone.
    """
    try:
        # Parse date and time
        if isinstance(date_str, datetime):
            # If Excel already parsed it as datetime
            dt = date_str
        else:
            date_part = str(date_str).strip()
            time_part = str(time_str).strip() if time_str else "00:00:00"
            
            # Combine date and time
            dt_str = f"{date_part} {time_part}"
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        
        # Make timezone-aware using Excel timezone
        excel_tz = get_excel_timezone()
        if timezone.is_naive(dt):
            dt = excel_tz.localize(dt)
        
        # Convert to Django timezone
        django_tz = pytz.timezone(settings.TIME_ZONE)
        dt = dt.astimezone(django_tz)
        
        return dt
    except Exception as e:
        logger.error(f"Error parsing Excel datetime '{date_str} {time_str}': {e}")
        return None


def create_record_key(employee_id, start_time, task, is_non_productive):
    """Create a unique key for matching records"""
    # Use employee_id, start_time (rounded to minute), task, and type
    start_minute = start_time.replace(second=0, microsecond=0)
    return f"{employee_id}|{start_minute.isoformat()}|{task}|{is_non_productive}"


def sync_timesheet_data():
    """
    Sync function: reads Excel, upserts to DB, then replaces Excel with all DB data.
    This ensures Excel always matches the database exactly.
    
    Process:
    1. Read all records from Excel
    2. Upsert each Excel record to database (update if exists, insert if not)
    3. Clear Excel sheets
    4. Write all database records back to Excel
    
    Returns:
        dict: {
            'success': bool,
            'productive_count': int,
            'non_productive_count': int,
            'upserted_from_excel': int,
            'message': str,
            'error': str (if failed)
        }
    """
    excel_client = get_excel_client()
    if not excel_client:
        return {
            'success': False,
            'error': 'Excel client not available. Please set EXCEL_FILE_PATH in environment variables.'
        }
    
    try:
        # Step 1: Read all records from Excel and upsert to database
        upserted_from_excel = 0
        updated_count = 0
        inserted_count = 0
        added_to_excel = 0
        
        # Read productive records from Excel and upsert to database
        try:
            excel_productive = excel_client.get_worksheet_data("Záznamy")
            for row in excel_productive:
                try:
                    employee_id = str(row.get('Zaměstnanec ID', '')).strip()
                    if not employee_id:
                        continue
                    
                    date_str = row.get('Datum')
                    start_time_str = row.get('Začátek')
                    end_time_str = row.get('Konec')
                    
                    if not date_str or not start_time_str or not end_time_str:
                        continue
                    
                    start_dt = parse_excel_datetime(date_str, start_time_str)
                    end_dt = parse_excel_datetime(date_str, end_time_str)
                    
                    if not start_dt or not end_dt:
                        continue
                    
                    # If end time is before start time, assume it's next day
                    if end_dt < start_dt:
                        end_dt = end_dt + timedelta(days=1)
                    
                    task = str(row.get('Úkon', '')).strip()
                    employee_name = str(row.get('Zaměstnanec', '')).strip()
                    project_id = str(row.get('Projekt ID', '')).strip() or None
                    project_name = str(row.get('Projekt', '')).strip() or None
                    duration_seconds = row.get('Doba (sekundy)')
                    
                    if duration_seconds is None:
                        # Calculate from start/end times
                        duration_seconds = int((end_dt - start_dt).total_seconds())
                    
                    # Upsert to database using composite key (employee_id, start_time rounded to minute, task, is_non_productive)
                    # Round start_time to minute for matching - use a 1-minute window
                    start_minute = start_dt.replace(second=0, microsecond=0)
                    start_window_start = start_minute
                    start_window_end = start_minute + timedelta(minutes=1)
                    
                    # Query for records matching the composite key within the minute window
                    matching_records = TimeRecord.objects.filter(
                        employee_id=employee_id,
                        start_time__gte=start_window_start,
                        start_time__lt=start_window_end,
                        task=task,
                        is_non_productive=False
                    )
                    
                    if matching_records.exists():
                        # Update the first matching record (if duplicates exist, update first one)
                        time_record = matching_records.first()
                        time_record.employee_name = employee_name
                        time_record.project_id = project_id
                        time_record.project_name = project_name
                        time_record.start_time = start_dt
                        time_record.end_time = end_dt
                        time_record.duration_seconds = duration_seconds
                        time_record.save()
                        created = False
                        logger.debug(f"Updated existing productive record: {employee_name} - {task} at {start_dt}")
                    else:
                        # No matching record found, create new one
                        time_record = TimeRecord(
                            id=str(uuid.uuid4()),
                            employee_id=employee_id,
                            employee_name=employee_name,
                            project_id=project_id,
                            project_name=project_name,
                            task=task,
                            is_non_productive=False,
                            start_time=start_dt,
                            end_time=end_dt,
                            duration_seconds=duration_seconds
                        )
                        time_record.save()
                        created = True
                        logger.debug(f"Created new productive record: {employee_name} - {task} at {start_dt}")
                    
                    if created:
                        inserted_count += 1
                        logger.debug(f"Inserted record from Excel to DB: {employee_name} - {task}")
                    else:
                        updated_count += 1
                        logger.debug(f"Updated record from Excel to DB: {employee_name} - {task}")
                    
                    upserted_from_excel += 1
                except Exception as e:
                    logger.warning(f"Error processing Excel productive record: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Error reading productive records from Excel: {e}")
        
        # Read non-productive records from Excel and upsert to database
        try:
            excel_non_productive = excel_client.get_worksheet_data("Neproduktivní záznamy")
            for row in excel_non_productive:
                try:
                    employee_id = str(row.get('Zaměstnanec ID', '')).strip()
                    if not employee_id:
                        continue
                    
                    date_str = row.get('Datum')
                    start_time_str = row.get('Začátek')
                    end_time_str = row.get('Konec')
                    
                    if not date_str or not start_time_str or not end_time_str:
                        continue
                    
                    start_dt = parse_excel_datetime(date_str, start_time_str)
                    end_dt = parse_excel_datetime(date_str, end_time_str)
                    
                    if not start_dt or not end_dt:
                        continue
                    
                    # If end time is before start time, assume it's next day
                    if end_dt < start_dt:
                        end_dt = end_dt + timedelta(days=1)
                    
                    task = str(row.get('Úkon', '')).strip()
                    employee_name = str(row.get('Zaměstnanec', '')).strip()
                    duration_seconds = row.get('Doba (sekundy)')
                    
                    if duration_seconds is None:
                        # Calculate from start/end times
                        duration_seconds = int((end_dt - start_dt).total_seconds())
                    
                    # Upsert to database using composite key
                    start_minute = start_dt.replace(second=0, microsecond=0)
                    start_window_start = start_minute
                    start_window_end = start_minute + timedelta(minutes=1)
                    
                    # Query for records matching the composite key within the minute window
                    matching_records = TimeRecord.objects.filter(
                        employee_id=employee_id,
                        start_time__gte=start_window_start,
                        start_time__lt=start_window_end,
                        task=task,
                        is_non_productive=True
                    )
                    
                    if matching_records.exists():
                        # Update the first matching record (if duplicates exist, update first one)
                        time_record = matching_records.first()
                        time_record.employee_name = employee_name
                        time_record.project_id = None
                        time_record.project_name = None
                        time_record.start_time = start_dt
                        time_record.end_time = end_dt
                        time_record.duration_seconds = duration_seconds
                        time_record.save()
                        created = False
                        logger.debug(f"Updated existing non-productive record: {employee_name} - {task} at {start_dt}")
                    else:
                        # No matching record found, create new one
                        time_record = TimeRecord(
                            id=str(uuid.uuid4()),
                            employee_id=employee_id,
                            employee_name=employee_name,
                            project_id=None,
                            project_name=None,
                            task=task,
                            is_non_productive=True,
                            start_time=start_dt,
                            end_time=end_dt,
                            duration_seconds=duration_seconds
                        )
                        time_record.save()
                        created = True
                        logger.debug(f"Created new non-productive record: {employee_name} - {task} at {start_dt}")
                    
                    if created:
                        inserted_count += 1
                        logger.debug(f"Inserted non-productive record from Excel to DB: {employee_name} - {task}")
                    else:
                        updated_count += 1
                        logger.debug(f"Updated non-productive record from Excel to DB: {employee_name} - {task}")
                    
                    upserted_from_excel += 1
                except Exception as e:
                    logger.warning(f"Error processing Excel non-productive record: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Error reading non-productive records from Excel: {e}")
        
        logger.info(f"Upserted {upserted_from_excel} records from Excel to DB (inserted: {inserted_count}, updated: {updated_count})")
        
        # Step 2: Get all records from database
        all_db_records = TimeRecord.objects.filter(end_time__isnull=False).order_by('start_time')
        
        # Step 3: Clear Excel sheets and write all database records
        productive_records = []
        non_productive_records = []
        
        for record in all_db_records:
            # Convert to Excel timezone for display
            start_dt_excel = convert_to_excel_timezone(record.start_time)
            end_dt_excel = convert_to_excel_timezone(record.end_time)
            
            # Format duration
            duration_seconds = record.duration_seconds or 0
            hours = duration_seconds // 3600
            minutes = (duration_seconds % 3600) // 60
            seconds = duration_seconds % 60
            duration_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            if record.is_non_productive:
                row_data = [
                    start_dt_excel.strftime("%Y-%m-%d"),
                    record.employee_id,
                    record.employee_name,
                    record.task,
                    start_dt_excel.strftime("%H:%M:%S"),
                    end_dt_excel.strftime("%H:%M:%S"),
                    duration_formatted,
                    duration_seconds
                ]
                non_productive_records.append(row_data)
            else:
                # Productive records have project info
                productive_row = [
                    start_dt_excel.strftime("%Y-%m-%d"),
                    record.employee_id,
                    record.employee_name,
                    record.project_id or '',
                    record.project_name or '',
                    record.task,
                    start_dt_excel.strftime("%H:%M:%S"),
                    end_dt_excel.strftime("%H:%M:%S"),
                    duration_formatted,
                    duration_seconds
                ]
                productive_records.append(productive_row)
        
        # Replace Excel worksheets with all database records
        excel_client.replace_worksheet_data(
            "Neproduktivní záznamy",
            ["Datum", "Zaměstnanec ID", "Zaměstnanec", "Úkon",
             "Začátek", "Konec", "Doba trvání", "Doba (sekundy)"],
            non_productive_records
        )
        logger.info(f"Replaced Excel with {len(non_productive_records)} non-productive records")
        
        excel_client.replace_worksheet_data(
            "Záznamy",
            ["Datum", "Zaměstnanec ID", "Zaměstnanec", "Projekt ID", "Projekt",
             "Úkon", "Začátek", "Konec", "Doba trvání", "Doba (sekundy)"],
            productive_records
        )
        logger.info(f"Replaced Excel with {len(productive_records)} productive records")
        
        total_productive = len(productive_records)
        total_non_productive = len(non_productive_records)
        
        return {
            'success': True,
            'message': f'Úspěšně synchronizováno: {total_productive} produktivních záznamů, {total_non_productive} neproduktivních záznamů v DB. Upsertováno z Excel do DB: {upserted_from_excel} (vloženo: {inserted_count}, aktualizováno: {updated_count})',
            'productive_count': total_productive,
            'non_productive_count': total_non_productive,
            'upserted_from_excel': upserted_from_excel,
            'inserted_count': inserted_count,
            'updated_count': updated_count,
        }
        
    except Exception as e:
        logger.error(f"Error syncing to Excel: {e}", exc_info=True)
        return {
            'success': False,
            'error': f'Chyba při synchronizaci: {str(e)}'
        }


# Sync Database and Excel (bidirectional)
@login_required
def sync_to_excel(request):
    """
    Bidirectional sync: ensures all records in Excel exist in DB and vice versa.
    Reads from both sources, merges them, and updates both.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    result = sync_timesheet_data()
    
    if result['success']:
        return JsonResponse(result)
    else:
        return JsonResponse(result, status=500)
