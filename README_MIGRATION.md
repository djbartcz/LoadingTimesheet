# Migration to Django Monolith

## Old App Status

The old FastAPI + React app has been **stopped and disabled**.

### Service Status
- **Service Name:** `LoadingTimesheetBackend`
- **Status:** STOPPED and DISABLED
- **Auto-start:** Disabled (will not start on boot)

### To Completely Remove the Old Service

If you want to completely uninstall the old Windows service:

1. **Run as Administrator:**
   ```cmd
   cd backend
   uninstall_service.bat
   ```

   Or manually:
   ```cmd
   net stop LoadingTimesheetBackend
   sc delete LoadingTimesheetBackend
   ```

### Old App Files

The old app files are still in:
- `backend/` - FastAPI backend
- `frontend/` - React frontend

These can be kept for reference or deleted later. The new Django app is in:
- `django_app/` - New Django monolith

## New Django App

The new Django monolith app is ready to use:

```bash
cd django_app
pipenv install
pipenv run python manage.py migrate
pipenv run python manage.py runserver
```

Access at: `http://localhost:8000`

## Port Conflict

If port 8000 is still in use by the old app:
1. Check for running processes: `netstat -ano | findstr :8000`
2. Kill the process if needed
3. Or use a different port: `pipenv run python manage.py runserver 8001`

