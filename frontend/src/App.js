import { useState, useEffect, useCallback } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";
import { Play, Square, Clock, User, Briefcase, Package, AlertTriangle, Wrench } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Employee Selection Page
const EmployeeSelection = () => {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchEmployees = async () => {
      try {
        const response = await axios.get(`${API}/employees`);
        setEmployees(response.data);
      } catch (e) {
        console.error("Error fetching employees:", e);
        toast.error("Nepodařilo se načíst zaměstnance");
      } finally {
        setLoading(false);
      }
    };
    fetchEmployees();
  }, []);

  const handleSelectEmployee = (employee) => {
    localStorage.setItem('selectedEmployee', JSON.stringify(employee));
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
      <div className="header">
        <Clock className="header-icon" />
        <h1>Časomíra nakládky</h1>
        <p>Vyberte své jméno pro zahájení</p>
      </div>
      
      <div className="employees-grid">
        {employees.length === 0 ? (
          <div className="empty-state" data-testid="no-employees">
            <User size={48} />
            <p>Žádní zaměstnanci</p>
            <span>Přidejte zaměstnance do Google Sheets</span>
          </div>
        ) : (
          employees.map((employee) => (
            <button
              key={employee.id}
              className="employee-button"
              onClick={() => handleSelectEmployee(employee)}
              data-testid={`employee-btn-${employee.id}`}
            >
              <User className="employee-icon" />
              <span className="employee-name">{employee.name}</span>
            </button>
          ))
        )}
      </div>
    </div>
  );
};

// Timer Page
const TimerPage = () => {
  const { employeeId } = useParams();
  const navigate = useNavigate();
  const [employee, setEmployee] = useState(null);
  const [projects, setProjects] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [nonProductiveTasks, setNonProductiveTasks] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [selectedTask, setSelectedTask] = useState(null);
  const [selectedNonProductiveTask, setSelectedNonProductiveTask] = useState(null);
  const [mode, setMode] = useState('productive'); // 'productive' or 'non-productive'
  const [isRunning, setIsRunning] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [activeRecord, setActiveRecord] = useState(null);
  const [loading, setLoading] = useState(true);

  // Load employee from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('selectedEmployee');
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

  // Fetch projects, tasks and non-productive tasks
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [projectsRes, tasksRes, nonProductiveRes] = await Promise.all([
          axios.get(`${API}/projects`),
          axios.get(`${API}/tasks`),
          axios.get(`${API}/non-productive-tasks`)
        ]);
        setProjects(projectsRes.data);
        setTasks(tasksRes.data);
        setNonProductiveTasks(nonProductiveRes.data);
      } catch (e) {
        console.error("Error fetching data:", e);
        toast.error("Nepodařilo se načíst data");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Check for active timer on load
  useEffect(() => {
    const checkActiveTimer = async () => {
      if (!employeeId) return;
      try {
        const response = await axios.get(`${API}/timer/active/${employeeId}`);
        if (response.data) {
          setActiveRecord(response.data);
          setIsRunning(true);
          
          if (response.data.is_non_productive) {
            setMode('non-productive');
            setSelectedNonProductiveTask(response.data.task);
          } else {
            setMode('productive');
            setSelectedProject(projects.find(p => p.id === response.data.project_id) || null);
            setSelectedTask(response.data.task);
          }
          
          // Calculate elapsed time
          const startTime = new Date(response.data.start_time).getTime();
          const now = Date.now();
          setElapsedTime(Math.floor((now - startTime) / 1000));
        }
      } catch (e) {
        console.error("Error checking active timer:", e);
      }
    };
    if (projects.length > 0 || nonProductiveTasks.length > 0) {
      checkActiveTimer();
    }
  }, [employeeId, projects, nonProductiveTasks]);

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

    try {
      const requestData = {
        employee_id: employee.id,
        employee_name: employee.name,
        is_non_productive: mode === 'non-productive'
      };

      if (mode === 'productive') {
        requestData.project_id = selectedProject.id;
        requestData.project_name = selectedProject.name;
        requestData.task = selectedTask;
      } else {
        requestData.task = selectedNonProductiveTask;
      }

      const response = await axios.post(`${API}/timer/start`, requestData);
      
      setActiveRecord(response.data);
      setIsRunning(true);
      setElapsedTime(0);
      toast.success("Časomíra spuštěna");
    } catch (e) {
      console.error("Error starting timer:", e);
      toast.error("Nepodařilo se spustit časomíru");
    }
  };

  const handleStop = async () => {
    if (!activeRecord) return;

    try {
      await axios.post(`${API}/timer/stop`, {
        record_id: activeRecord.id,
        end_time: new Date().toISOString(),
        duration_seconds: elapsedTime
      });
      
      setIsRunning(false);
      setActiveRecord(null);
      setElapsedTime(0);
      setSelectedProject(null);
      setSelectedTask(null);
      setSelectedNonProductiveTask(null);
      toast.success("Čas uložen do Google Sheets");
    } catch (e) {
      console.error("Error stopping timer:", e);
      toast.error("Nepodařilo se zastavit časomíru");
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
      <div className="timer-header">
        <button className="back-button" onClick={handleBack} data-testid="back-button">
          ← Zpět
        </button>
        <div className="employee-info">
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

      {/* Mode Toggle - Only visible when timer is not running */}
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

      {/* Selection Controls - Only visible when timer is not running */}
      {!isRunning && mode === 'productive' && (
        <div className="selection-section" data-testid="selection-section">
          <Card className="selection-card">
            <CardHeader>
              <CardTitle>
                <Briefcase className="section-icon" />
                Projekt
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Select
                value={selectedProject?.id || ""}
                onValueChange={(value) => {
                  const project = projects.find(p => p.id === value);
                  setSelectedProject(project);
                }}
              >
                <SelectTrigger className="select-trigger" data-testid="project-select">
                  <SelectValue placeholder="Vyberte projekt" />
                </SelectTrigger>
                <SelectContent>
                  {projects.map((project) => (
                    <SelectItem key={project.id} value={project.id} data-testid={`project-option-${project.id}`}>
                      {project.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

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

      {/* Non-Productive Selection - Only visible when timer is not running and mode is non-productive */}
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
