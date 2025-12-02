from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import gspread
from google.oauth2.service_account import Credentials
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Google Sheets setup
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

google_creds_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', '')
SPREADSHEET_ID = os.environ.get('GOOGLE_SPREADSHEET_ID', '')

gc = None
spreadsheet = None

def init_google_sheets():
    global gc, spreadsheet
    if google_creds_json and SPREADSHEET_ID:
        try:
            creds_dict = json.loads(google_creds_json)
            credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            gc = gspread.authorize(credentials)
            spreadsheet = gc.open_by_key(SPREADSHEET_ID)
            logging.info("Google Sheets connection established")
        except Exception as e:
            logging.error(f"Failed to connect to Google Sheets: {e}")

init_google_sheets()

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Models
class Employee(BaseModel):
    id: str
    name: str

class Project(BaseModel):
    id: str
    name: str

class Task(BaseModel):
    name: str

class NonProductiveTask(BaseModel):
    name: str

class TimeRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    employee_name: str
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    task: str
    is_non_productive: bool = False
    is_break: bool = False
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[int] = None

class StartTimerRequest(BaseModel):
    employee_id: str
    employee_name: str
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    task: str
    is_non_productive: bool = False
    is_break: bool = False

class StopTimerRequest(BaseModel):
    record_id: str
    end_time: str
    duration_seconds: int

class DailySummary(BaseModel):
    date: str
    total_seconds: int
    productive_seconds: int
    non_productive_seconds: int
    break_seconds: int
    records: List[dict]

class EmployeeStats(BaseModel):
    employee_id: str
    employee_name: str
    today_seconds: int
    week_seconds: int
    is_working: bool
    current_task: Optional[str] = None
    current_project: Optional[str] = None
    last_task: Optional[dict] = None

# Helper functions
def get_or_create_worksheet(name: str, headers: List[str]):
    try:
        worksheet = spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=name, rows=1000, cols=20)
        worksheet.append_row(headers)
    return worksheet

def get_today_start():
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)

def get_week_start():
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=now.weekday())
    return start.replace(hour=0, minute=0, second=0, microsecond=0)

@api_router.get("/")
async def root():
    return {"message": "Timesheet API is running"}

@api_router.get("/employees", response_model=List[Employee])
async def get_employees():
    if not spreadsheet:
        raise HTTPException(status_code=500, detail="Google Sheets not configured")
    try:
        worksheet = get_or_create_worksheet("Zaměstnanci", ["ID", "Jméno"])
        records = worksheet.get_all_records()
        employees = [Employee(id=str(r.get('ID', '')), name=str(r.get('Jméno', ''))) for r in records if r.get('ID') and r.get('Jméno')]
        return employees
    except Exception as e:
        logging.error(f"Error fetching employees: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/projects", response_model=List[Project])
async def get_projects():
    if not spreadsheet:
        raise HTTPException(status_code=500, detail="Google Sheets not configured")
    try:
        worksheet = get_or_create_worksheet("Projekty", ["ID", "Název"])
        records = worksheet.get_all_records()
        projects = [Project(id=str(r.get('ID', '')), name=str(r.get('Název', ''))) for r in records if r.get('ID') and r.get('Název')]
        return projects
    except Exception as e:
        logging.error(f"Error fetching projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/tasks", response_model=List[Task])
async def get_tasks():
    if not spreadsheet:
        raise HTTPException(status_code=500, detail="Google Sheets not configured")
    try:
        worksheet = get_or_create_worksheet("Úkony", ["Název"])
        records = worksheet.get_all_records()
        if not records:
            default_tasks = ["NAKLÁDKA", "VYKLÁDKA", "VYCHYSTÁVÁNÍ", "BALENÍ", "MANIPULACE"]
            for task in default_tasks:
                worksheet.append_row([task])
            tasks = [Task(name=t) for t in default_tasks]
        else:
            tasks = [Task(name=str(r.get('Název', ''))) for r in records if r.get('Název')]
        return tasks
    except Exception as e:
        logging.error(f"Error fetching tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/non-productive-tasks", response_model=List[NonProductiveTask])
async def get_non_productive_tasks():
    if not spreadsheet:
        raise HTTPException(status_code=500, detail="Google Sheets not configured")
    try:
        worksheet = get_or_create_worksheet("Neproduktivní úkony", ["Název"])
        records = worksheet.get_all_records()
        if not records:
            default_tasks = ["ÚKLID", "ŠROT", "MANIPULACE", "PŘEVÁŽENÍ"]
            for task in default_tasks:
                worksheet.append_row([task])
            tasks = [NonProductiveTask(name=t) for t in default_tasks]
        else:
            tasks = [NonProductiveTask(name=str(r.get('Název', ''))) for r in records if r.get('Název')]
        return tasks
    except Exception as e:
        logging.error(f"Error fetching non-productive tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/timer/start", response_model=TimeRecord)
async def start_timer(request: StartTimerRequest):
    try:
        record = TimeRecord(
            employee_id=request.employee_id,
            employee_name=request.employee_name,
            project_id=request.project_id,
            project_name=request.project_name,
            task=request.task,
            is_non_productive=request.is_non_productive,
            is_break=request.is_break,
            start_time=datetime.now(timezone.utc).isoformat()
        )
        doc = record.model_dump()
        await db.active_timers.insert_one(doc)
        return record
    except Exception as e:
        logging.error(f"Error starting timer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/timer/stop")
async def stop_timer(request: StopTimerRequest):
    try:
        timer = await db.active_timers.find_one({"id": request.record_id})
        if not timer:
            raise HTTPException(status_code=404, detail="Timer not found")
        
        timer['end_time'] = request.end_time
        timer['duration_seconds'] = request.duration_seconds
        
        hours = request.duration_seconds // 3600
        minutes = (request.duration_seconds % 3600) // 60
        seconds = request.duration_seconds % 60
        duration_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        start_dt = datetime.fromisoformat(timer['start_time'].replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(request.end_time.replace('Z', '+00:00'))
        
        if spreadsheet:
            is_non_productive = timer.get('is_non_productive', False)
            is_break = timer.get('is_break', False)
            
            if is_break:
                worksheet = get_or_create_worksheet("Přestávky", [
                    "Datum", "Zaměstnanec ID", "Zaměstnanec", "Typ",
                    "Začátek", "Konec", "Doba trvání", "Doba (sekundy)"
                ])
                row = [
                    start_dt.strftime("%Y-%m-%d"),
                    timer['employee_id'],
                    timer['employee_name'],
                    timer['task'],
                    start_dt.strftime("%H:%M:%S"),
                    end_dt.strftime("%H:%M:%S"),
                    duration_formatted,
                    request.duration_seconds
                ]
            elif is_non_productive:
                worksheet = get_or_create_worksheet("Neproduktivní záznamy", [
                    "Datum", "Zaměstnanec ID", "Zaměstnanec", "Úkon",
                    "Začátek", "Konec", "Doba trvání", "Doba (sekundy)"
                ])
                row = [
                    start_dt.strftime("%Y-%m-%d"),
                    timer['employee_id'],
                    timer['employee_name'],
                    timer['task'],
                    start_dt.strftime("%H:%M:%S"),
                    end_dt.strftime("%H:%M:%S"),
                    duration_formatted,
                    request.duration_seconds
                ]
            else:
                worksheet = get_or_create_worksheet("Záznamy", [
                    "Datum", "Zaměstnanec ID", "Zaměstnanec", "Projekt ID", "Projekt",
                    "Úkon", "Začátek", "Konec", "Doba trvání", "Doba (sekundy)"
                ])
                row = [
                    start_dt.strftime("%Y-%m-%d"),
                    timer['employee_id'],
                    timer['employee_name'],
                    timer.get('project_id', ''),
                    timer.get('project_name', ''),
                    timer['task'],
                    start_dt.strftime("%H:%M:%S"),
                    end_dt.strftime("%H:%M:%S"),
                    duration_formatted,
                    request.duration_seconds
                ]
            worksheet.append_row(row)
        
        await db.active_timers.delete_one({"id": request.record_id})
        await db.time_records.insert_one(timer)
        
        return {"success": True, "message": "Timer stopped and saved to Google Sheets"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error stopping timer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/timer/active/{employee_id}")
async def get_active_timer(employee_id: str):
    try:
        timer = await db.active_timers.find_one({"employee_id": employee_id}, {"_id": 0})
        return timer
    except Exception as e:
        logging.error(f"Error getting active timer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/timers/active")
async def get_all_active_timers():
    try:
        timers = await db.active_timers.find({}, {"_id": 0}).to_list(1000)
        return timers
    except Exception as e:
        logging.error(f"Error getting active timers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/employee/{employee_id}/last-task")
async def get_last_task(employee_id: str):
    """Get the last completed task for quick repeat"""
    try:
        last_record = await db.time_records.find_one(
            {"employee_id": employee_id, "is_break": {"$ne": True}},
            {"_id": 0},
            sort=[("end_time", -1)]
        )
        return last_record
    except Exception as e:
        logging.error(f"Error getting last task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/employee/{employee_id}/history")
async def get_employee_history(employee_id: str, days: int = 7):
    """Get employee's work history for the last N days"""
    try:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        records = await db.time_records.find(
            {
                "employee_id": employee_id,
                "end_time": {"$gte": start_date.isoformat()}
            },
            {"_id": 0}
        ).sort("end_time", -1).to_list(100)
        return records
    except Exception as e:
        logging.error(f"Error getting employee history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/employee/{employee_id}/summary")
async def get_employee_summary(employee_id: str):
    """Get employee's daily summary"""
    try:
        today_start = get_today_start()
        week_start = get_week_start()
        
        # Today's records
        today_records = await db.time_records.find(
            {
                "employee_id": employee_id,
                "end_time": {"$gte": today_start.isoformat()}
            },
            {"_id": 0}
        ).to_list(100)
        
        # Week's records
        week_records = await db.time_records.find(
            {
                "employee_id": employee_id,
                "end_time": {"$gte": week_start.isoformat()}
            },
            {"_id": 0}
        ).to_list(500)
        
        def calc_totals(records):
            productive = sum(r.get('duration_seconds', 0) for r in records if not r.get('is_non_productive') and not r.get('is_break'))
            non_productive = sum(r.get('duration_seconds', 0) for r in records if r.get('is_non_productive') and not r.get('is_break'))
            breaks = sum(r.get('duration_seconds', 0) for r in records if r.get('is_break'))
            return productive, non_productive, breaks
        
        today_prod, today_nonprod, today_breaks = calc_totals(today_records)
        week_prod, week_nonprod, week_breaks = calc_totals(week_records)
        
        return {
            "today": {
                "total_seconds": today_prod + today_nonprod,
                "productive_seconds": today_prod,
                "non_productive_seconds": today_nonprod,
                "break_seconds": today_breaks,
                "records": today_records
            },
            "week": {
                "total_seconds": week_prod + week_nonprod,
                "productive_seconds": week_prod,
                "non_productive_seconds": week_nonprod,
                "break_seconds": week_breaks
            }
        }
    except Exception as e:
        logging.error(f"Error getting employee summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/admin/dashboard")
async def get_admin_dashboard():
    """Get admin dashboard data with all employees stats"""
    try:
        today_start = get_today_start()
        week_start = get_week_start()
        
        # Get all active timers
        active_timers = await db.active_timers.find({}, {"_id": 0}).to_list(1000)
        active_map = {t['employee_id']: t for t in active_timers}
        
        # Get all employees from sheets
        employees = []
        if spreadsheet:
            try:
                worksheet = spreadsheet.worksheet("Zaměstnanci")
                records = worksheet.get_all_records()
                employees = [{"id": str(r.get('ID', '')), "name": str(r.get('Jméno', ''))} for r in records if r.get('ID')]
            except:
                pass
        
        # Get today's and week's records for all
        today_records = await db.time_records.find(
            {"end_time": {"$gte": today_start.isoformat()}},
            {"_id": 0}
        ).to_list(1000)
        
        week_records = await db.time_records.find(
            {"end_time": {"$gte": week_start.isoformat()}},
            {"_id": 0}
        ).to_list(5000)
        
        # Get last task for each employee
        last_tasks = {}
        for emp in employees:
            last = await db.time_records.find_one(
                {"employee_id": emp['id'], "is_break": {"$ne": True}},
                {"_id": 0},
                sort=[("end_time", -1)]
            )
            if last:
                last_tasks[emp['id']] = last
        
        # Build stats per employee
        employee_stats = []
        for emp in employees:
            emp_id = emp['id']
            today_emp = [r for r in today_records if r.get('employee_id') == emp_id and not r.get('is_break')]
            week_emp = [r for r in week_records if r.get('employee_id') == emp_id and not r.get('is_break')]
            
            today_secs = sum(r.get('duration_seconds', 0) for r in today_emp)
            week_secs = sum(r.get('duration_seconds', 0) for r in week_emp)
            
            active = active_map.get(emp_id)
            
            employee_stats.append({
                "employee_id": emp_id,
                "employee_name": emp['name'],
                "today_seconds": today_secs,
                "week_seconds": week_secs,
                "is_working": active is not None,
                "is_on_break": active.get('is_break', False) if active else False,
                "is_non_productive": active.get('is_non_productive', False) if active else False,
                "current_task": active.get('task') if active else None,
                "current_project": active.get('project_name') if active else None,
                "start_time": active.get('start_time') if active else None,
                "last_task": last_tasks.get(emp_id)
            })
        
        # Sort: working first, then by name
        employee_stats.sort(key=lambda x: (not x['is_working'], x['employee_name']))
        
        # Calculate totals
        total_today = sum(s['today_seconds'] for s in employee_stats)
        total_week = sum(s['week_seconds'] for s in employee_stats)
        working_count = sum(1 for s in employee_stats if s['is_working'])
        on_break_count = sum(1 for s in employee_stats if s.get('is_on_break'))
        
        # Long running alerts (> 4 hours)
        alerts = []
        for timer in active_timers:
            start = datetime.fromisoformat(timer['start_time'].replace('Z', '+00:00'))
            elapsed = (datetime.now(timezone.utc) - start).total_seconds()
            if elapsed > 4 * 3600:  # 4 hours
                alerts.append({
                    "type": "long_running",
                    "employee_name": timer['employee_name'],
                    "task": timer.get('task'),
                    "hours": round(elapsed / 3600, 1),
                    "message": f"{timer['employee_name']} pracuje už {round(elapsed/3600, 1)} hodin"
                })
        
        return {
            "employees": employee_stats,
            "summary": {
                "total_employees": len(employees),
                "working_now": working_count,
                "on_break": on_break_count,
                "today_total_seconds": total_today,
                "week_total_seconds": total_week
            },
            "alerts": alerts,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logging.error(f"Error getting admin dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
