import React, { useEffect, useState } from 'react';

const Dashboard = ({ stats: initialStats, anomalies: initialAnomalies = [] }) => {
  const [mounted, setMounted] = useState(false);
  const [liveStats, setLiveStats] = useState(initialStats);
  const [liveAnomalies, setLiveAnomalies] = useState(initialAnomalies);
  const [categoryData, setCategoryData] = useState(
    initialStats?.top_categories ? Object.entries(initialStats.top_categories) : []
  );

  // Fetch full dashboard data (with categories) from /api/dashboard on mount
  useEffect(() => {
    setMounted(true);
    fetch('http://localhost:5000/api/dashboard')
      .then(r => r.json())
      .then(data => {
        if (data.stats) {
          setLiveStats(data.stats);
          if (data.stats.top_categories) {
            setCategoryData(Object.entries(data.stats.top_categories));
          }
        }
        if (data.anomalies) setLiveAnomalies(data.anomalies);
      })
      .catch(() => {/* silently use initial props on failure */});
  }, []);

  const stats = liveStats || initialStats;
  const anomalies = liveAnomalies;

  if (!stats) return <div className="card" style={{ color: 'var(--text-secondary)' }}>Loading stats...</div>;

  const hasAnomalies = (stats.anomaly_count || 0) > 0;
  const topCategoryName = stats.top_cat_name || (categoryData[0]?.[0]) || 'N/A';
  const topCategoryAmount = stats.top_cat_amount ?? (categoryData[0]?.[1]) ?? 0;

  // Max for bar scaling
  const maxCategoryAmount = categoryData.length > 0 ? Math.max(...categoryData.map(c => c[1])) : 1;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* ── STAT CARDS ── */}
      <div className="card">
        <h2>Financial Overview</h2>
        <div className="stat-grid-3">

          {/* Total Spend */}
          <div className="stat-item">
            <div className="stat-label">Total Spend</div>
            <div className="stat-value">
              ${stats.total_spend?.toFixed(2) || '0.00'}
            </div>
            {/* Mini sparkline */}
            <div className="sparkline">
              {[40, 60, 30, 80, 50, 90].map((h, i) => (
                <div key={i} className="sparkline-bar" style={{ height: `${h}%` }} />
              ))}
            </div>
          </div>

          {/* Anomalies */}
          <div className="stat-item" style={{ borderLeftColor: hasAnomalies ? '#FF4444' : 'var(--accent)' }}>
            <div className="stat-label">Anomalies</div>
            <div className="stat-value" style={{ color: hasAnomalies ? '#FF4444' : 'var(--accent)' }}>
              {stats.anomaly_count || 0}
              {hasAnomalies ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="#FF4444">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="var(--accent)">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
          </div>

          {/* Top Category */}
          <div className="stat-item">
            <div className="stat-label">Top Category</div>
            <div className="stat-value" style={{ fontSize: '16px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {topCategoryName}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              ${typeof topCategoryAmount === 'number' ? topCategoryAmount.toFixed(2) : '0.00'}
            </div>
          </div>

        </div>
      </div>

      {/* ── SPENDING BREAKDOWN ── */}
      <div className="card">
        <h2>Spending Breakdown</h2>
        {categoryData.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '8px' }}>
            {categoryData.map(([cat, amt], idx) => {
              const pct = (amt / maxCategoryAmount) * 100;
              const isTop = idx === 0;
              return (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ width: '100px', fontSize: '12px', color: '#888', textAlign: 'right', flexShrink: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {cat}
                  </span>
                  <div style={{ flex: 1, background: '#1A1A1A', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
                    <div style={{
                      width: mounted ? `${pct}%` : '0%',
                      background: isTop ? '#00D26A' : '#2A6A4A',
                      height: '8px',
                      borderRadius: '4px',
                      transition: 'width 0.8s ease',
                    }} />
                  </div>
                  <span style={{ width: '70px', fontSize: '12px', color: 'white', textAlign: 'right', flexShrink: 0 }}>
                    ${amt.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ color: 'var(--text-secondary)', marginTop: '8px', fontSize: '14px' }}>
            No category data available.
          </div>
        )}
      </div>

      {/* ── ANOMALY LIST ── */}
      <div className="card">
        <h2>Anomaly List</h2>
        {anomalies && anomalies.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
            {anomalies.map((anom, idx) => (
              <div key={idx} style={{
                border: '1px solid rgba(255,68,68,0.25)',
                background: '#1A0A0A',
                borderLeft: '3px solid #FF4444',
                borderRadius: '8px',
                padding: '12px 16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}>
                {/* Date + badge row */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: '#888888', fontSize: '12px' }}>
                    {anom.date || 'Unknown Date'}
                  </span>
                  <span style={{
                    background: 'rgba(255,68,68,0.13)',
                    color: '#FF4444',
                    borderRadius: '4px',
                    padding: '2px 8px',
                    fontSize: '11px',
                    fontWeight: 600,
                  }}>
                    ⚠ Flagged as anomaly
                  </span>
                </div>
                {/* Description */}
                <div style={{ color: '#FFFFFF', fontSize: '14px', fontWeight: 500 }}>
                  {anom.description || 'Unknown Transaction'}
                </div>
                {/* Amount + reason row */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: '#FF4444', fontSize: '16px', fontWeight: 700 }}>
                    ${typeof anom.amount === 'number' ? anom.amount.toFixed(2) : '0.00'}
                  </span>
                  {anom.reason && (
                    <span style={{ color: '#888888', fontSize: '12px' }}>{anom.reason}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            color: 'var(--accent)', marginTop: '8px', fontSize: '14px'
          }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            No anomalies detected
          </div>
        )}
      </div>

    </div>
  );
};

export default Dashboard;
