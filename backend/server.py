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
from datetime import datetime, timezone
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

# Load credentials from environment
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

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class Employee(BaseModel):
    id: str
    name: str

class Project(BaseModel):
    id: str
    name: str

class Task(BaseModel):
    name: str

class TimeRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    employee_name: str
    project_id: str
    project_name: str
    task: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[int] = None

class StartTimerRequest(BaseModel):
    employee_id: str
    employee_name: str
    project_id: str
    project_name: str
    task: str

class StopTimerRequest(BaseModel):
    record_id: str
    end_time: str
    duration_seconds: int

# Helper functions
def get_or_create_worksheet(name: str, headers: List[str]):
    """Get or create a worksheet with headers"""
    try:
        worksheet = spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=name, rows=1000, cols=20)
        worksheet.append_row(headers)
    return worksheet

@api_router.get("/")
async def root():
    return {"message": "Timesheet API is running"}

@api_router.get("/employees", response_model=List[Employee])
async def get_employees():
    """Get all employees from Google Sheets"""
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
    """Get all projects from Google Sheets"""
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
    """Get all tasks from Google Sheets"""
    if not spreadsheet:
        raise HTTPException(status_code=500, detail="Google Sheets not configured")
    
    try:
        worksheet = get_or_create_worksheet("Úkony", ["Název"])
        records = worksheet.get_all_records()
        
        # If empty, add default tasks
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

@api_router.post("/timer/start", response_model=TimeRecord)
async def start_timer(request: StartTimerRequest):
    """Start a new timer - stores in MongoDB for real-time tracking"""
    try:
        record = TimeRecord(
            employee_id=request.employee_id,
            employee_name=request.employee_name,
            project_id=request.project_id,
            project_name=request.project_name,
            task=request.task,
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
    """Stop a timer and save to Google Sheets"""
    try:
        # Get the active timer from MongoDB
        timer = await db.active_timers.find_one({"id": request.record_id})
        if not timer:
            raise HTTPException(status_code=404, detail="Timer not found")
        
        # Update timer with end time
        timer['end_time'] = request.end_time
        timer['duration_seconds'] = request.duration_seconds
        
        # Calculate duration in HH:MM:SS format
        hours = request.duration_seconds // 3600
        minutes = (request.duration_seconds % 3600) // 60
        seconds = request.duration_seconds % 60
        duration_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Parse times for Google Sheets
        start_dt = datetime.fromisoformat(timer['start_time'].replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(request.end_time.replace('Z', '+00:00'))
        
        # Save to Google Sheets
        if spreadsheet:
            worksheet = get_or_create_worksheet("Záznamy", [
                "Datum", "Zaměstnanec ID", "Zaměstnanec", "Projekt ID", "Projekt", 
                "Úkon", "Začátek", "Konec", "Doba trvání", "Doba (sekundy)"
            ])
            
            row = [
                start_dt.strftime("%Y-%m-%d"),
                timer['employee_id'],
                timer['employee_name'],
                timer['project_id'],
                timer['project_name'],
                timer['task'],
                start_dt.strftime("%H:%M:%S"),
                end_dt.strftime("%H:%M:%S"),
                duration_formatted,
                request.duration_seconds
            ]
            worksheet.append_row(row)
        
        # Remove from active timers
        await db.active_timers.delete_one({"id": request.record_id})
        
        # Also save to MongoDB for history
        await db.time_records.insert_one(timer)
        
        return {"success": True, "message": "Timer stopped and saved to Google Sheets"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error stopping timer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/timer/active/{employee_id}")
async def get_active_timer(employee_id: str):
    """Get active timer for an employee"""
    try:
        timer = await db.active_timers.find_one({"employee_id": employee_id}, {"_id": 0})
        if timer:
            return timer
        return None
    except Exception as e:
        logging.error(f"Error getting active timer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
