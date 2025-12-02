# LoadingTimesheet - Czech Loading/Unloading Time Tracking Application

A timesheet tracking application for tracking employee time spent on loading/unloading tasks. Built with FastAPI backend and React frontend, using PostgreSQL for active timer state and Excel files for persistent data storage.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Data Storage](#data-storage)
- [API Endpoints](#api-endpoints)
- [Excel File Structure](#excel-file-structure)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

This application allows employees to:
- Select their name from a list
- Start/stop timers for loading/unloading tasks
- Track time spent on productive (project-based) and non-productive tasks
- Automatically save time records to an Excel file

**Key Technologies:**
- **Backend:** FastAPI (Python)
- **Frontend:** React 19 with React Router
- **Database:** PostgreSQL (for active timers and history)
- **Storage:** Excel files (for persistent data and master data)

---

## 🏗️ Architecture

### **Two-Tier Storage System:**

1. **PostgreSQL** - Fast, real-time operational data
   - Stores active timers while they're running
   - Stores time records history
   - Enables timer persistence across page refreshes

2. **Excel File** - Human-readable persistent storage
   - Stores employees, projects, tasks (master data)
   - Stores completed time records
   - Can be shared and edited by users

### **Data Flow:**

```
User starts timer → PostgreSQL (active_timers)
User stops timer → PostgreSQL (time_records) + Excel file
App reads data → Excel file (employees, projects, tasks)
```

---

## ✨ Features

- ⏱️ **Real-time timer tracking** with persistence
- 👥 **Employee selection** from Excel file
- 📊 **Project-based time tracking** (productive tasks)
- 🔧 **Non-productive task tracking** (maintenance, etc.)
- 📝 **Automatic record saving** to Excel
- 🔄 **Timer state persistence** (survives page refresh)
- 📱 **Responsive design** for mobile devices
- 🖥️ **Windows Service** support for production deployment

---

## 📦 Prerequisites

- **Python 3.12+**
- **Node.js 16+** and npm
- **PostgreSQL** (local installation)
- **Excel file** (.xlsx) for data storage
- **Windows** (for Windows service installation)
- **Administrator privileges** (for Windows service installation)

---

## 🚀 Installation

### **1. Clone the Repository**

```bash
git clone <repository-url>
cd LoadingTimesheet
```

### **2. Backend Setup**

**Using pipenv (Recommended for Windows Service):**

```bash
cd backend
pip install pipenv
pipenv install
```

**Key packages:**
- `fastapi` - Web framework
- `asyncpg` - Async PostgreSQL driver
- `openpyxl` - Excel file manipulation
- `python-dotenv` - Environment variables
- `pywin32` - Windows service support
- `uvicorn` - ASGI server

### **3. Frontend Setup**

```bash
cd frontend
npm install --legacy-peer-deps
npm run build
```

The frontend is built and served by the backend, so you don't need to run it separately.

---

## ⚙️ Configuration

### **1. Backend Configuration**

Create `backend/.env` file (you can copy from `ENV_TEMPLATE.txt`):

```env
# PostgreSQL Database Configuration
DB_NAME=timesheet_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Excel File Configuration
# Use absolute path, avoid spaces in filename (or use quotes)
EXCEL_FILE_PATH=C:\Users\YourName\Desktop\LoadingTimesheet\backend\TimesheetSystem.xlsx

# CORS Configuration (comma-separated origins)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### **2. PostgreSQL Setup**

1. **Create the database:**
   ```sql
   CREATE DATABASE timesheet_db;
   ```

2. **Tables are created automatically** when the server starts, or you can run `setup_postgresql.sql` manually.

### **3. Excel File Setup**

Create an Excel file with these worksheets:

#### **Required Worksheets:**

1. **Zaměstnanci** (Employees)
   ```
   | ID | Jméno      |
   |----|------------|
   | 1  | Jan Novák  |
   ```

2. **Projekty** (Projects)
   ```
   | ID   | Název         |
   |------|---------------|
   | PROJ1| Projekt Alpha|
   ```

3. **Úkony** (Tasks)
   ```
   | Název        |
   |--------------|
   | NAKLÁDKA    |
   | VYKLÁDKA    |
   ```

4. **Neproduktivní úkony** (Non-productive Tasks)
   ```
   | Název     |
   |-----------|
   | ÚKLID     |
   ```

#### **Auto-Created Worksheets:**

These will be created automatically when first used:

5. **Záznamy** (Records) - Productive time records
   ```
   | Datum | Zaměstnanec ID | Zaměstnanec | Projekt ID | Projekt | Úkon | Začátek | Konec | Doba trvání | Doba (sekundy) |
   ```

6. **Neproduktivní záznamy** (Non-productive Records)
   ```
   | Datum | Zaměstnanec ID | Zaměstnanec | Úkon | Začátek | Konec | Doba trvání | Doba (sekundy) |
   ```

---

## 🏃 Running the Application

### **Option 1: Windows Service (Recommended for Production)**

The application can run as a Windows service, automatically starting on system boot.

#### **Installation:**

1. **Open Command Prompt as Administrator:**
   - Right-click Command Prompt → "Run as administrator"

2. **Navigate to backend directory:**
   ```cmd
   cd C:\path\to\LoadingTimesheet\backend
   ```

3. **Run installation script:**
   ```cmd
   install_service.bat
   ```

   This script will:
   - Install pipenv if not already installed
   - Create virtual environment with pipenv
   - Install all dependencies
   - Build React frontend
   - Install pywin32 (required for Windows service)
   - Install and register the Windows service

4. **Configure environment variables:**
   - Edit `backend\.env` file with your settings
   - Make sure PostgreSQL credentials and `EXCEL_FILE_PATH` are set correctly

5. **Start the service:**
   ```cmd
   net start LoadingTimesheetBackend
   ```

#### **Service Management:**

**Start service:**
```cmd
net start LoadingTimesheetBackend
```

**Stop service:**
```cmd
net stop LoadingTimesheetBackend
```

**Check service status:**
```cmd
sc query LoadingTimesheetBackend
```

**View service logs:**
```cmd
type backend\logs\service.log
```

**Uninstall service:**
```cmd
cd backend
uninstall_service.bat
```

**Change service startup type:**
```cmd
sc config LoadingTimesheetBackend start= auto    # Automatic (start on boot)
sc config LoadingTimesheetBackend start= demand  # Manual (start on demand)
sc config LoadingTimesheetBackend start= disabled # Disabled
```

#### **Access Application:**

Once the service is running, open your browser:
- **Application:** `http://localhost:8000`
- **API:** `http://localhost:8000/api/`

---

### **Option 2: Manual Development Mode**

For development and testing, you can run the application manually.

#### **1. Start PostgreSQL**

Make sure PostgreSQL service is running:
```cmd
# Windows
Get-Service postgresql*
```

#### **2. Start Backend Server**

**Using pipenv:**
```bash
cd backend
pipenv install
pipenv run python server.py
```

**Or with uvicorn directly:**
```bash
cd backend
pipenv run uvicorn server:app --reload --port 8000
```

Backend will run on: `http://localhost:8000`

#### **3. Access Application**

Open browser: `http://localhost:8000`

The frontend is served automatically by the backend (from `frontend/build` directory).

---

## 💾 Data Storage

### **Why PostgreSQL?**

PostgreSQL is used for **active timer state management**:

- **Timer Persistence:** When a user refreshes the page, the timer state is preserved
- **Fast Queries:** Sub-millisecond queries vs 200-500ms with Excel
- **Concurrent Users:** Handles multiple employees using the app simultaneously
- **Real-time State:** Active timers need immediate availability

**Tables:**
- `active_timers` - Currently running timers
- `time_records` - Historical timer records

### **Why Excel File?**

Excel files provide:
- **Human-readable** data format
- **Easy sharing** via OneDrive or network share
- **Manual editing** by users (employees, projects, tasks)
- **No API setup** required (simple file I/O)

### **How It Works Together:**

1. **App reads master data** (employees, projects, tasks) from Excel
2. **User starts timer** → Stored in PostgreSQL `active_timers`
3. **User stops timer** → Saved to PostgreSQL `time_records` + Excel file
4. **Excel file syncs** to OneDrive (if using OneDrive sync)
5. **Users can view/edit** Excel file via OneDrive or locally

---

## 🔌 API Endpoints

Base URL: `http://localhost:8000/api`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API health check |
| GET | `/employees` | Get all employees from Excel |
| GET | `/projects` | Get all projects from Excel |
| GET | `/tasks` | Get productive tasks from Excel |
| GET | `/non-productive-tasks` | Get non-productive tasks from Excel |
| POST | `/timer/start` | Start a new timer (stores in PostgreSQL) |
| POST | `/timer/stop` | Stop timer and save to Excel |
| GET | `/timer/active/{employee_id}` | Get active timer for an employee |

### **Example API Calls:**

**Get Employees:**
```bash
curl http://localhost:8000/api/employees
```

**Start Timer:**
```bash
curl -X POST http://localhost:8000/api/timer/start \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "4345",
    "employee_name": "Jan Novák",
    "project_id": "PROJ1",
    "project_name": "Projekt Alpha",
    "task": "NAKLÁDKA"
  }'
```

**Stop Timer:**
```bash
curl -X POST http://localhost:8000/api/timer/stop \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "timer-uuid-here",
    "end_time": "2024-01-15T10:30:00Z",
    "duration_seconds": 3600
  }'
```

---

## 📊 Excel File Structure

### **Master Data Worksheets:**

**Zaměstnanci (Employees):**
- Column A: `ID` - Employee identifier
- Column B: `Jméno` - Employee name

**Projekty (Projects):**
- Column A: `ID` - Project identifier
- Column B: `Název` - Project name

**Úkony (Tasks):**
- Column A: `Název` - Task name

**Neproduktivní úkony (Non-productive Tasks):**
- Column A: `Název` - Task name

### **Record Worksheets:**

**Záznamy (Productive Records):**
- Datum, Zaměstnanec ID, Zaměstnanec, Projekt ID, Projekt, Úkon, Začátek, Konec, Doba trvání, Doba (sekundy)

**Neproduktivní záznamy (Non-productive Records):**
- Datum, Zaměstnanec ID, Zaměstnanec, Úkon, Začátek, Konec, Doba trvání, Doba (sekundy)

---

## 🔧 Sharing Excel File with Users

### **Option 1: OneDrive Sync (Recommended)**

1. **Store Excel file in OneDrive folder**
2. **OneDrive syncs** file to cloud automatically
3. **Share file** with users:
   - Right-click file → "Share"
   - Add user emails
   - Give "Edit" or "View" permissions
4. **Users access** via:
   - Excel Online (web browser) - Best for collaboration
   - OneDrive sync (local file) - For offline editing

### **Option 2: Network Share**

- Place Excel file on network drive
- Share folder with users
- Users access via network path

### **Important Notes:**

- ⚠️ **Close Excel file** when app is running (prevents file locking)
- ✅ **App writes are fast** (milliseconds) - brief lock during writes
- ✅ **Users can edit** between app writes
- ✅ **Excel Online** allows simultaneous editing (recommended)

---

## 🐛 Troubleshooting

### **Backend Issues**

**Error: "Excel file not configured"**
- Check `EXCEL_FILE_PATH` in `backend/.env`
- Verify path is correct and absolute
- Ensure file exists at that location
- Make sure path doesn't have line breaks (should be on one line)

**Error: "Database not configured"**
- Check PostgreSQL is running: `Get-Service postgresql*`
- Verify database credentials in `backend/.env`
- Ensure database exists: `CREATE DATABASE timesheet_db;`
- Check connection: Use `test_database.py` script

**Error: "Permission denied"**
- Close Excel file if open
- Check file permissions
- Ensure write access to file location

**Error: "Module not found"**
```bash
cd backend
pipenv install
```

### **Frontend Issues**

**Frontend not loading:**
- Make sure frontend is built: `cd frontend && npm run build`
- Check `frontend/build` directory exists
- Verify backend is serving static files correctly

**Error: "Cannot connect to backend"**
- Verify backend is running on port 8000
- Check CORS settings in backend `.env`

### **Windows Service Issues**

**Service won't start:**
- Check `backend\.env` file exists and is configured correctly
- Check PostgreSQL is running
- Check Excel file path is correct and file exists
- View logs: `backend\logs\service.log`

**Service stops immediately:**
- Check logs in `backend\logs\service.log`
- Verify PostgreSQL connection string is correct
- Verify Excel file path is accessible
- Check Windows Event Viewer for errors

**View service logs:**
```cmd
type backend\logs\service.log
```

**Check service status:**
```cmd
sc query LoadingTimesheetBackend
```

**Restart service:**
```cmd
net stop LoadingTimesheetBackend
net start LoadingTimesheetBackend
```

### **Excel File Issues**

**Data not appearing:**
- Check worksheet names match exactly (case-sensitive)
- Verify column headers match (`ID`, `Jméno`, `Název`)
- Check backend logs for errors
- Ensure data exists in Excel file

**File locked errors:**
- Close Excel file before running app
- Don't keep file open while app is writing
- Wait a moment if file is being written to

---

## 📝 Project Structure

```
LoadingTimesheet/
├── backend/
│   ├── server.py              # FastAPI server
│   ├── database.py           # PostgreSQL connection and setup
│   ├── excel_client.py       # Excel file operations
│   ├── windows_service.py     # Windows service wrapper
│   ├── install_service.bat    # Service installation script
│   ├── uninstall_service.bat  # Service uninstallation script
│   ├── build_frontend.bat     # Frontend build script
│   ├── Pipfile               # Pipenv dependencies
│   ├── requirements.txt       # Python dependencies
│   ├── ENV_TEMPLATE.txt      # Environment variables template
│   ├── setup_postgresql.sql  # Manual database setup (optional)
│   ├── .env                  # Environment variables (create this)
│   └── logs/                 # Service logs (auto-created)
├── frontend/
│   ├── src/
│   │   ├── App.js           # Main React app
│   │   └── components/      # UI components
│   ├── build/               # Built frontend (served by backend)
│   ├── package.json         # Node dependencies
│   └── .env                 # Frontend env vars (optional)
└── README.md                # This file
```

---

## 🎯 Key Code Locations

### **Backend:**
- **PostgreSQL Connection:** `backend/database.py`
- **Excel Initialization:** `backend/server.py` lines 20-32
- **Timer Start:** `backend/server.py` lines 169-206
- **Timer Stop:** `backend/server.py` lines 209-310
- **Data Retrieval:** `backend/server.py` lines 84-167

### **Frontend:**
- **API Configuration:** `frontend/src/App.js` line 12-13
- **Employee Selection:** `frontend/src/App.js` lines 16-81
- **Timer Logic:** `frontend/src/App.js` lines 85-460

---

## 🔒 Security Notes

- ⚠️ Never commit `.env` files to version control
- ⚠️ Keep PostgreSQL credentials secure
- ⚠️ Use environment-specific configurations
- ⚠️ Configure CORS properly for production
- ⚠️ Consider adding authentication for production use

---

## 📚 Dependencies

### **Backend:**
- `fastapi` - Web framework
- `asyncpg` - Async PostgreSQL driver
- `openpyxl` - Excel file manipulation
- `python-dotenv` - Environment variables
- `pydantic` - Data validation
- `uvicorn` - ASGI server
- `pywin32` - Windows service support

### **Frontend:**
- `react` - UI framework
- `react-router-dom` - Routing
- `axios` - HTTP client
- `shadcn/ui` - UI component library
- `tailwindcss` - Styling

---

## 🚀 Deployment

### **Backend:**
1. Set production environment variables
2. Use production PostgreSQL
3. Configure CORS for production domain
4. Use Windows Service for production deployment

### **Frontend:**
1. Build production bundle: `npm run build`
2. Frontend is automatically served by backend from `frontend/build`
3. Configure backend URL if needed
4. Enable HTTPS for production

---

## 📞 Summary

This application provides a simple, effective way to track employee time for loading/unloading operations:

- ✅ **Easy setup** - Just configure Excel file path and PostgreSQL
- ✅ **No complex APIs** - Simple file-based storage
- ✅ **User-friendly** - Clean React interface
- ✅ **Flexible** - Excel files can be edited manually
- ✅ **Scalable** - PostgreSQL handles concurrent users
- ✅ **Production-ready** - Windows Service support

**Quick Start:**
1. Install dependencies
2. Configure `.env` file
3. Set up Excel file
4. Start PostgreSQL
5. Run backend (or install Windows service)
6. Open `http://localhost:8000`
7. Start tracking time!

---

## 📄 License

[Add your license here]

---

**Need Help?** Check the troubleshooting section or review the code comments for detailed explanations.
