from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from excel_client import init_excel_client
import excel_client as excel_client_module
from database import init_db, close_db
import database as database_module

ROOT_DIR = Path(__file__).parent
PROJECT_ROOT = ROOT_DIR.parent
load_dotenv(ROOT_DIR / '.env')

# Excel file setup
EXCEL_FILE_PATH = os.environ.get('EXCEL_FILE_PATH', '').strip()
# Remove quotes if present
EXCEL_FILE_PATH = EXCEL_FILE_PATH.strip('"').strip("'")
# Handle line breaks in .env file (common issue with spaces in paths)
if EXCEL_FILE_PATH and '\n' in EXCEL_FILE_PATH:
    EXCEL_FILE_PATH = EXCEL_FILE_PATH.split('\n')[0].strip()
if EXCEL_FILE_PATH and '\r' in EXCEL_FILE_PATH:
    EXCEL_FILE_PATH = EXCEL_FILE_PATH.split('\r')[0].strip()
if EXCEL_FILE_PATH:
    try:
        init_excel_client(EXCEL_FILE_PATH)
        logging.info(f"Excel client initialized with file: {EXCEL_FILE_PATH}")
    except Exception as e:
        logging.error(f"Failed to initialize Excel client: {e}")
        logging.error(f"Excel path was: {repr(EXCEL_FILE_PATH)}")
else:
    logging.warning("EXCEL_FILE_PATH not set - Excel features will be disabled")

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

class StopTimerRequest(BaseModel):
    record_id: str
    end_time: str
    duration_seconds: int

# Helper functions (now handled by excel_client)

@api_router.get("/")
async def root():
    return {"message": "Timesheet API is running"}

@api_router.get("/employees", response_model=List[Employee])
async def get_employees():
    """Get all employees from Excel file"""
    if not excel_client_module.excel_client:
        raise HTTPException(status_code=500, detail="Excel file not configured")
    
    try:
        excel_client_module.excel_client.get_or_create_worksheet("Zaměstnanci", ["ID", "Jméno"])
        records = excel_client_module.excel_client.get_worksheet_data("Zaměstnanci")
        employees = [Employee(id=str(r.get('ID', '')), name=str(r.get('Jméno', ''))) for r in records if r.get('ID') and r.get('Jméno')]
        return employees
    except Exception as e:
        logging.error(f"Error fetching employees: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/projects", response_model=List[Project])
async def get_projects():
    """Get all projects from Excel file"""
    if not excel_client_module.excel_client:
        raise HTTPException(status_code=500, detail="Excel file not configured")
    
    try:
        excel_client_module.excel_client.get_or_create_worksheet("Projekty", ["ID", "Název"])
        records = excel_client_module.excel_client.get_worksheet_data("Projekty")
        projects = [Project(id=str(r.get('ID', '')), name=str(r.get('Název', ''))) for r in records if r.get('ID') and r.get('Název')]
        return projects
    except Exception as e:
        logging.error(f"Error fetching projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/tasks", response_model=List[Task])
async def get_tasks():
    """Get all tasks from Excel file"""
    if not excel_client_module.excel_client:
        raise HTTPException(status_code=500, detail="Excel file not configured")
    
    try:
        excel_client_module.excel_client.get_or_create_worksheet("Úkony", ["Název"])
        records = excel_client_module.excel_client.get_worksheet_data("Úkony")
        
        # If empty, add default tasks
        if not records:
            default_tasks = ["NAKLÁDKA", "VYKLÁDKA", "VYCHYSTÁVÁNÍ", "BALENÍ", "MANIPULACE"]
            for task in default_tasks:
                excel_client_module.excel_client.append_row("Úkony", [task])
            tasks = [Task(name=t) for t in default_tasks]
        else:
            tasks = [Task(name=str(r.get('Název', ''))) for r in records if r.get('Název')]
        return tasks
    except Exception as e:
        logging.error(f"Error fetching tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/non-productive-tasks", response_model=List[NonProductiveTask])
async def get_non_productive_tasks():
    """Get all non-productive tasks from Excel file"""
    if not excel_client_module.excel_client:
        raise HTTPException(status_code=500, detail="Excel file not configured")
    
    try:
        excel_client_module.excel_client.get_or_create_worksheet("Neproduktivní úkony", ["Název"])
        records = excel_client_module.excel_client.get_worksheet_data("Neproduktivní úkony")
        
        # If empty, add default non-productive tasks
        if not records:
            default_tasks = ["ÚKLID", "ŠROT", "MANIPULACE", "PŘEVÁŽENÍ"]
            for task in default_tasks:
                excel_client_module.excel_client.append_row("Neproduktivní úkony", [task])
            tasks = [NonProductiveTask(name=t) for t in default_tasks]
        else:
            tasks = [NonProductiveTask(name=str(r.get('Název', ''))) for r in records if r.get('Název')]
        return tasks
    except Exception as e:
        logging.error(f"Error fetching non-productive tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/timer/start", response_model=TimeRecord)
async def start_timer(request: StartTimerRequest):
    """Start a new timer - stores in PostgreSQL for real-time tracking"""
    try:
        if not database_module.pool:
            raise HTTPException(status_code=500, detail="Database not configured")
        
        record = TimeRecord(
            employee_id=request.employee_id,
            employee_name=request.employee_name,
            project_id=request.project_id,
            project_name=request.project_name,
            task=request.task,
            is_non_productive=request.is_non_productive,
            start_time=datetime.now(timezone.utc).isoformat()
        )
        
        # Insert into PostgreSQL
        async with database_module.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO active_timers 
                (id, employee_id, employee_name, project_id, project_name, task, is_non_productive, start_time)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, 
                record.id,
                record.employee_id,
                record.employee_name,
                record.project_id,
                record.project_name,
                record.task,
                record.is_non_productive,
                datetime.fromisoformat(record.start_time.replace('Z', '+00:00'))
            )
        
        return record
    except Exception as e:
        logging.error(f"Error starting timer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/timer/stop")
async def stop_timer(request: StopTimerRequest):
    """Stop a timer and save to Excel file"""
    try:
        if not database_module.pool:
            raise HTTPException(status_code=500, detail="Database not configured")
        
        # Get the active timer from PostgreSQL
        async with database_module.pool.acquire() as conn:
            timer_row = await conn.fetchrow("""
                SELECT id, employee_id, employee_name, project_id, project_name, 
                       task, is_non_productive, start_time
                FROM active_timers
                WHERE id = $1
            """, request.record_id)
            
            if not timer_row:
                raise HTTPException(status_code=404, detail="Timer not found")
            
            # Convert row to dict
            timer = dict(timer_row)
            timer['end_time'] = request.end_time
            timer['duration_seconds'] = request.duration_seconds
        
        # Calculate duration in HH:MM:SS format
        hours = request.duration_seconds // 3600
        minutes = (request.duration_seconds % 3600) // 60
        seconds = request.duration_seconds % 60
        duration_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Parse times for Excel
        start_time = timer['start_time']
        if isinstance(start_time, datetime):
            start_dt = start_time
        else:
            start_dt = datetime.fromisoformat(str(start_time).replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(request.end_time.replace('Z', '+00:00'))
        
        # Save to Excel file - different sheet based on type
        if excel_client_module.excel_client:
            is_non_productive = timer.get('is_non_productive', False)
            
            if is_non_productive:
                # Save to non-productive records sheet
                excel_client_module.excel_client.get_or_create_worksheet("Neproduktivní záznamy", [
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
                excel_client_module.excel_client.append_row("Neproduktivní záznamy", row)
            else:
                # Save to productive records sheet
                excel_client_module.excel_client.get_or_create_worksheet("Záznamy", [
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
                excel_client_module.excel_client.append_row("Záznamy", row)
        
        # Remove from active timers and save to history
        async with database_module.pool.acquire() as conn:
            # Delete from active_timers
            await conn.execute("DELETE FROM active_timers WHERE id = $1", request.record_id)
            
            # Save to time_records
            await conn.execute("""
                INSERT INTO time_records 
                (id, employee_id, employee_name, project_id, project_name, task, 
                 is_non_productive, start_time, end_time, duration_seconds)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                timer['id'],
                timer['employee_id'],
                timer['employee_name'],
                timer.get('project_id'),
                timer.get('project_name'),
                timer['task'],
                timer.get('is_non_productive', False),
                timer['start_time'],
                datetime.fromisoformat(request.end_time.replace('Z', '+00:00')),
                request.duration_seconds
            )
        
        return {"success": True, "message": "Timer stopped and saved to Excel file"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error stopping timer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/timer/active/{employee_id}")
async def get_active_timer(employee_id: str):
    """Get active timer for an employee"""
    try:
        if not pool:
            return None
        
        async with database_module.pool.acquire() as conn:
            timer_row = await conn.fetchrow("""
                SELECT id, employee_id, employee_name, project_id, project_name, 
                       task, is_non_productive, start_time
                FROM active_timers
                WHERE employee_id = $1
            """, employee_id)
            
            if timer_row:
                timer = dict(timer_row)
                # Convert start_time to ISO format string
                if isinstance(timer['start_time'], datetime):
                    timer['start_time'] = timer['start_time'].isoformat()
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

# Serve React frontend static files
frontend_build_dir = PROJECT_ROOT / "frontend" / "build"
if frontend_build_dir.exists():
    # Serve static files (JS, CSS, images, etc.)
    app.mount("/static", StaticFiles(directory=str(frontend_build_dir / "static")), name="static")
    
    # Serve React app for all non-API routes
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        """Serve React app for all non-API routes"""
        # Don't serve API routes
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not found")
        
        # Serve index.html for React Router
        index_file = frontend_build_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        else:
            raise HTTPException(status_code=404, detail="Frontend not built")
    
    logging.info(f"Serving React frontend from: {frontend_build_dir}")
else:
    logging.warning(f"Frontend build directory not found: {frontend_build_dir}")
    logging.warning("Run 'npm run build' in frontend directory to build React app")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        result = await init_db()
        if result:
            logging.info("Database initialized successfully")
        else:
            logging.warning("Database initialization returned None - PostgreSQL features disabled")
    except Exception as e:
        logging.error(f"Failed to initialize database on startup: {e}", exc_info=True)

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown"""
    await close_db()

# Main entry point for running the server
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
