"""
Windows Service Wrapper for LoadingTimesheet Backend
This script allows the FastAPI server to run as a Windows service.
"""

import sys
import os
import logging
import time
from pathlib import Path
import win32serviceutil
import win32service
import win32event
import servicemanager
import uvicorn
import threading

# Add backend directory to path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

# Load environment variables before importing server
from dotenv import load_dotenv
load_dotenv(ROOT_DIR / '.env')

# Import the FastAPI app
from server import app

class LoadingTimesheetService(win32serviceutil.ServiceFramework):
    """Windows Service for LoadingTimesheet Backend"""
    
    _svc_name_ = "LoadingTimesheetBackend"
    _svc_display_name_ = "LoadingTimesheet Backend Service"
    _svc_description_ = "Timesheet tracking application backend API server"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.server_thread = None
        self.server = None
        
        # Configure logging
        log_dir = ROOT_DIR / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "service.log"
        
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def SvcStop(self):
        """Stop the service"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.logger.info("Stopping LoadingTimesheet service...")
        
        # Stop uvicorn server
        if self.server:
            try:
                self.server.should_exit = True
            except Exception as e:
                self.logger.error(f"Error stopping server: {e}")
        
        # Signal stop event
        win32event.SetEvent(self.stop_event)
        
        # Wait for thread to finish
        if self.server_thread:
            self.server_thread.join(timeout=10)
        
        self.logger.info("LoadingTimesheet service stopped")
    
    def SvcDoRun(self):
        """Run the service"""
        try:
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            self.logger.info(f"{self._svc_display_name_} started")
            self.logger.info(f"Python version: {sys.version}")
            self.logger.info(f"Working directory: {os.getcwd()}")
            self.logger.info(f"ROOT_DIR: {ROOT_DIR}")
            
            self.main()
        except Exception as e:
            error_msg = f"Service error: {e}"
            self.logger.error(error_msg, exc_info=True)
            servicemanager.LogErrorMsg(error_msg)
            raise
    
    def main(self):
        """Main service loop"""
        try:
            # Change to backend directory (important for relative paths)
            os.chdir(str(ROOT_DIR))
            self.logger.info(f"Working directory: {os.getcwd()}")
            
            # Get port from environment or default
            port = int(os.environ.get('PORT', 8000))
            host = os.environ.get('HOST', '0.0.0.0')
            
            self.logger.info(f"Starting server on {host}:{port}")
            self.logger.info(f"Frontend build dir exists: {(ROOT_DIR.parent / 'frontend' / 'build').exists()}")
            
            # Configure uvicorn
            config = uvicorn.Config(
                app=app,
                host=host,
                port=port,
                log_config=None,  # Use our own logging
                access_log=False
            )
            
            # Create server instance
            self.server = uvicorn.Server(config)
            
            # Run server in a separate thread
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            
            self.logger.info(f"Server thread started on {host}:{port}")
            
            # Wait for stop event
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
            
            self.logger.info("Service main loop ended")
        except Exception as e:
            self.logger.error(f"Error in main(): {e}", exc_info=True)
            raise
    
    def _run_server(self):
        """Run uvicorn server in thread"""
        try:
            self.logger.info("Starting uvicorn server thread...")
            self.server.run()
            self.logger.info("Uvicorn server thread ended")
        except Exception as e:
            self.logger.error(f"Error running server: {e}", exc_info=True)
            import traceback
            self.logger.error(traceback.format_exc())

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(LoadingTimesheetService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(LoadingTimesheetService)

