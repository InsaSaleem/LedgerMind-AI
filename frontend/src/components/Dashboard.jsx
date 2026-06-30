import React from 'react';

const Dashboard = ({ stats }) => {
  if (!stats) return <div className="card">Loading stats...</div>;

  return (
    <div className="card" style={{ height: '100%' }}>
      <h2>Financial Overview</h2>
      
      <div className="stat-grid">
        <div className="stat-item">
          <div className="stat-label">Total Spend</div>
          <div className="stat-value">${stats.total_spend?.toFixed(2) || '0.00'}</div>
        </div>
        <div className="stat-item">
          <div className="stat-label">Anomalies Detected</div>
          <div className="stat-value" style={{ color: stats.anomaly_count > 0 ? '#ff4d4f' : 'var(--text-primary)' }}>
             {stats.anomaly_count || 0}
          </div>
        </div>
      </div>

      {stats.top_categories && Object.keys(stats.top_categories).length > 0 && (
        <div style={{ marginTop: '24px' }}>
          <div className="stat-label">Top Categories</div>
          <ul className="anomaly-list">
            {Object.entries(stats.top_categories).map(([cat, amt], idx) => (
              <li key={idx} className="anomaly-item" style={{ borderLeftColor: 'var(--text-secondary)' }}>
                {cat}: ${amt.toFixed(2)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
