import { useState, useEffect, useCallback, useRef } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";
import { Play, Square, Clock, User, Briefcase, Package, AlertTriangle, Wrench, WifiOff, CloudOff, RefreshCw, X, ChevronRight, Search, Timer } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Offline Storage Keys
const STORAGE_KEYS = {
  ACTIVE_TIMER: 'timesheet_active_timer',
  PENDING_STOPS: 'timesheet_pending_stops',
  SELECTED_EMPLOYEE: 'selectedEmployee'
};

// Offline Queue Manager
const OfflineQueue = {
  getPendingStops: () => {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.PENDING_STOPS);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  },
  
  addPendingStop: (stopData) => {
    const pending = OfflineQueue.getPendingStops();
    pending.push(stopData);
    localStorage.setItem(STORAGE_KEYS.PENDING_STOPS, JSON.stringify(pending));
  },
  
  removePendingStop: (recordId) => {
    const pending = OfflineQueue.getPendingStops();
    const filtered = pending.filter(p => p.record_id !== recordId);
    localStorage.setItem(STORAGE_KEYS.PENDING_STOPS, JSON.stringify(filtered));
  },
  
  clearPendingStops: () => {
    localStorage.removeItem(STORAGE_KEYS.PENDING_STOPS);
  }
};

// Local Timer Storage
const TimerStorage = {
  save: (timerData) => {
    localStorage.setItem(STORAGE_KEYS.ACTIVE_TIMER, JSON.stringify(timerData));
  },
  
  get: () => {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.ACTIVE_TIMER);
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  },
  
  clear: () => {
    localStorage.removeItem(STORAGE_KEYS.ACTIVE_TIMER);
  }
};

// Online Status Hook
const useOnlineStatus = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);
  
  return isOnline;
};

// Connection Status Component
const ConnectionStatus = ({ isOnline, pendingCount }) => {
  if (isOnline && pendingCount === 0) return null;
  
  return (
    <div className={`connection-status ${isOnline ? 'pending' : 'offline'}`} data-testid="connection-status">
      {!isOnline ? (
        <>
          <WifiOff size={18} />
          <span>Offline režim</span>
        </>
      ) : pendingCount > 0 ? (
        <>
          <RefreshCw size={18} className="spinning" />
          <span>Synchronizuji ({pendingCount})...</span>
        </>
      ) : null}
    </div>
  );
};

// Fullscreen Project Picker Modal
const ProjectPickerModal = ({ isOpen, onClose, projects, onSelect, selectedProject }) => {
  const [searchTerm, setSearchTerm] = useState('');
  
  if (!isOpen) return null;
  
  const filteredProjects = projects.filter(p => 
    p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.id.toLowerCase().includes(searchTerm.toLowerCase())
  );
  
  return (
    <div className="fullscreen-modal" data-testid="project-modal">
      <div className="modal-header">
        <h2>Vyberte projekt</h2>
        <button className="modal-close" onClick={onClose} data-testid="modal-close">
          <X size={28} />
        </button>
      </div>
      
      <div className="modal-search">
        <Search size={20} />
        <input
          type="text"
          placeholder="Hledat projekt..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          data-testid="project-search"
        />
      </div>
      
      <div className="modal-list">
        {filteredProjects.map((project) => (
          <button
            key={project.id}
            className={`modal-list-item ${selectedProject?.id === project.id ? 'selected' : ''}`}
            onClick={() => {
              onSelect(project);
              onClose();
            }}
            data-testid={`project-item-${project.id}`}
          >
            <div className="item-content">
              <span className="item-id">{project.id}</span>
              <span className="item-name">{project.name}</span>
            </div>
            <ChevronRight size={24} />
          </button>
        ))}
        {filteredProjects.length === 0 && (
          <div className="modal-empty">
            <p>Žádné projekty nenalezeny</p>
          </div>
        )}
      </div>
    </div>
  );
};

// Employee Selection Page
const EmployeeSelection = () => {
  const [employees, setEmployees] = useState([]);
  const [activeTimers, setActiveTimers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const isOnline = useOnlineStatus();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [employeesRes, timersRes] = await Promise.all([
          axios.get(`${API}/employees`, { timeout: 10000 }),
          axios.get(`${API}/timers/active`, { timeout: 10000 }).catch(() => ({ data: [] }))
        ]);
        
        // Sort alphabetically by name
        const sorted = employeesRes.data.sort((a, b) => a.name.localeCompare(b.name, 'cs'));
        setEmployees(sorted);
        setActiveTimers(timersRes.data || []);
        localStorage.setItem('cached_employees', JSON.stringify(sorted));
        setError(null);
      } catch (e) {
        console.error("Error fetching employees:", e);
        const cached = localStorage.getItem('cached_employees');
        if (cached) {
          setEmployees(JSON.parse(cached));
          toast.info("Načteno z cache (offline)");
        } else {
          setError("Nepodařilo se načíst zaměstnance");
          toast.error("Nepodařilo se načíst zaměstnance");
        }
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    
    // Refresh active timers every 30 seconds
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${API}/timers/active`, { timeout: 10000 });
        setActiveTimers(res.data || []);
      } catch (e) {
        console.error("Error refreshing active timers:", e);
      }
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);
  
  const getActiveTimer = (employeeId) => {
    return activeTimers.find(t => t.employee_id === employeeId);
  };

  const handleSelectEmployee = (employee) => {
    localStorage.setItem(STORAGE_KEYS.SELECTED_EMPLOYEE, JSON.stringify(employee));
    navigate(`/employee/${employee.id}`);
  };

  if (loading) {
    return (
      <div className="loading-container" data-testid="loading-spinner">
        <div className="spinner"></div>
        <p>Načítání...</p>
      </div>
    );
  }

  return (
    <div className="employee-selection" data-testid="employee-selection-page">
      <ConnectionStatus isOnline={isOnline} pendingCount={0} />
      
      <div className="header">
        <Clock className="header-icon" />
        <h1>Časomíra nakládky</h1>
        <p>Vyberte své jméno</p>
      </div>
      
      <div className="employees-list">
        {employees.length === 0 ? (
          <div className="empty-state" data-testid="no-employees">
            <User size={48} />
            <p>{error || "Žádní zaměstnanci"}</p>
            <span>Přidejte zaměstnance do Google Sheets</span>
          </div>
        ) : (
          employees.map((employee) => {
            const activeTimer = getActiveTimer(employee.id);
            return (
              <button
                key={employee.id}
                className={`employee-list-item ${activeTimer ? 'working' : ''}`}
                onClick={() => handleSelectEmployee(employee)}
                data-testid={`employee-btn-${employee.id}`}
              >
                <User className="employee-icon" />
                <div className="employee-info-content">
                  <span className="employee-name">{employee.name}</span>
                  {activeTimer && (
                    <div className="employee-status">
                      <Timer size={14} className="status-icon" />
                      <span>{activeTimer.project_name || activeTimer.task}</span>
                    </div>
                  )}
                </div>
                {activeTimer ? (
                  <div className="working-badge">
                    <span className="pulse-dot"></span>
                    Pracuje
                  </div>
                ) : (
                  <ChevronRight className="chevron" />
                )}
              </button>
            );
          })
        )}
      </div>
    </div>
  );
};

// Timer Page
const TimerPage = () => {
  const { employeeId } = useParams();
  const navigate = useNavigate();
  const isOnline = useOnlineStatus();
  const [employee, setEmployee] = useState(null);
  const [projects, setProjects] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [nonProductiveTasks, setNonProductiveTasks] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [selectedTask, setSelectedTask] = useState(null);
  const [selectedNonProductiveTask, setSelectedNonProductiveTask] = useState(null);
  const [mode, setMode] = useState('productive');
  const [isRunning, setIsRunning] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [activeRecord, setActiveRecord] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pendingStops, setPendingStops] = useState([]);
  const [syncing, setSyncing] = useState(false);
  const [showProjectModal, setShowProjectModal] = useState(false);
  const syncingRef = useRef(false);

  // Load employee from localStorage
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEYS.SELECTED_EMPLOYEE);
    if (stored) {
      const emp = JSON.parse(stored);
      if (emp.id === employeeId) {
        setEmployee(emp);
      } else {
        navigate('/');
      }
    } else {
      navigate('/');
    }
  }, [employeeId, navigate]);

  // Load pending stops count
  useEffect(() => {
    setPendingStops(OfflineQueue.getPendingStops());
  }, []);

  // Sync pending stops when online
  useEffect(() => {
    const syncPendingStops = async () => {
      if (!isOnline || syncingRef.current) return;
      
      const pending = OfflineQueue.getPendingStops();
      if (pending.length === 0) return;
      
      syncingRef.current = true;
      setSyncing(true);
      
      for (const stopData of pending) {
        try {
          await axios.post(`${API}/timer/stop`, stopData, { timeout: 15000 });
          OfflineQueue.removePendingStop(stopData.record_id);
          toast.success(`Synchronizováno: ${stopData.task || 'záznam'}`);
        } catch (e) {
          console.error("Sync failed:", e);
        }
      }
      
      setPendingStops(OfflineQueue.getPendingStops());
      syncingRef.current = false;
      setSyncing(false);
    };
    
    syncPendingStops();
  }, [isOnline]);

  // Fetch projects, tasks and non-productive tasks
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [projectsRes, tasksRes, nonProductiveRes] = await Promise.all([
          axios.get(`${API}/projects`, { timeout: 10000 }),
          axios.get(`${API}/tasks`, { timeout: 10000 }),
          axios.get(`${API}/non-productive-tasks`, { timeout: 10000 })
        ]);
        
        // Sort projects alphabetically
        const sortedProjects = projectsRes.data.sort((a, b) => a.name.localeCompare(b.name, 'cs'));
        setProjects(sortedProjects);
        setTasks(tasksRes.data);
        setNonProductiveTasks(nonProductiveRes.data);
        
        localStorage.setItem('cached_projects', JSON.stringify(sortedProjects));
        localStorage.setItem('cached_tasks', JSON.stringify(tasksRes.data));
        localStorage.setItem('cached_nonproductive_tasks', JSON.stringify(nonProductiveRes.data));
      } catch (e) {
        console.error("Error fetching data:", e);
        const cachedProjects = localStorage.getItem('cached_projects');
        const cachedTasks = localStorage.getItem('cached_tasks');
        const cachedNonProductive = localStorage.getItem('cached_nonproductive_tasks');
        
        if (cachedProjects) setProjects(JSON.parse(cachedProjects));
        if (cachedTasks) setTasks(JSON.parse(cachedTasks));
        if (cachedNonProductive) setNonProductiveTasks(JSON.parse(cachedNonProductive));
        
        if (cachedProjects || cachedTasks) {
          toast.info("Načteno z cache (offline)");
        } else {
          toast.error("Nepodařilo se načíst data");
        }
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Load timer from localStorage first, then check server
  useEffect(() => {
    const loadTimer = async () => {
      const localTimer = TimerStorage.get();
      if (localTimer && localTimer.employee_id === employeeId) {
        setActiveRecord(localTimer);
        setIsRunning(true);
        
        if (localTimer.is_non_productive) {
          setMode('non-productive');
          setSelectedNonProductiveTask(localTimer.task);
        } else {
          setMode('productive');
          setSelectedTask(localTimer.task);
        }
        
        const startTime = new Date(localTimer.start_time).getTime();
        const now = Date.now();
        setElapsedTime(Math.floor((now - startTime) / 1000));
      }
      
      if (isOnline && employeeId) {
        try {
          const response = await axios.get(`${API}/timer/active/${employeeId}`, { timeout: 10000 });
          if (response.data) {
            const serverTimer = response.data;
            setActiveRecord(serverTimer);
            setIsRunning(true);
            TimerStorage.save(serverTimer);
            
            if (serverTimer.is_non_productive) {
              setMode('non-productive');
              setSelectedNonProductiveTask(serverTimer.task);
            } else {
              setMode('productive');
              const project = projects.find(p => p.id === serverTimer.project_id);
              if (project) setSelectedProject(project);
              setSelectedTask(serverTimer.task);
            }
            
            const startTime = new Date(serverTimer.start_time).getTime();
            const now = Date.now();
            setElapsedTime(Math.floor((now - startTime) / 1000));
          } else if (!localTimer) {
            setIsRunning(false);
            setActiveRecord(null);
            TimerStorage.clear();
          }
        } catch (e) {
          console.error("Error checking server timer:", e);
        }
      }
    };
    
    if (projects.length > 0 || nonProductiveTasks.length > 0) {
      loadTimer();
    }
  }, [employeeId, projects, nonProductiveTasks, isOnline]);

  // Timer effect
  useEffect(() => {
    let interval;
    if (isRunning) {
      interval = setInterval(() => {
        setElapsedTime(prev => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isRunning]);

  const formatTime = useCallback((seconds) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, []);

  const handleStart = async () => {
    if (mode === 'productive' && (!selectedProject || !selectedTask)) {
      toast.error("Vyberte projekt a úkon");
      return;
    }
    if (mode === 'non-productive' && !selectedNonProductiveTask) {
      toast.error("Vyberte neproduktivní úkon");
      return;
    }

    const startTime = new Date().toISOString();
    const localRecord = {
      id: `local_${Date.now()}`,
      employee_id: employee.id,
      employee_name: employee.name,
      is_non_productive: mode === 'non-productive',
      start_time: startTime,
      task: mode === 'productive' ? selectedTask : selectedNonProductiveTask,
      project_id: mode === 'productive' ? selectedProject?.id : null,
      project_name: mode === 'productive' ? selectedProject?.name : null
    };

    TimerStorage.save(localRecord);
    setActiveRecord(localRecord);
    setIsRunning(true);
    setElapsedTime(0);

    if (isOnline) {
      try {
        const requestData = {
          employee_id: employee.id,
          employee_name: employee.name,
          is_non_productive: mode === 'non-productive',
          task: mode === 'productive' ? selectedTask : selectedNonProductiveTask
        };

        if (mode === 'productive') {
          requestData.project_id = selectedProject.id;
          requestData.project_name = selectedProject.name;
        }

        const response = await axios.post(`${API}/timer/start`, requestData, { timeout: 15000 });
        const serverRecord = response.data;
        TimerStorage.save(serverRecord);
        setActiveRecord(serverRecord);
        toast.success("Časomíra spuštěna");
      } catch (e) {
        console.error("Error starting timer on server:", e);
        toast.warning("Spuštěno lokálně (offline)");
      }
    } else {
      toast.warning("Spuštěno lokálně (offline)");
    }
  };

  const handleStop = async () => {
    if (!activeRecord) return;

    const endTime = new Date().toISOString();
    const stopData = {
      record_id: activeRecord.id,
      end_time: endTime,
      duration_seconds: elapsedTime,
      task: activeRecord.task,
      project_name: activeRecord.project_name
    };

    setIsRunning(false);
    setActiveRecord(null);
    setElapsedTime(0);
    setSelectedProject(null);
    setSelectedTask(null);
    setSelectedNonProductiveTask(null);
    TimerStorage.clear();

    if (isOnline) {
      try {
        await axios.post(`${API}/timer/stop`, stopData, { timeout: 15000 });
        toast.success("Čas uložen do Google Sheets");
      } catch (e) {
        console.error("Error stopping timer on server:", e);
        OfflineQueue.addPendingStop(stopData);
        setPendingStops(OfflineQueue.getPendingStops());
        toast.warning("Uloženo lokálně - synchronizuje se při připojení");
      }
    } else {
      OfflineQueue.addPendingStop(stopData);
      setPendingStops(OfflineQueue.getPendingStops());
      toast.warning("Uloženo lokálně - synchronizuje se při připojení");
    }
  };

  const handleBack = () => {
    if (isRunning) {
      const confirm = window.confirm("Časomíra stále běží! Opravdu chcete odejít? Časomíra bude pokračovat.");
      if (!confirm) return;
    }
    navigate('/');
  };

  const handleModeChange = (newMode) => {
    if (isRunning) return;
    setMode(newMode);
    setSelectedProject(null);
    setSelectedTask(null);
    setSelectedNonProductiveTask(null);
  };

  if (loading || !employee) {
    return (
      <div className="loading-container" data-testid="loading-spinner">
        <div className="spinner"></div>
        <p>Načítání...</p>
      </div>
    );
  }

  return (
    <div className="timer-page" data-testid="timer-page">
      <ConnectionStatus isOnline={isOnline} pendingCount={pendingStops.length} />
      
      <div className="timer-header">
        <button className="back-button" onClick={handleBack} data-testid="back-button">
          ← Zpět
        </button>
        <div className="employee-info">
          {!isOnline && <WifiOff size={16} className="offline-icon" />}
          <User className="user-icon" />
          <span data-testid="employee-name">{employee.name}</span>
        </div>
      </div>

      {/* Active Timer Display */}
      <Card className={`timer-card ${isRunning ? (activeRecord?.is_non_productive ? 'running-nonproductive' : 'running') : ''}`} data-testid="timer-card">
        <CardHeader>
          <CardTitle className="timer-title">
            <Clock className="clock-icon" />
            Časomíra
            {isRunning && !isOnline && (
              <span className="offline-badge">
                <CloudOff size={14} />
                Offline
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="timer-display" data-testid="timer-display">
            {formatTime(elapsedTime)}
          </div>
          {isRunning && activeRecord && (
            <div className={`active-info ${activeRecord.is_non_productive ? 'nonproductive' : ''}`} data-testid="active-timer-info">
              {activeRecord.is_non_productive ? (
                <div className="info-row">
                  <Wrench size={18} />
                  <span>{activeRecord.task}</span>
                  <span className="badge nonproductive-badge">Neproduktivní</span>
                </div>
              ) : (
                <>
                  <div className="info-row">
                    <Briefcase size={18} />
                    <span>{activeRecord.project_name}</span>
                  </div>
                  <div className="info-row">
                    <Package size={18} />
                    <span>{activeRecord.task}</span>
                  </div>
                </>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Mode Toggle */}
      {!isRunning && (
        <div className="mode-toggle" data-testid="mode-toggle">
          <button
            className={`mode-button ${mode === 'productive' ? 'active' : ''}`}
            onClick={() => handleModeChange('productive')}
            data-testid="mode-productive"
          >
            <Briefcase size={20} />
            Produktivní
          </button>
          <button
            className={`mode-button nonproductive ${mode === 'non-productive' ? 'active' : ''}`}
            onClick={() => handleModeChange('non-productive')}
            data-testid="mode-nonproductive"
          >
            <Wrench size={20} />
            Neproduktivní
          </button>
        </div>
      )}

      {/* Selection Controls - Productive */}
      {!isRunning && mode === 'productive' && (
        <div className="selection-section" data-testid="selection-section">
          {/* Project Selector - Opens Modal */}
          <button 
            className="project-selector" 
            onClick={() => setShowProjectModal(true)}
            data-testid="project-selector"
          >
            <div className="selector-content">
              <Briefcase className="selector-icon" />
              <div className="selector-text">
                <span className="selector-label">Projekt</span>
                <span className="selector-value">
                  {selectedProject ? selectedProject.name : 'Vyberte projekt...'}
                </span>
              </div>
            </div>
            <ChevronRight size={24} />
          </button>

          <Card className="selection-card">
            <CardHeader>
              <CardTitle>
                <Package className="section-icon" />
                Úkon
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="task-grid">
                {tasks.map((task) => (
                  <button
                    key={task.name}
                    className={`task-button ${selectedTask === task.name ? 'selected' : ''}`}
                    onClick={() => setSelectedTask(task.name)}
                    data-testid={`task-btn-${task.name}`}
                  >
                    {task.name}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Non-Productive Selection */}
      {!isRunning && mode === 'non-productive' && (
        <div className="selection-section" data-testid="nonproductive-section">
          <Card className="selection-card nonproductive-card">
            <CardHeader>
              <CardTitle>
                <Wrench className="section-icon" />
                Neproduktivní úkon
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="task-grid">
                {nonProductiveTasks.map((task) => (
                  <button
                    key={task.name}
                    className={`task-button nonproductive ${selectedNonProductiveTask === task.name ? 'selected' : ''}`}
                    onClick={() => setSelectedNonProductiveTask(task.name)}
                    data-testid={`nonproductive-btn-${task.name}`}
                  >
                    {task.name}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
          
          <div className="nonproductive-hint">
            <AlertTriangle size={16} />
            <span>Neproduktivní úkony nejsou vázány na projekt</span>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="action-buttons">
        {!isRunning ? (
          <Button
            className={`start-button ${mode === 'non-productive' ? 'nonproductive' : ''}`}
            onClick={handleStart}
            disabled={mode === 'productive' ? (!selectedProject || !selectedTask) : !selectedNonProductiveTask}
            data-testid="start-button"
          >
            <Play size={24} />
            START
          </Button>
        ) : (
          <Button
            className="stop-button"
            onClick={handleStop}
            data-testid="stop-button"
          >
            <Square size={24} />
            STOP
          </Button>
        )}
      </div>

      {/* Pending Syncs Info */}
      {pendingStops.length > 0 && (
        <div className="pending-syncs" data-testid="pending-syncs">
          <CloudOff size={16} />
          <span>{pendingStops.length} záznam(ů) čeká na synchronizaci</span>
        </div>
      )}

      {/* Project Picker Modal */}
      <ProjectPickerModal
        isOpen={showProjectModal}
        onClose={() => setShowProjectModal(false)}
        projects={projects}
        selectedProject={selectedProject}
        onSelect={setSelectedProject}
      />
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<EmployeeSelection />} />
          <Route path="/employee/:employeeId" element={<TimerPage />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-center" richColors />
    </div>
  );
}

export default App;
