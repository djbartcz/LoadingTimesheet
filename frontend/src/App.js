import { useState, useEffect, useCallback, useRef } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate, useParams, Link } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";
import { 
  Play, Square, Clock, User, Briefcase, Package, AlertTriangle, Wrench, 
  WifiOff, CloudOff, RefreshCw, X, ChevronRight, Search, Timer, Coffee,
  BarChart3, Users, History, Repeat, Bell, TrendingUp, Pause
} from "lucide-react";

// Use relative URL when served from same server, or env variable if set
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || window.location.origin;
const API = `${BACKEND_URL}/api`;

// Storage Keys
const STORAGE_KEYS = {
  ACTIVE_TIMER: 'timesheet_active_timer',
  PENDING_STOPS: 'timesheet_pending_stops',
  SELECTED_EMPLOYEE: 'selectedEmployee'
};

// Offline Queue Manager
const OfflineQueue = {
  getPendingStops: () => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEYS.PENDING_STOPS) || '[]');
    } catch { return []; }
  },
  addPendingStop: (stopData) => {
    const pending = OfflineQueue.getPendingStops();
    pending.push(stopData);
    localStorage.setItem(STORAGE_KEYS.PENDING_STOPS, JSON.stringify(pending));
  },
  removePendingStop: (recordId) => {
    const pending = OfflineQueue.getPendingStops().filter(p => p.record_id !== recordId);
    localStorage.setItem(STORAGE_KEYS.PENDING_STOPS, JSON.stringify(pending));
  }
};

const TimerStorage = {
  save: (data) => localStorage.setItem(STORAGE_KEYS.ACTIVE_TIMER, JSON.stringify(data)),
  get: () => { try { return JSON.parse(localStorage.getItem(STORAGE_KEYS.ACTIVE_TIMER)); } catch { return null; } },
  clear: () => localStorage.removeItem(STORAGE_KEYS.ACTIVE_TIMER)
};

const useOnlineStatus = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  useEffect(() => {
    const on = () => setIsOnline(true);
    const off = () => setIsOnline(false);
    window.addEventListener('online', on);
    window.addEventListener('offline', off);
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off); };
  }, []);
  return isOnline;
};

const formatDuration = (seconds) => {
  if (!seconds) return '0min';
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  if (hrs > 0) return `${hrs}h ${mins}min`;
  return `${mins}min`;
};

const formatTime = (seconds) => {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

const ConnectionStatus = ({ isOnline, pendingCount }) => {
  if (isOnline && pendingCount === 0) return null;
  return (
    <div className={`connection-status ${isOnline ? 'pending' : 'offline'}`}>
      {!isOnline ? <><WifiOff size={18} /><span>Offline režim</span></> 
        : <><RefreshCw size={18} className="spinning" /><span>Synchronizuji ({pendingCount})...</span></>}
    </div>
  );
};

const ProjectPickerModal = ({ isOpen, onClose, projects, onSelect, selectedProject }) => {
  const [searchTerm, setSearchTerm] = useState('');
  if (!isOpen) return null;
  const filtered = projects.filter(p => 
    p.name.toLowerCase().includes(searchTerm.toLowerCase()) || p.id.toLowerCase().includes(searchTerm.toLowerCase())
  );
  return (
    <div className="fullscreen-modal">
      <div className="modal-header">
        <h2>Vyberte projekt</h2>
        <button className="modal-close" onClick={onClose}><X size={28} /></button>
      </div>
      <div className="modal-search">
        <Search size={20} />
        <input type="text" placeholder="Hledat projekt..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
      </div>
      <div className="modal-list">
        {filtered.map((project) => (
          <button key={project.id} className={`modal-list-item ${selectedProject?.id === project.id ? 'selected' : ''}`}
            onClick={() => { onSelect(project); onClose(); }}>
            <div className="item-content">
              <span className="item-id">{project.id}</span>
              <span className="item-name">{project.name}</span>
            </div>
            <ChevronRight size={24} />
          </button>
        ))}
      </div>
    </div>
  );
};

// Employee Selection Page
const EmployeeSelection = () => {
  const [employees, setEmployees] = useState([]);
  const [activeTimers, setActiveTimers] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const isOnline = useOnlineStatus();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [empRes, timersRes] = await Promise.all([
          axios.get(`${API}/employees`, { timeout: 10000 }),
          axios.get(`${API}/timers/active`, { timeout: 10000 }).catch(() => ({ data: [] }))
        ]);
        const sorted = empRes.data.sort((a, b) => a.name.localeCompare(b.name, 'cs'));
        setEmployees(sorted);
        setActiveTimers(timersRes.data || []);
        localStorage.setItem('cached_employees', JSON.stringify(sorted));
      } catch (e) {
        const cached = localStorage.getItem('cached_employees');
        if (cached) setEmployees(JSON.parse(cached));
      } finally { setLoading(false); }
    };
    fetchData();
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${API}/timers/active`, { timeout: 10000 });
        setActiveTimers(res.data || []);
      } catch (e) {}
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const getActiveTimer = (employeeId) => activeTimers.find(t => t.employee_id === employeeId);

  if (loading) return <div className="loading-container"><div className="spinner"></div><p>Načítání...</p></div>;

  return (
    <div className="employee-selection">
      <ConnectionStatus isOnline={isOnline} pendingCount={0} />
      <div className="header">
        <Clock className="header-icon" />
        <h1>Evidence pracovní doby</h1>
        <p>Vyberte své jméno</p>
      </div>
      
      <Link to="/admin" className="admin-link">
        <BarChart3 size={20} />
        <span>Admin přehled</span>
        <ChevronRight size={20} />
      </Link>
      
      <div className="employees-list">
        {employees.map((employee) => {
          const activeTimer = getActiveTimer(employee.id);
          const isNonProductive = activeTimer?.is_non_productive;
          const isBreak = activeTimer?.is_break;
          return (
            <button key={employee.id}
              className={`employee-list-item ${activeTimer ? (isBreak ? 'on-break' : isNonProductive ? 'working-nonproductive' : 'working') : ''}`}
              onClick={() => { localStorage.setItem(STORAGE_KEYS.SELECTED_EMPLOYEE, JSON.stringify(employee)); navigate(`/employee/${employee.id}`); }}>
              <User className="employee-icon" />
              <div className="employee-info-content">
                <span className="employee-name">{employee.name}</span>
                {activeTimer && (
                  <div className={`employee-status ${isBreak ? 'break' : isNonProductive ? 'nonproductive' : ''}`}>
                    {isBreak ? <Coffee size={14} /> : <Timer size={14} />}
                    <span>{activeTimer.project_name || activeTimer.task}</span>
                  </div>
                )}
              </div>
              {activeTimer ? (
                <div className={`working-badge ${isBreak ? 'break' : isNonProductive ? 'nonproductive' : ''}`}>
                  <span className={`pulse-dot ${isBreak ? 'break' : isNonProductive ? 'nonproductive' : ''}`}></span>
                  {isBreak ? 'Přestávka' : isNonProductive ? 'Neprod.' : 'Pracuje'}
                </div>
              ) : <ChevronRight className="chevron" />}
            </button>
          );
        })}
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
  const [mode, setMode] = useState('productive'); // productive, non-productive, break
  const [isRunning, setIsRunning] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [activeRecord, setActiveRecord] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pendingStops, setPendingStops] = useState([]);
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [lastTask, setLastTask] = useState(null);
  const [summary, setSummary] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const syncingRef = useRef(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEYS.SELECTED_EMPLOYEE);
    if (stored) {
      const emp = JSON.parse(stored);
      if (emp.id === employeeId) setEmployee(emp);
      else navigate('/');
    } else navigate('/');
  }, [employeeId, navigate]);

  useEffect(() => { setPendingStops(OfflineQueue.getPendingStops()); }, []);

  useEffect(() => {
    const sync = async () => {
      if (!isOnline || syncingRef.current) return;
      const pending = OfflineQueue.getPendingStops();
      if (pending.length === 0) return;
      syncingRef.current = true;
      for (const stopData of pending) {
        try {
          await axios.post(`${API}/timer/stop`, stopData, { timeout: 15000 });
          OfflineQueue.removePendingStop(stopData.record_id);
          toast.success(`Synchronizováno`);
        } catch (e) {}
      }
      setPendingStops(OfflineQueue.getPendingStops());
      syncingRef.current = false;
    };
    sync();
  }, [isOnline]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [projectsRes, tasksRes, nonProdRes, lastTaskRes, summaryRes] = await Promise.all([
          axios.get(`${API}/projects`, { timeout: 10000 }),
          axios.get(`${API}/tasks`, { timeout: 10000 }),
          axios.get(`${API}/non-productive-tasks`, { timeout: 10000 }),
          axios.get(`${API}/employee/${employeeId}/last-task`, { timeout: 10000 }).catch(() => ({ data: null })),
          axios.get(`${API}/employee/${employeeId}/summary`, { timeout: 10000 }).catch(() => ({ data: null }))
        ]);
        setProjects(projectsRes.data.sort((a, b) => a.name.localeCompare(b.name, 'cs')));
        setTasks(tasksRes.data);
        setNonProductiveTasks(nonProdRes.data);
        setLastTask(lastTaskRes.data);
        setSummary(summaryRes.data);
        localStorage.setItem('cached_projects', JSON.stringify(projectsRes.data));
        localStorage.setItem('cached_tasks', JSON.stringify(tasksRes.data));
      } catch (e) {
        const cp = localStorage.getItem('cached_projects');
        const ct = localStorage.getItem('cached_tasks');
        if (cp) setProjects(JSON.parse(cp));
        if (ct) setTasks(JSON.parse(ct));
      } finally { setLoading(false); }
    };
    if (employeeId) fetchData();
  }, [employeeId]);

  useEffect(() => {
    const loadTimer = async () => {
      const localTimer = TimerStorage.get();
      if (localTimer && localTimer.employee_id === employeeId) {
        setActiveRecord(localTimer);
        setIsRunning(true);
        if (localTimer.is_break) setMode('break');
        else if (localTimer.is_non_productive) setMode('non-productive');
        else setMode('productive');
        const startTime = new Date(localTimer.start_time).getTime();
        setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
      }
      if (isOnline && employeeId) {
        try {
          const response = await axios.get(`${API}/timer/active/${employeeId}`, { timeout: 10000 });
          if (response.data) {
            setActiveRecord(response.data);
            setIsRunning(true);
            TimerStorage.save(response.data);
            if (response.data.is_break) setMode('break');
            else if (response.data.is_non_productive) setMode('non-productive');
            else setMode('productive');
            const startTime = new Date(response.data.start_time).getTime();
            setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
          } else if (!localTimer) {
            setIsRunning(false);
            setActiveRecord(null);
            TimerStorage.clear();
          }
        } catch (e) {}
      }
    };
    if (projects.length > 0) loadTimer();
  }, [employeeId, projects, isOnline]);

  useEffect(() => {
    let interval;
    if (isRunning) interval = setInterval(() => setElapsedTime(prev => prev + 1), 1000);
    return () => clearInterval(interval);
  }, [isRunning]);

  // Check for long running timer (> 4 hours)
  useEffect(() => {
    if (isRunning && elapsedTime > 4 * 3600 && elapsedTime % 1800 < 2) {
      toast.warning(`Pracujete už ${Math.floor(elapsedTime/3600)} hodin. Nezapomněli jste zastavit čas?`);
    }
  }, [isRunning, elapsedTime]);

  const handleStart = async (repeatLast = false) => {
    let taskData = {};
    
    if (repeatLast && lastTask) {
      taskData = {
        employee_id: employee.id,
        employee_name: employee.name,
        project_id: lastTask.project_id,
        project_name: lastTask.project_name,
        task: lastTask.task,
        is_non_productive: lastTask.is_non_productive || false,
        is_break: false
      };
    } else if (mode === 'productive') {
      if (!selectedProject || !selectedTask) { toast.error("Vyberte projekt a úkon"); return; }
      taskData = {
        employee_id: employee.id,
        employee_name: employee.name,
        project_id: selectedProject.id,
        project_name: selectedProject.name,
        task: selectedTask,
        is_non_productive: false,
        is_break: false
      };
    } else {
      if (!selectedNonProductiveTask) { toast.error("Vyberte neproduktivní úkon"); return; }
      taskData = {
        employee_id: employee.id,
        employee_name: employee.name,
        task: selectedNonProductiveTask,
        is_non_productive: true,
        is_break: false
      };
    }

    const localRecord = { id: `local_${Date.now()}`, ...taskData, start_time: new Date().toISOString() };
    TimerStorage.save(localRecord);
    setActiveRecord(localRecord);
    setIsRunning(true);
    setElapsedTime(0);

    if (isOnline) {
      try {
        const response = await axios.post(`${API}/timer/start`, taskData, { timeout: 15000 });
        TimerStorage.save(response.data);
        setActiveRecord(response.data);
        toast.success(mode === 'break' ? "Přestávka spuštěna" : "Časomíra spuštěna");
      } catch (e) { toast.warning("Spuštěno lokálně (offline)"); }
    } else { toast.warning("Spuštěno lokálně (offline)"); }
  };

  const handleStop = async () => {
    if (!activeRecord) return;
    const stopData = { record_id: activeRecord.id, end_time: new Date().toISOString(), duration_seconds: elapsedTime };
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
        toast.success("Čas uložen");
        // Refresh summary
        const summaryRes = await axios.get(`${API}/employee/${employeeId}/summary`, { timeout: 10000 });
        setSummary(summaryRes.data);
        const lastRes = await axios.get(`${API}/employee/${employeeId}/last-task`, { timeout: 10000 });
        setLastTask(lastRes.data);
      } catch (e) {
        OfflineQueue.addPendingStop(stopData);
        setPendingStops(OfflineQueue.getPendingStops());
        toast.warning("Uloženo lokálně");
      }
    } else {
      OfflineQueue.addPendingStop(stopData);
      setPendingStops(OfflineQueue.getPendingStops());
      toast.warning("Uloženo lokálně");
    }
  };

  if (loading || !employee) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div className="timer-page">
      <ConnectionStatus isOnline={isOnline} pendingCount={pendingStops.length} />
      
      <div className="timer-header">
        <button className="back-button" onClick={() => { if (isRunning && !window.confirm('Časomíra běží! Odejít?')) return; navigate('/'); }}>← Zpět</button>
        <div className="employee-info">
          {!isOnline && <WifiOff size={16} className="offline-icon" />}
          <User className="user-icon" />
          <span>{employee.name}</span>
        </div>
      </div>

      {/* Today's Summary */}
      {summary && !isRunning && (
        <div className="today-summary">
          <div className="summary-item">
            <span className="summary-label">Dnes</span>
            <span className="summary-value">{formatDuration(summary.today?.total_seconds)}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Tento týden</span>
            <span className="summary-value">{formatDuration(summary.week?.total_seconds)}</span>
          </div>
          <button className="history-btn" onClick={() => setShowHistory(!showHistory)}>
            <History size={18} />
          </button>
        </div>
      )}

      {/* History Panel */}
      {showHistory && summary?.today?.records && (
        <div className="history-panel">
          <h3>Dnešní záznamy</h3>
          {summary.today.records.length === 0 ? <p className="no-records">Žádné záznamy</p> : (
            summary.today.records.slice(0, 10).map((r, i) => (
              <div key={i} className={`history-item ${r.is_break ? 'break' : r.is_non_productive ? 'nonproductive' : ''}`}>
                <div className="history-info">
                  <span className="history-task">{r.project_name || r.task}</span>
                  <span className="history-time">{formatDuration(r.duration_seconds)}</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Timer Card */}
      <Card className={`timer-card ${isRunning ? (activeRecord?.is_break ? 'running-break' : activeRecord?.is_non_productive ? 'running-nonproductive' : 'running') : ''}`}>
        <CardHeader>
          <CardTitle className="timer-title">
            {activeRecord?.is_break ? <Coffee className="clock-icon" /> : <Clock className="clock-icon" />}
            {activeRecord?.is_break ? 'Přestávka' : 'Časomíra'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="timer-display">{formatTime(elapsedTime)}</div>
          {isRunning && activeRecord && (
            <div className={`active-info ${activeRecord.is_break ? 'break' : activeRecord.is_non_productive ? 'nonproductive' : ''}`}>
              {!activeRecord.is_break && (
                <div className="info-row">
                  {activeRecord.is_non_productive ? <Wrench size={18} /> : <Briefcase size={18} />}
                  <span>{activeRecord.project_name || activeRecord.task}</span>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Repeat Last Task */}
      {!isRunning && lastTask && !lastTask.is_break && (
        <button className="quick-repeat" onClick={() => handleStart(true)}>
          <Repeat size={20} />
          <div className="repeat-info">
            <span className="repeat-label">Pokračovat v posledním</span>
            <span className="repeat-task">{lastTask.project_name || lastTask.task}</span>
          </div>
          <Play size={20} />
        </button>
      )}

      {/* Mode Toggle */}
      {!isRunning && (
        <div className="mode-toggle">
          <button className={`mode-button ${mode === 'productive' ? 'active' : ''}`} onClick={() => setMode('productive')}>
            <Briefcase size={18} />Produktivní
          </button>
          <button className={`mode-button nonproductive ${mode === 'non-productive' ? 'active' : ''}`} onClick={() => setMode('non-productive')}>
            <Wrench size={18} />Neproduktivní
          </button>
        </div>
      )}

      {/* Selection Controls */}
      {!isRunning && mode === 'productive' && (
        <div className="selection-section">
          <button className="project-selector" onClick={() => setShowProjectModal(true)}>
            <div className="selector-content">
              <Briefcase className="selector-icon" />
              <div className="selector-text">
                <span className="selector-label">Projekt</span>
                <span className="selector-value">{selectedProject ? selectedProject.name : 'Vyberte projekt...'}</span>
              </div>
            </div>
            <ChevronRight size={24} />
          </button>
          <Card className="selection-card">
            <CardHeader><CardTitle><Package className="section-icon" />Úkon</CardTitle></CardHeader>
            <CardContent>
              <div className="task-grid">
                {tasks.map((task) => (
                  <button key={task.name} className={`task-button ${selectedTask === task.name ? 'selected' : ''}`}
                    onClick={() => setSelectedTask(task.name)}>{task.name}</button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {!isRunning && mode === 'non-productive' && (
        <div className="selection-section">
          <Card className="selection-card nonproductive-card">
            <CardHeader><CardTitle><Wrench className="section-icon" />Neproduktivní úkon</CardTitle></CardHeader>
            <CardContent>
              <div className="task-grid">
                {nonProductiveTasks.map((task) => (
                  <button key={task.name} className={`task-button nonproductive ${selectedNonProductiveTask === task.name ? 'selected' : ''}`}
                    onClick={() => setSelectedNonProductiveTask(task.name)}>{task.name}</button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Action Buttons */}
      <div className="action-buttons">
        {!isRunning ? (
          <Button className={`start-button ${mode === 'non-productive' ? 'nonproductive' : ''}`}
            onClick={() => handleStart(false)}
            disabled={mode === 'productive' ? (!selectedProject || !selectedTask) : !selectedNonProductiveTask}>
            <Play size={24} />START
          </Button>
        ) : (
          <Button className="stop-button" onClick={handleStop}><Square size={24} />STOP</Button>
        )}
      </div>

      {pendingStops.length > 0 && (
        <div className="pending-syncs"><CloudOff size={16} /><span>{pendingStops.length} záznam(ů) čeká</span></div>
      )}

      <ProjectPickerModal isOpen={showProjectModal} onClose={() => setShowProjectModal(false)} 
        projects={projects} selectedProject={selectedProject} onSelect={setSelectedProject} />
    </div>
  );
};

// Admin Dashboard
const AdminDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const ADMIN_PASSWORD = 'VedouciNakladky2025.';

  const handleLogin = (e) => {
    e.preventDefault();
    if (password === ADMIN_PASSWORD) {
      setIsAuthenticated(true);
      sessionStorage.setItem('adminAuth', 'true');
      setError('');
    } else {
      setError('Nesprávné heslo');
    }
  };

  useEffect(() => {
    const auth = sessionStorage.getItem('adminAuth');
    if (auth === 'true') {
      setIsAuthenticated(true);
    }
  }, []);

  const fetchData = async () => {
    try {
      const res = await axios.get(`${API}/admin/dashboard`, { timeout: 15000 });
      setData(res.data);
    } catch (e) { toast.error("Nepodařilo se načíst data"); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchData();
      const interval = setInterval(fetchData, 30000);
      return () => clearInterval(interval);
    }
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <div className="admin-login">
        <div className="login-card">
          <BarChart3 size={40} className="login-icon" />
          <h2>Admin přehled</h2>
          <p>Zadejte heslo pro přístup</p>
          <form onSubmit={handleLogin}>
            <input
              type="password"
              placeholder="Heslo"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="login-input"
              autoFocus
            />
            {error && <div className="login-error">{error}</div>}
            <button type="submit" className="login-button">Přihlásit</button>
          </form>
          <button className="back-link" onClick={() => navigate('/')}>← Zpět na výběr</button>
        </div>
      </div>
    );
  }

  if (loading) return <div className="loading-container"><div className="spinner"></div></div>;

  return (
    <div className="admin-dashboard">
      <div className="admin-header">
        <button className="back-button" onClick={() => navigate('/')}>← Zpět</button>
        <h1><BarChart3 size={24} /> Admin přehled</h1>
        <button className="refresh-btn" onClick={fetchData}><RefreshCw size={20} /></button>
      </div>

      {/* Alerts */}
      {data?.alerts?.length > 0 && (
        <div className="alerts-section">
          {data.alerts.map((alert, i) => (
            <div key={i} className="alert-item">
              <Bell size={18} />
              <span>{alert.message}</span>
            </div>
          ))}
        </div>
      )}

      {/* Summary Cards */}
      <div className="summary-cards">
        <div className="stat-card">
          <Users size={24} />
          <div className="stat-info">
            <span className="stat-value">{data?.summary?.working_now || 0}</span>
            <span className="stat-label">Pracuje</span>
          </div>
        </div>
        <div className="stat-card">
          <TrendingUp size={24} />
          <div className="stat-info">
            <span className="stat-value">{formatDuration(data?.summary?.today_total_seconds)}</span>
            <span className="stat-label">Dnes celkem</span>
          </div>
        </div>
      </div>

      {/* Employee List */}
      <div className="admin-employee-list">
        <h2>Zaměstnanci ({data?.employees?.length || 0})</h2>
        {data?.employees?.map((emp) => (
          <div key={emp.employee_id} className={`admin-employee-item ${emp.is_working ? (emp.is_non_productive ? 'nonproductive' : 'working') : ''}`}>
            <div className="emp-main">
              <User size={20} />
              <div className="emp-info">
                <span className="emp-name">{emp.employee_name}</span>
                {emp.is_working && (
                  <span className="emp-task">
                    <Timer size={12} />
                    {emp.current_project || emp.current_task}
                  </span>
                )}
              </div>
            </div>
            <div className="emp-stats">
              <span className="emp-today">{formatDuration(emp.today_seconds)}</span>
              {emp.is_working && (
                <span className={`emp-badge ${emp.is_non_productive ? 'nonproductive' : ''}`}>
                  <span className="pulse-dot-small"></span>
                  {emp.is_non_productive ? 'Neprod.' : 'Pracuje'}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
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
          <Route path="/admin" element={<AdminDashboard />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-center" richColors />
    </div>
  );
}

export default App;
