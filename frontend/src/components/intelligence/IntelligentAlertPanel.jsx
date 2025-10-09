import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Bell,
  Brain,
  CheckCircle,
  Filter,
  TrendingUp,
  X,
  Zap,
} from 'lucide-react';
import UncertaintyIndicator from './UncertaintyIndicator';
import CausalAnalysisCard from './CausalAnalysisCard';
import './styles/IntelligentAlertPanel.css';

const filters = [
  { id: 'all', label: 'All' },
  { id: 'critical', label: 'Critical' },
  { id: 'high-confidence', label: 'High Confidence' },
  { id: 'actionable', label: 'Actionable' },
];

const getWebSocketUrl = () => {
  if (process.env.REACT_APP_INTELLIGENCE_WS) {
    return process.env.REACT_APP_INTELLIGENCE_WS;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${protocol}://${window.location.host}/api/intelligence/alerts`;
};

const IntelligentAlertPanel = ({ projectId, userId }) => {
  const [alerts, setAlerts] = useState([]);
  const [filter, setFilter] = useState('all');
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const url = getWebSocketUrl();
    const socket = new WebSocket(url);
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onerror = () => setConnected(false);
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setAlerts((previous) => [payload, ...previous].slice(0, 100));
      } catch (error) {
        console.warn('Failed to parse alert payload', error);
      }
    };
    return () => socket.close();
  }, []);

  const filteredAlerts = useMemo(() => alerts.filter((alert) => {
    if (filter === 'all') return true;
    if (filter === 'critical') return alert.severity === 'critical';
    if (filter === 'high-confidence') return (alert.confidence || 0) > 0.8;
    if (filter === 'actionable') return Array.isArray(alert.recommended_actions) && alert.recommended_actions.length > 0;
    return true;
  }), [alerts, filter]);

  const handleAction = async (alert, action) => {
    try {
      const response = await fetch('/api/intelligence/alert-action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alertId: alert.alert_id, action, userId }),
      });
      if (!response.ok) {
        throw new Error('Failed to process action');
      }
      setAlerts((previous) => previous.map((item) => (item.alert_id === alert.alert_id ? { ...item, status: action } : item)));
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div className="intelligent-alert-panel">
      <header className="panel-header">
        <div className="panel-title">
          <Brain size={20} />
          <div>
            <h2>Intelligent Alerts</h2>
            <p>Uncertainty-aware monitoring with causal insights</p>
          </div>
        </div>
        <div className="panel-status" data-connected={connected}>
          <span className="status-indicator" />
          {connected ? 'Live' : 'Offline'}
        </div>
      </header>

      <div className="panel-filters">
        <Filter size={16} />
        {filters.map((option) => (
          <button
            key={option.id}
            type="button"
            className={option.id === filter ? 'active' : ''}
            onClick={() => setFilter(option.id)}
          >
            {option.label}
            <span className="count">
              {
                alerts.filter((alert) => {
                  if (option.id === 'all') return true;
                  if (option.id === 'critical') return alert.severity === 'critical';
                  if (option.id === 'high-confidence') return (alert.confidence || 0) > 0.8;
                  if (option.id === 'actionable') {
                    return Array.isArray(alert.recommended_actions) && alert.recommended_actions.length > 0;
                  }
                  return true;
                }).length
              }
            </span>
          </button>
        ))}
      </div>

      <div className="panel-content">
        <div className="alert-list">
          {filteredAlerts.map((alert) => {
            const Icon = alert.severity === 'critical'
              ? AlertTriangle
              : alert.severity === 'high'
                ? AlertTriangle
                : Bell;
            return (
              <article
                key={alert.alert_id}
                className={`alert-card severity-${alert.severity} ${selectedAlert?.alert_id === alert.alert_id ? 'selected' : ''}`}
                onClick={() => setSelectedAlert(alert)}
              >
                <div className="alert-meta">
                  <div className="alert-icon">
                    <Icon size={18} />
                  </div>
                  <div>
                    <h3>{alert.alert_type}</h3>
                    <time>{new Date(alert.timestamp).toLocaleString()}</time>
                  </div>
                  {alert.auto_resolvable && (
                    <span className="auto-resolve">
                      <Zap size={14} />
                      Auto-resolvable
                    </span>
                  )}
                </div>
                <p className="alert-message">{alert.message}</p>
                <UncertaintyIndicator
                  confidence={alert.confidence}
                  uncertainty={1 - (alert.confidence || 0)}
                  confidenceInterval={alert.uncertainty_range}
                  shouldEscalate={alert.escalation_required}
                  showDetails={false}
                />
                <div className="alert-actions">
                  <button type="button" onClick={(event) => { event.stopPropagation(); handleAction(alert, 'acknowledged'); }}>
                    <CheckCircle size={16} />
                    Acknowledge
                  </button>
                  <button type="button" onClick={(event) => { event.stopPropagation(); handleAction(alert, 'dismissed'); }}>
                    <X size={16} />
                    Dismiss
                  </button>
                </div>
              </article>
            );
          })}
          {filteredAlerts.length === 0 && (
            <div className="empty-state">
              <TrendingUp size={18} />
              <span>No alerts match the selected filter.</span>
            </div>
          )}
        </div>

        {selectedAlert && (
          <aside className="alert-details">
            <header>
              <h3>Alert Details</h3>
              <button type="button" onClick={() => setSelectedAlert(null)}>
                <X size={16} />
              </button>
            </header>
            <dl className="details-grid">
              <div>
                <dt>ID</dt>
                <dd>{selectedAlert.alert_id}</dd>
              </div>
              <div>
                <dt>Severity</dt>
                <dd className={`severity-tag severity-${selectedAlert.severity}`}>{selectedAlert.severity}</dd>
              </div>
              <div>
                <dt>Confidence</dt>
                <dd>{Math.round((selectedAlert.confidence || 0) * 100)}%</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>{selectedAlert.status || 'active'}</dd>
              </div>
            </dl>
            {selectedAlert.root_cause_analysis && Object.keys(selectedAlert.root_cause_analysis).length > 0 && (
              <CausalAnalysisCard
                rootCauses={selectedAlert.root_cause_analysis}
                recommendedInterventions={selectedAlert.recommended_actions}
                expectedImpact={selectedAlert.expected_impact}
                onInterventionSelect={(intervention) => console.log('Selected intervention', intervention)}
                projectId={projectId}
              />
            )}
            {selectedAlert.context && (
              <section className="context-block">
                <h4>Context</h4>
                <pre>{JSON.stringify(selectedAlert.context, null, 2)}</pre>
              </section>
            )}
          </aside>
        )}
      </div>
    </div>
  );
};

export default IntelligentAlertPanel;
