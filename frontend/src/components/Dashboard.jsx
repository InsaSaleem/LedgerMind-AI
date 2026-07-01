import React, { useEffect, useState } from 'react';

const Dashboard = ({ stats, anomalies = [] }) => {
  const [mounted, setMounted] = useState(false);
  
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!stats) return <div className="card">Loading stats...</div>;

  const topCategories = stats.top_categories ? Object.entries(stats.top_categories) : [];
  const topCategoryName = topCategories.length > 0 ? topCategories[0][0] : 'None';
  const topCategoryAmount = topCategories.length > 0 ? topCategories[0][1] : 0;
  
  const hasAnomalies = stats.anomaly_count > 0;
  
  // Find max for bar chart scaling
  const maxCategoryAmount = topCategories.length > 0 ? Math.max(...topCategories.map(c => c[1])) : 1;

  return (
    <div className="dashboard-container" style={{ display: 'flex', flexDirection: 'column', gap: '24px', height: '100%' }}>
      <div className="card">
        <h2>Financial Overview</h2>
        <div className="stat-grid-3">
          <div className="stat-item">
            <div className="stat-label">Total Spend</div>
            <div className="stat-value">
              ${stats.total_spend?.toFixed(2) || '0.00'}
            </div>
            <div className="sparkline">
              {[40, 60, 30, 80, 50, 90].map((h, i) => (
                <div key={i} className="sparkline-bar" style={{ height: `${h}%` }}></div>
              ))}
            </div>
          </div>
          
          <div className="stat-item" style={{ borderLeftColor: hasAnomalies ? '#ff4d4f' : 'var(--accent)' }}>
            <div className="stat-label">Anomalies Detected</div>
            <div className="stat-value" style={{ color: hasAnomalies ? '#ff4d4f' : 'var(--accent)' }}>
               {stats.anomaly_count || 0}
               {hasAnomalies ? (
                 <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="#ff4d4f"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
               ) : (
                 <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="var(--accent)"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
               )}
            </div>
          </div>
          
          <div className="stat-item">
            <div className="stat-label">Top Category</div>
            <div className="stat-value" style={{ fontSize: '18px' }}>
              {topCategoryName}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              ${topCategoryAmount.toFixed(2)}
            </div>
          </div>
        </div>
      </div>
      
      <div className="card">
        <h2>Spending Breakdown</h2>
        {topCategories.length > 0 ? (
          <div className="bar-chart-container">
            {topCategories.map(([cat, amt], idx) => {
              const widthPct = (amt / maxCategoryAmount) * 100;
              const isHighest = idx === 0;
              return (
                <div key={idx} className="bar-chart-row">
                  <div className="bar-label">{cat}</div>
                  <div className="bar-track">
                    <div 
                      className="bar-fill" 
                      style={{ 
                        width: mounted ? `${widthPct}%` : '0%',
                        backgroundColor: isHighest ? '#ff4d4f' : 'var(--accent)',
                      }}
                    ></div>
                  </div>
                  <div className="bar-value">${amt.toFixed(2)}</div>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ color: 'var(--text-secondary)' }}>No category data available.</div>
        )}
      </div>
      
      <div className="card">
        <h2>Anomaly List</h2>
        {anomalies && anomalies.length > 0 ? (
          <div className="anomaly-cards-list">
            {anomalies.map((anom, idx) => (
              <div key={idx} className="anomaly-card">
                <div className="anomaly-header">
                  <span className="anomaly-date">{anom.date || 'Unknown Date'}</span>
                  <span className="anomaly-badge">⚠ Flagged as anomaly</span>
                </div>
                <div className="anomaly-body">
                  <span className="anomaly-desc">{anom.description || 'Unknown Transaction'}</span>
                  <span className="anomaly-amt">${anom.amount?.toFixed(2) || '0.00'}</span>
                </div>
                {anom.reason && <div className="anomaly-reason">{anom.reason}</div>}
              </div>
            ))}
          </div>
        ) : (
          <div className="no-anomalies-msg">
            <span role="img" aria-label="check" style={{ color: 'var(--accent)' }}>✓</span> No anomalies detected
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
