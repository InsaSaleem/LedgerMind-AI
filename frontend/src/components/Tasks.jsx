import React, { useState, useEffect } from 'react';

const PRIORITY_CONFIG = {
  high:   { color: '#FF4444', bg: 'rgba(255, 68, 68, 0.10)', label: 'High' },
  medium: { color: '#FFB300', bg: 'rgba(255, 179, 0, 0.10)', label: 'Medium' },
  low:    { color: '#00D26A', bg: 'rgba(0, 210, 106, 0.10)', label: 'Low' },
};

const CATEGORY_ICONS = {
  review:      '📋',
  budget:      '💰',
  investigate: '🔍',
  optimize:    '⚡',
  plan:        '📅',
};

const Tasks = ({ theme }) => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fetched, setFetched] = useState(false);

  const fetchTasks = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('http://localhost:5000/api/tasks');
      const data = await res.json();
      if (data.tasks) {
        setTasks(data.tasks);
        setFetched(true);
      }
      if (data.error) {
        setError(data.error);
      }
    } catch (err) {
      console.error(err);
      setError('Failed to connect to server.');
    } finally {
      setLoading(false);
    }
  };

  const toggleTask = (index) => {
    setTasks(prev =>
      prev.map((t, i) => i === index ? { ...t, completed: !t.completed } : t)
    );
  };

  const completedCount = tasks.filter(t => t.completed).length;
  const progress = tasks.length > 0 ? (completedCount / tasks.length) * 100 : 0;

  return (
    <div className="tasks-panel">
      <div className="tasks-header">
        <div className="tasks-header-left">
          <span className="tasks-header-title">📌 AI Tasks</span>
          {fetched && tasks.length > 0 && (
            <span className="tasks-counter">{completedCount}/{tasks.length}</span>
          )}
        </div>
        <button
          className="btn tasks-generate-btn"
          onClick={fetchTasks}
          disabled={loading}
        >
          {loading ? (
            <>
              <div className="status-dot pulsing" />
              Generating...
            </>
          ) : fetched ? (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </>
          ) : (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Generate Tasks
            </>
          )}
        </button>
      </div>

      {/* Progress bar */}
      {fetched && tasks.length > 0 && (
        <div className="tasks-progress">
          <div className="tasks-progress-track">
            <div
              className="tasks-progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="tasks-progress-label">
            {Math.round(progress)}% complete
          </span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="tasks-error">
          ⚠ {error}
        </div>
      )}

      {/* Task list */}
      <div className="tasks-list">
        {!fetched && !loading && (
          <div className="tasks-empty">
            <div className="tasks-empty-icon">📌</div>
            <div className="tasks-empty-text">
              Click <strong>Generate Tasks</strong> to get AI-powered financial action items
            </div>
          </div>
        )}

        {tasks.map((task, idx) => {
          const pConfig = PRIORITY_CONFIG[task.priority] || PRIORITY_CONFIG.medium;
          const catIcon = CATEGORY_ICONS[task.category] || '📋';
          return (
            <div
              key={idx}
              className={`task-item ${task.completed ? 'task-completed' : ''}`}
              onClick={() => toggleTask(idx)}
            >
              {/* Checkbox */}
              <div className={`task-checkbox ${task.completed ? 'checked' : ''}`}>
                {task.completed && (
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>

              {/* Content */}
              <div className="task-content">
                <div className="task-title-row">
                  <span className="task-icon">{catIcon}</span>
                  <span className={`task-title ${task.completed ? 'line-through' : ''}`}>
                    {task.title}
                  </span>
                </div>
                {task.description && (
                  <div className="task-description">{task.description}</div>
                )}
              </div>

              {/* Priority badge */}
              <span
                className="task-priority-badge"
                style={{ color: pConfig.color, background: pConfig.bg }}
              >
                {pConfig.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Tasks;
