import React, { useMemo, useState } from 'react';
import {
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  DollarSign,
  PlayCircle,
  Target,
  TrendingUp,
} from 'lucide-react';
import {
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  Cell,
} from 'recharts';
import { apiFetch } from '../../lib/api';
import './styles/CausalAnalysisCard.css';

const palette = ['#f97316', '#ef4444', '#eab308', '#10b981', '#6366f1'];

const CausalAnalysisCard = ({
  rootCauses = {},
  recommendedInterventions = [],
  expectedImpact = {},
  onInterventionSelect = () => {},
  projectId,
}) => {
  const [expanded, setExpanded] = useState({ causes: true, interventions: true });
  const [selectedIntervention, setSelectedIntervention] = useState(null);
  const [simulation, setSimulation] = useState(null);
  const chartData = useMemo(() =>
    Object.entries(rootCauses)
      .slice(0, 5)
      .map(([name, effect], index) => ({
        name,
        effect,
        value: Math.abs(effect),
        fill: palette[index % palette.length],
      })),
  [rootCauses]);

  const toggleSection = (section) => {
    setExpanded((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const simulate = async (intervention) => {
    setSelectedIntervention(intervention);
    try {
      const response = await apiFetch('/api/intelligence/simulate-intervention', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intervention, projectId }),
      });
      if (!response.ok) {
        throw new Error('Failed to simulate intervention');
      }
      const data = await response.json();
      setSimulation(data);
    } catch (error) {
      setSimulation({ error: error.message });
    }
  };

  return (
    <div className="causal-analysis-card">
      <div className="card-header">
        <div>
          <h3>Root Cause Analysis</h3>
          <p className="card-subtitle">Data-driven insights for proactive mitigation</p>
        </div>
        <div className="impact-summary">
          <span>
            <Clock size={16} />
            {Math.round(expectedImpact.total_delay_reduction_days || 0)} days saved
          </span>
          <span>
            <DollarSign size={16} />
            {Math.round((expectedImpact.net_benefit || 0) / 1000)}k benefit
          </span>
        </div>
      </div>

      <section className="analysis-section">
        <button type="button" className="section-header" onClick={() => toggleSection('causes')}>
          <div className="section-title">
            <TrendingUp size={18} />
            <span>Top Root Causes</span>
          </div>
          {expanded.causes ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
        {expanded.causes && (
          <div className="section-content causes">
            <div className="causes-chart">
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <RadialBarChart innerRadius="30%" outerRadius="100%" data={chartData}>
                    <RadialBar dataKey="value" clockWise />
                    <Tooltip formatter={(value, name, props) => [`${(props.payload.effect * 100).toFixed(1)}%`, props.payload.name]} />
                    {chartData.map((entry, index) => (
                      <Cell key={entry.name} fill={entry.fill} />
                    ))}
                  </RadialBarChart>
                </ResponsiveContainer>
              ) : (
                <div className="empty-state">
                  <AlertCircle size={18} />
                  <span>No causal signals detected yet.</span>
                </div>
              )}
            </div>
            <div className="causes-list">
              {chartData.map((item, index) => (
                <div key={item.name} className="cause-item">
                  <span className="cause-rank">#{index + 1}</span>
                  <div className="cause-details">
                    <span className="cause-name">{item.name.replaceAll('_', ' ')}</span>
                    <span className="cause-effect">{(item.effect * 100).toFixed(1)}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      <section className="analysis-section">
        <button type="button" className="section-header" onClick={() => toggleSection('interventions')}>
          <div className="section-title">
            <Target size={18} />
            <span>Recommended Interventions</span>
          </div>
          {expanded.interventions ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
        {expanded.interventions && (
          <div className="section-content interventions">
            {recommendedInterventions.length === 0 && (
              <div className="empty-state">
                <AlertCircle size={18} />
                <span>No interventions available yet.</span>
              </div>
            )}
            {recommendedInterventions.map((intervention, index) => {
              const isSelected = selectedIntervention && selectedIntervention.variable === intervention.variable;
              const roi = typeof intervention.roi === 'number' ? `${(intervention.roi * 100).toFixed(0)}%` : 'n/a';
              return (
                <article
                  key={intervention.variable}
                  className={`intervention-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => simulate(intervention)}
                >
                  <header>
                    <span className="intervention-rank">#{index + 1}</span>
                    <h4>{intervention.action}</h4>
                    <span className="roi" data-roi={intervention.roi}>{roi}</span>
                  </header>
                  <dl className="intervention-details">
                    <div>
                      <dt>Implementation</dt>
                      <dd>{intervention.implementation}</dd>
                    </div>
                    <div>
                      <dt>Deployment Time</dt>
                      <dd>{intervention.time_to_implement}</dd>
                    </div>
                    <div>
                      <dt>Cost</dt>
                      <dd>${Math.round((intervention.cost || 0) / 1000)}k</dd>
                    </div>
                    <div>
                      <dt>Payback</dt>
                      <dd>{intervention.payback_period_days || 0} days</dd>
                    </div>
                  </dl>
                  <button type="button" className="simulate-button" onClick={(event) => {
                    event.stopPropagation();
                    simulate(intervention);
                  }}>
                    <PlayCircle size={16} />
                    Simulate Impact
                  </button>
                </article>
              );
            })}
          </div>
        )}
      </section>

      {simulation && (
        <section className="analysis-section simulation">
          <header className="section-header static">
            <div className="section-title">
              <Target size={18} />
              <span>Simulation Result</span>
            </div>
          </header>
          {simulation.error ? (
            <div className="empty-state">
              <AlertCircle size={18} />
              <span>{simulation.error}</span>
            </div>
          ) : (
            <div className="simulation-grid">
              <div>
                <span className="label">Schedule Impact</span>
                <strong>-{simulation.schedule_improvement} days</strong>
              </div>
              <div>
                <span className="label">Cost Impact</span>
                <strong>${Math.round(simulation.cost_savings / 1000)}k</strong>
              </div>
              <div>
                <span className="label">Confidence</span>
                <strong>{Math.round((simulation.confidence || 0) * 100)}%</strong>
              </div>
            </div>
          )}
          {selectedIntervention && !simulation?.error && (
            <button type="button" className="apply-button" onClick={() => onInterventionSelect(selectedIntervention)}>
              Apply Intervention
            </button>
          )}
        </section>
      )}
    </div>
  );
};

export default CausalAnalysisCard;
