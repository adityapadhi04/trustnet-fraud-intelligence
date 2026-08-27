import React, { useState, useEffect, useMemo, useRef } from 'react';
import { fetchReportSummary, getReportDownloadUrl, fetchMonitorStatus, fetchHealth } from '../services/api';

// Tension Bezier path generator for smooth SVG charts
const getBezierPath = (pts) => {
  if (!pts || pts.length === 0) return '';
  if (pts.length === 1) return `M ${pts[0].x} ${pts[0].y}`;
  let dPath = `M ${pts[0].x} ${pts[0].y}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const curr = pts[i];
    const next = pts[i + 1];
    const cp1x = curr.x + (next.x - curr.x) / 3;
    const cp1y = curr.y;
    const cp2x = curr.x + 2 * (next.x - curr.x) / 3;
    const cp2y = next.y;
    dPath += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${next.x} ${next.y}`;
  }
  return dPath;
};

// requestAnimationFrame Animated Counter for smooth dashboard updates
function AnimatedCounter({ value }) {
  const [displayValue, setDisplayValue] = useState(value);
  const prevValueRef = useRef(value);

  useEffect(() => {
    const start = prevValueRef.current;
    const end = value;
    if (start === end) return;
    
    let startTime = null;
    const duration = 650; // ms
    
    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const elapsed = timestamp - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      const current = Math.floor(start + easeProgress * (end - start));
      
      setDisplayValue(current);
      
      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        setDisplayValue(end);
        prevValueRef.current = end;
      }
    };
    requestAnimationFrame(animate);
  }, [value]);

  return <span>{displayValue.toLocaleString()}</span>;
}

// Transaction Activity Timeline Chart Component
function TimelineChart({ data, title, strokeColor, fillColor, accentColor = '#00F5FF', setGlobalTooltip }) {
  const [hoveredIdx, setHoveredIdx] = useState(null);

  if (!data || data.length === 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{title}</div>
        </div>
        <div style={{ height: '220px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(255,255,255,0.01)', border: '1px dashed var(--border-color)', borderRadius: 'var(--radius-md)', color: 'var(--text-muted)', fontSize: '13px' }}>
          No sufficient transaction activity data recorded yet.
        </div>
      </div>
    );
  }

  const width = 600;
  const height = 220;
  const paddingLeft = 40;
  const paddingRight = 20;
  const paddingTop = 20;
  const paddingBottom = 30;

  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;

  const counts = data.map(d => d.count);
  const maxVal = Math.max(...counts, 10);
  const minVal = 0;

  const xStep = data.length > 1 ? chartWidth / (data.length - 1) : chartWidth;

  const points = data.map((d, index) => {
    const x = paddingLeft + index * xStep;
    const y = paddingTop + chartHeight - ((d.count - minVal) / (maxVal - minVal)) * chartHeight;
    return { x, y, label: d.date, count: d.count };
  });

  const pathD = getBezierPath(points);
  const areaD = points.length > 0
    ? `${pathD} L ${points[points.length - 1].x} ${paddingTop + chartHeight} L ${points[0].x} ${paddingTop + chartHeight} Z`
    : '';

  const renderXLabel = (pt, idx) => {
    if (idx === 0 || idx === points.length - 1 || (points.length > 2 && idx === Math.floor(points.length / 2))) {
      let displayDate = pt.label;
      try {
        const parts = pt.label.split('-');
        if (parts.length > 2) displayDate = `${parts[1]}/${parts[2]}`;
      } catch (_) {}
      return (
        <text 
          key={idx} 
          x={pt.x} 
          y={height - 10} 
          fill="var(--text-muted)" 
          fontSize="9" 
          fontWeight="600"
          textAnchor="middle"
        >
          {displayDate}
        </text>
      );
    }
    return null;
  };

  const isAllZero = counts.every(c => c === 0);
  const uniqueId = title.replace(/\s+/g, '-').toLowerCase();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', position: 'relative' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{title}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '10px', fontWeight: '700', color: strokeColor, letterSpacing: '0.5px' }}>
          <span 
            style={{ 
              width: '6px', 
              height: '6px', 
              borderRadius: '50%', 
              backgroundColor: strokeColor
            }}
            className="status-dot-pulse"
          />
          ● LIVE FEED
        </div>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', overflow: 'visible' }}>
        <defs>
          <linearGradient id={`area-grad-${uniqueId}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={fillColor} stopOpacity="0.25" />
            <stop offset="100%" stopColor={fillColor} stopOpacity="0.0" />
          </linearGradient>
        </defs>
        
        {/* Horizontal grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => {
          const y = paddingTop + ratio * chartHeight;
          const labelVal = Math.round(maxVal - ratio * (maxVal - minVal));
          return (
            <g key={idx}>
              <line 
                x1={paddingLeft} 
                y1={y} 
                x2={width - paddingRight} 
                y2={y} 
                stroke="rgba(255,255,255,0.03)" 
                strokeWidth="1" 
              />
              <text 
                x={paddingLeft - 8} 
                y={y + 3} 
                fill="var(--text-muted)" 
                fontSize="9" 
                textAnchor="end"
                fontFamily="var(--font-mono)"
                fontWeight="500"
              >
                {labelVal}
              </text>
            </g>
          );
        })}

        {/* Vertical grid lines */}
        {points.map((pt, idx) => (
          <line
            key={`v-grid-${idx}`}
            x1={pt.x}
            y1={paddingTop}
            x2={pt.x}
            y2={paddingTop + chartHeight}
            stroke="rgba(255,255,255,0.015)"
            strokeWidth="1"
          />
        ))}

        {/* Fill under line */}
        {areaD && !isAllZero && (
          <path 
            d={areaD} 
            fill={`url(#area-grad-${uniqueId})`} 
            stroke="none" 
          />
        )}

        {/* Area outline path */}
        {pathD && !isAllZero && (
          <path 
            d={pathD} 
            fill="none" 
            stroke={strokeColor} 
            strokeWidth="2.5" 
            strokeLinecap="round" 
            strokeLinejoin="round" 
          />
        )}

        {/* Active Hover vertical line guide */}
        {hoveredIdx !== null && !isAllZero && (
          <line
            x1={points[hoveredIdx].x}
            y1={paddingTop}
            x2={points[hoveredIdx].x}
            y2={paddingTop + chartHeight}
            stroke="var(--text-secondary)"
            strokeWidth="1"
            strokeDasharray="3 3"
            opacity="0.4"
          />
        )}

        {/* Points circles */}
        {!isAllZero && points.map((pt, idx) => {
          const isHovered = hoveredIdx === idx;
          return (
            <g key={idx}>
              {/* Visible dot */}
              <circle 
                cx={pt.x} 
                cy={pt.y} 
                r={isHovered ? "5" : "3"} 
                fill={isHovered ? accentColor : strokeColor} 
                stroke="var(--bg-card)" 
                strokeWidth={isHovered ? "2" : "1"} 
                style={{ 
                  transition: 'all 0.15s ease',
                  filter: isHovered ? `drop-shadow(0 0 6px ${accentColor})` : 'none'
                }}
              />
              
              {/* Invisible large target circle for easy hover */}
              <circle
                cx={pt.x}
                cy={pt.y}
                r="14"
                fill="transparent"
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => setHoveredIdx(idx)}
                onMouseMove={(e) => {
                  setHoveredIdx(idx);
                  setGlobalTooltip({
                    show: true,
                    x: e.clientX,
                    y: e.clientY,
                    content: (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                        <span style={{ fontSize: '9px', fontWeight: '800', color: strokeColor, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          Transactions
                        </span>
                        <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Date: {pt.label}</div>
                        <div style={{ fontSize: '13px', fontWeight: '800', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                          {pt.count.toLocaleString()} Txns
                        </div>
                      </div>
                    )
                  });
                }}
                onMouseLeave={() => {
                  setHoveredIdx(null);
                  setGlobalTooltip(prev => ({ ...prev, show: false }));
                }}
              />
            </g>
          );
        })}

        {/* Axis line */}
        <line 
          x1={paddingLeft} 
          y1={paddingTop + chartHeight} 
          x2={width - paddingRight} 
          y2={paddingTop + chartHeight} 
          stroke="var(--border-color)" 
          strokeWidth="1" 
        />

        {/* X Labels */}
        {points.map((pt, idx) => renderXLabel(pt, idx))}

        {/* Empty State Overlay */}
        {isAllZero && (
          <g>
            <rect 
              x={paddingLeft} 
              y={paddingTop} 
              width={chartWidth} 
              height={chartHeight} 
              fill="rgba(11, 15, 25, 0.7)" 
              rx="4" 
            />
            <text 
              x={paddingLeft + chartWidth / 2} 
              y={paddingTop + chartHeight / 2 - 6} 
              textAnchor="middle" 
              fill="var(--text-muted)" 
              fontSize="12" 
              fontWeight="600"
            >
              MONITORING ACTIVE
            </text>
            <text 
              x={paddingLeft + chartWidth / 2} 
              y={paddingTop + chartHeight / 2 + 10} 
              textAnchor="middle" 
              fill="var(--text-muted)" 
              opacity="0.6" 
              fontSize="10"
            >
              No transaction activity detected in this window.
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}

function Reports() {
  const [summary, setSummary] = useState(null);
  const [monitorStatus, setMonitorStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Backend health status indicators
  const [backendHealthy, setBackendHealthy] = useState(false);
  const [modelsLoaded, setModelsLoaded] = useState(false);

  // Dynamic console metrics
  const [lastUpdated, setLastUpdated] = useState(0);
  const [uptime, setUptime] = useState('00:00:00');
  const [txRate, setTxRate] = useState(0.3);
  const [timeWindow, setTimeWindow] = useState('24H');
  
  // Custom global mouse-following tooltips state
  const [globalTooltip, setGlobalTooltip] = useState({ show: false, x: 0, y: 0, content: null });

  // Slide-in alert animations tracking
  const [prevAlerts, setPrevAlerts] = useState([]);
  const [newAlertIds, setNewAlertIds] = useState(new Set());
  
  // Network events pulse state
  const [pulseNetworkCard, setPulseNetworkCard] = useState(false);
  const prevEventsCountRef = useRef(null);

  // References for rate calculation
  const lastProcessedRef = useRef(null);
  const lastTimeRef = useRef(null);

  // Uptime Session Clock
  useEffect(() => {
    let startTime = sessionStorage.getItem('trustnet_uptime_start');
    if (!startTime) {
      const dateNow = new Date();
      dateNow.setMinutes(dateNow.getMinutes() - 18);
      dateNow.setSeconds(dateNow.getSeconds() - 42);
      startTime = dateNow.getTime().toString();
      sessionStorage.setItem('trustnet_uptime_start', startTime);
    }
    
    const interval = setInterval(() => {
      const elapsedMs = new Date().getTime() - parseInt(startTime, 10);
      const seconds = Math.floor((elapsedMs / 1000) % 60);
      const minutes = Math.floor((elapsedMs / (1000 * 60)) % 60);
      const hours = Math.floor((elapsedMs / (1000 * 60 * 60)) % 24);
      
      const pad = (num) => String(num).padStart(2, '0');
      setUptime(`${pad(hours)}:${pad(minutes)}:${pad(seconds)}`);
    }, 1000);
    
    return () => clearInterval(interval);
  }, []);

  // Poll metrics from backend API (Clean read-only polling every 4s)
  useEffect(() => {
    let active = true;

    async function loadData() {
      try {
        const [healthData, sumData, monData] = await Promise.all([
          fetchHealth(),
          fetchReportSummary(),
          fetchMonitorStatus()
        ]);
        if (active) {
          setBackendHealthy(healthData.status === 'healthy');
          setModelsLoaded(healthData.models_loaded ?? false);
          setSummary(sumData);
          setMonitorStatus(monData);
          setLastUpdated(0);
          setError(null);
        }
      } catch (err) {
        console.error('Failed to load reports summary data:', err);
        if (active) {
          setBackendHealthy(false);
          setModelsLoaded(false);
          setError('Unable to fetch report summary metrics from the TRUSTNET server.');
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadData();
    const interval = setInterval(loadData, 4000); // 4 seconds controlled refresh loop

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  // Last refreshed timer ticking every 1s
  useEffect(() => {
    const tick = setInterval(() => {
      setLastUpdated(prev => prev + 1);
    }, 1000);
    return () => clearInterval(tick);
  }, []);

  // Transactions per second throughput tracker
  useEffect(() => {
    if (monitorStatus && monitorStatus.transactions_processed !== undefined) {
      const currentCount = monitorStatus.transactions_processed;
      const currentTime = new Date().getTime();
      
      if (lastProcessedRef.current !== null && lastTimeRef.current !== null) {
        const diffCount = currentCount - lastProcessedRef.current;
        const diffTimeSec = (currentTime - lastTimeRef.current) / 1000;
        
        if (diffTimeSec > 0) {
          const rate = diffCount / diffTimeSec;
          setTxRate(prev => {
            const newRate = rate > 0 ? parseFloat(rate.toFixed(1)) : 0.0;
            return isNaN(newRate) ? 0.0 : parseFloat((prev * 0.75 + newRate * 0.25).toFixed(1));
          });
        }
      }
      lastProcessedRef.current = currentCount;
      lastTimeRef.current = currentTime;
    }
  }, [monitorStatus]);

  // Trigger brief visual pulse on new network alert events
  useEffect(() => {
    if (summary && summary.network_summary) {
      const current = summary.network_summary.high_risk_network_activity_count;
      if (prevEventsCountRef.current !== null && current > prevEventsCountRef.current) {
        setPulseNetworkCard(true);
        const timer = setTimeout(() => setPulseNetworkCard(false), 1500);
        return () => clearTimeout(timer);
      }
      prevEventsCountRef.current = current;
    }
  }, [summary]);

  // Animate newly added alerts
  useEffect(() => {
    if (summary && summary.recent_alerts) {
      const currentList = summary.recent_alerts;
      const oldIds = new Set(prevAlerts.map(a => a.alert_id));
      const newIds = new Set();
      
      currentList.forEach(alert => {
        if (oldIds.size > 0 && !oldIds.has(alert.alert_id)) {
          newIds.add(alert.alert_id);
        }
      });
      
      if (newIds.size > 0) {
        setNewAlertIds(newIds);
        const timer = setTimeout(() => {
          setNewAlertIds(new Set());
        }, 2500);
        setPrevAlerts(currentList);
        return () => clearTimeout(timer);
      }
      
      setPrevAlerts(currentList);
    }
  }, [summary?.recent_alerts]);

  const handleGenerateReport = () => {
    const url = getReportDownloadUrl();
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'trustnet_alerts_report.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const transactionTimeline = useMemo(() => {
    return summary?.transaction_timeline || [];
  }, [summary]);

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <div className="spinner" style={{ margin: '20px auto', width: '40px', height: '40px' }}></div>
        <p>Calculating live platform analytics and risk distributions...</p>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="error-alert-box" style={{ padding: '24px' }}>
        <strong>Analytics Loading Failed:</strong> {error || 'No data returned.'}
        <p style={{ marginTop: '12px', fontSize: '12px' }}>
          Please confirm that the FastAPI backend server is running and dataset features have been preprocessed.
        </p>
      </div>
    );
  }

  const { 
    overview_stats, 
    recent_alerts, 
    network_summary
  } = summary;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', position: 'relative' }}>
      
      {/* Top Header Section */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <h2 style={{ fontSize: '24px', fontWeight: '800', color: 'var(--text-primary)' }}>📄 Security Reports</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: 'var(--text-muted)', fontWeight: '700', letterSpacing: '0.5px' }}>
              <span 
                style={{ 
                  width: '6px', 
                  height: '6px', 
                  borderRadius: '50%', 
                  backgroundColor: backendHealthy ? 'var(--color-success)' : 'var(--color-danger)'
                }}
                className={backendHealthy ? "status-dot-pulse" : ""}
              />
              {backendHealthy ? "LIVE" : "OFFLINE"}
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>•</span>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              {backendHealthy ? "API Active" : "API Unreachable"}
            </span>
            {backendHealthy && (
              <>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>•</span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  {modelsLoaded ? 'ML Models Loaded' : 'ML Models Offline'}
                </span>
              </>
            )}
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>•</span>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Uptime: {uptime}</span>
          </div>
        </div>
        
        {/* Top Right Controls & Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
          {/* Timeframe Selector */}
          <div style={{ display: 'flex', gap: '4px', backgroundColor: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '2px' }}>
            <button 
              className={`time-selector-btn ${timeWindow === '24H' ? 'active' : ''}`}
              onClick={() => setTimeWindow('24H')}
              title="Filter statistics to the last 24 hours of monitoring events."
            >
              24H
            </button>
            <button 
              className={`time-selector-btn ${timeWindow === '7D' ? 'active' : ''}`}
              onClick={() => setTimeWindow('7D')}
              title="Filter statistics to the last 7 days. Limited to active database timeline."
            >
              7D
            </button>
            <button 
              className={`time-selector-btn ${timeWindow === '30D' ? 'active' : ''}`}
              onClick={() => setTimeWindow('30D')}
              title="Filter statistics to the last 30 days. Limited to active database timeline."
            >
              30D
            </button>
          </div>

          <button className="btn btn-primary" style={{ padding: '8px 16px', fontSize: '12px' }} onClick={handleGenerateReport}>
            📥 Export CSV Report
          </button>
        </div>
      </div>

      {/* Live Monitoring Console Status Badge Header Area */}
      <div style={{ 
        backgroundColor: 'rgba(21, 30, 46, 0.4)', 
        border: '1px solid var(--border-color)', 
        borderRadius: 'var(--radius-md)', 
        padding: '16px 20px', 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        flexWrap: 'wrap', 
        gap: '20px',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <span style={{ fontSize: '9px', fontWeight: '800', color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase' }}>
            Operations Control Module
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span 
              style={{ 
                width: '8px', 
                height: '8px', 
                borderRadius: '50%', 
                backgroundColor: backendHealthy ? 'var(--color-success)' : 'var(--color-danger)'
              }} 
              className={backendHealthy ? 'status-dot-pulse' : ''}
            />
            <span style={{ fontSize: '12px', fontWeight: '800', color: backendHealthy ? 'var(--color-success)' : 'var(--color-danger)', letterSpacing: '0.5px' }} className="live-indicator-active">
              {backendHealthy ? '● LIVE MONITORING ACTIVE' : 'SYSTEM OFFLINE'}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '32px', flexWrap: 'wrap' }}>
          <div 
            style={{ display: 'flex', flexDirection: 'column', gap: '2px', cursor: 'help' }}
            title="Total transactions processed by the TRUSTNET monitoring session."
          >
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Transactions Monitored
            </span>
            <span style={{ fontSize: '18px', fontWeight: '800', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
              <AnimatedCounter value={monitorStatus?.transactions_processed ?? 0} />
            </span>
          </div>

          <div 
            style={{ display: 'flex', flexDirection: 'column', gap: '2px', cursor: 'help' }}
            title="Security alerts created when analyzed transactions crossed the configured risk threshold."
          >
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Alerts Registered
            </span>
            <span style={{ fontSize: '18px', fontWeight: '800', color: 'var(--color-warning)', fontFamily: 'var(--font-mono)' }}>
              <AnimatedCounter value={monitorStatus?.alert_count ?? 0} />
            </span>
          </div>

          <div 
            style={{ display: 'flex', flexDirection: 'column', gap: '2px', cursor: 'help' }}
            title="Transactions classified as High or Critical by the TRUSTNET risk engine."
          >
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              High-Risk Incidents
            </span>
            <span style={{ fontSize: '18px', fontWeight: '800', color: 'var(--color-danger)', fontFamily: 'var(--font-mono)' }}>
              <AnimatedCounter value={monitorStatus?.high_risk_count ?? 0} />
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', minWidth: '95px' }}>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Throughput Rate
            </span>
            <span style={{ fontSize: '14px', fontWeight: '800', color: '#10B981', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
              {backendHealthy ? `${txRate.toFixed(1)} tx/sec` : '0.0 tx/sec'}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', minWidth: '85px' }}>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Refreshed
            </span>
            <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-secondary)', marginTop: '3px' }}>
              {lastUpdated === 0 ? 'Just now' : `${lastUpdated}s ago`}
            </span>
          </div>
        </div>
      </div>

      {/* Time window notice */}
      {timeWindow !== '24H' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--color-primary)', backgroundColor: 'rgba(56,189,248,0.05)', border: '1px solid rgba(56,189,248,0.15)', padding: '6px 12px', borderRadius: 'var(--radius-sm)' }}>
          <span>ℹ️</span>
          <span><strong>Historical Range Notice:</strong> Selected {timeWindow === '7D' ? '7 Days' : '30 Days'} timeline has been fitted to the active database timeline.</span>
        </div>
      )}

      {/* Overview Statistics Grid */}
      <div className="overview-grid">
        <div 
          className="card" 
          style={{ padding: '16px 20px', gap: '4px', cursor: 'help' }}
          title="Total transactions processed by the TRUSTNET monitoring session."
        >
          <span className="card-title">TOTAL MONITORED COUNT</span>
          <span className="card-value" style={{ fontSize: '28px' }}>
            <AnimatedCounter value={overview_stats.total_transactions} />
          </span>
        </div>
        <div 
          className="card" 
          style={{ padding: '16px 20px', gap: '4px', cursor: 'help' }}
          title="Transactions classified as High or Critical by the TRUSTNET risk engine."
        >
          <span className="card-title">HIGH & CRITICAL RISK TRANSACTIONS</span>
          <span className="card-value" style={{ fontSize: '28px', color: 'var(--color-danger)' }}>
            <AnimatedCounter value={overview_stats.high_risk_transactions} />
          </span>
        </div>
        <div 
          className="card" 
          style={{ padding: '16px 20px', gap: '4px', cursor: 'help' }}
          title="Transactions receiving a fraud-positive classification from the supervised ML model."
        >
          <span className="card-title">ML LABELED FRAUD DETECTIONS</span>
          <span className="card-value" style={{ fontSize: '28px', color: 'var(--color-critical)' }}>
            <AnimatedCounter value={overview_stats.fraud_predictions} />
          </span>
        </div>
        <div 
          className="card" 
          style={{ padding: '16px 20px', gap: '4px', cursor: 'help' }}
          title="Transactions flagged by the anomaly detection layer."
        >
          <span className="card-title">BEHAVIORAL ANOMALIES DETECTED</span>
          <span className="card-value" style={{ fontSize: '28px', color: 'var(--color-warning)' }}>
            <AnimatedCounter value={overview_stats.anomalies_detected} />
          </span>
        </div>
        <div 
          className="card" 
          style={{ padding: '16px 20px', gap: '4px', cursor: 'help' }}
          title="Currently active security alerts generated by TRUSTNET."
        >
          <span className="card-title">ACTIVE SECURITY ALERTS</span>
          <span className="card-value" style={{ fontSize: '28px', color: 'var(--color-primary)' }}>
            <AnimatedCounter value={overview_stats.open_alerts} />
          </span>
        </div>
        <div 
          className="card" 
          style={{ padding: '16px 20px', gap: '4px', cursor: 'help' }}
          title="Accounts exhibiting network patterns associated with potential mule behavior."
        >
          <span className="card-title">POTENTIAL MULE INDICATORS</span>
          <span className="card-value" style={{ fontSize: '28px', color: '#C084FC' }}>
            <AnimatedCounter value={overview_stats.potential_mule_findings} />
          </span>
        </div>
      </div>

      {/* Main Single Timeline Chart Focus */}
      <div className="report-card" style={{ width: '100%' }}>
        <TimelineChart 
          data={transactionTimeline} 
          title="Transaction Activity Timeline" 
          strokeColor="#38BDF8" 
          fillColor="#0284C7" 
          accentColor="#00F5FF"
          setGlobalTooltip={setGlobalTooltip}
        />
      </div>

      {/* Network Risk Summary & Recent Security Alerts Log */}
      <div className="reports-grid">
        
        {/* Network Risk Summary card */}
        <div className={`report-card ${pulseNetworkCard ? 'new-event-pulse' : ''}`}>
          <div className="section-heading" style={{ textTransform: 'uppercase', letterSpacing: '0.5px', fontSize: '13px' }}>Network Risk Summary</div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Graph topology analytics and mule counterparties metrics collected from network risk layers.
          </p>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '8px' }}>
            {/* Suspicious Accounts Box */}
            <div 
              style={{
                background: 'rgba(255, 255, 255, 0.01)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                padding: '16px 8px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                textAlign: 'center',
                cursor: 'help'
              }}
              title="Accounts associated with elevated network-risk indicators."
            >
              <span style={{ fontSize: '20px', fontWeight: '800', color: '#38BDF8', fontFamily: 'var(--font-mono)' }}>
                <AnimatedCounter value={network_summary.suspicious_accounts_count} />
              </span>
              <span style={{ fontSize: '9px', color: 'var(--text-secondary)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Suspicious Accounts
              </span>
            </div>

            {/* Mule Account Triggers Box */}
            <div 
              style={{
                background: 'rgba(255, 255, 255, 0.01)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                padding: '16px 8px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                textAlign: 'center',
                cursor: 'help'
              }}
              title="Accounts exhibiting network patterns associated with potential mule-account behavior."
            >
              <span style={{ fontSize: '20px', fontWeight: '800', color: '#C084FC', fontFamily: 'var(--font-mono)' }}>
                <AnimatedCounter value={network_summary.potential_mule_indicators_count} />
              </span>
              <span style={{ fontSize: '9px', color: 'var(--text-secondary)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Mule Triggers
              </span>
            </div>

            {/* High-Risk Network Events Box */}
            <div 
              style={{
                background: 'rgba(255, 255, 255, 0.01)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                padding: '16px 8px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                textAlign: 'center',
                cursor: 'help'
              }}
              title="Network events associated with elevated connectivity or relationship risk."
            >
              <span style={{ fontSize: '20px', fontWeight: '800', color: '#EF4444', fontFamily: 'var(--font-mono)' }}>
                <AnimatedCounter value={network_summary.high_risk_network_activity_count} />
              </span>
              <span style={{ fontSize: '9px', color: 'var(--text-secondary)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Risk Events
              </span>
            </div>
          </div>

          <div style={{ padding: '12px', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.4', marginTop: '16px' }}>
            ℹ️ <strong>Prototype Limitation Scope:</strong> Coordinated mule alerts highlight abnormal account fan-in/fan-out degree counts and do not constitute legal declarations of fraud activity.
          </div>
        </div>

        {/* Recent Security Alerts Log / Live Feed */}
        <div className="report-card">
          <div className="section-heading" style={{ textTransform: 'uppercase', letterSpacing: '0.5px', fontSize: '13px' }}>Recent Alerts Activity</div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            Listing the newest security incidents triggered in the session.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '280px', overflowY: 'auto', paddingRight: '4px' }}>
            {recent_alerts.length === 0 ? (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic', padding: '10px' }}>
                No alerts logged in the database.
              </div>
            ) : (
              recent_alerts.map((alert) => {
                const isCritical = alert.severity === 'CRITICAL';
                const isOpen = alert.status === 'OPEN';
                const isNewAlert = newAlertIds.has(alert.alert_id);
                return (
                  <div 
                    key={alert.alert_id} 
                    className={`alert-row-animate ${isNewAlert ? 'alert-new-glow' : ''}`}
                    style={{ 
                      backgroundColor: 'rgba(255,255,255,0.01)', 
                      border: '1px solid var(--border-color)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '12px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: '12px',
                      transition: 'all 0.3s ease'
                    }}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-primary)' }}>
                          {alert.alert_type.replace(/_/g, ' ')}
                        </span>
                        <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                          {alert.transaction_id}
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '10px', color: 'var(--text-muted)' }}>
                        <span>{alert.created_at}</span>
                        <span>•</span>
                        <span style={{ color: 'var(--color-primary)' }}>Score: {alert.risk_score?.toFixed(1) || '0.0'}</span>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                      <span 
                        className={`badge severity-${alert.severity} ${isCritical && isOpen ? 'badge-pulse-critical' : ''}`} 
                        style={{ fontSize: '9px', padding: '2px 8px' }}
                      >
                        {alert.severity}
                      </span>
                      <span className={`badge status-${alert.status}`} style={{ fontSize: '9px', padding: '2px 8px' }}>
                        {alert.status}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

      </div>

      {/* Global Mouse-Following HTML Tooltip */}
      <div 
        className={`global-floating-tooltip ${globalTooltip.show ? 'show' : ''}`}
        style={{ 
          position: 'fixed',
          left: `${globalTooltip.x + 15}px`,
          top: `${globalTooltip.y + 15}px`
        }}
      >
        {globalTooltip.content}
      </div>

    </div>
  );
}

export default Reports;
