import React, { useState } from 'react';
import { AlertTriangle, CheckCircle, HelpCircle, Info } from 'lucide-react';
import './styles/UncertaintyIndicator.css';

const getConfidenceMeta = (confidence) => {
  if (confidence > 0.9) {
    return { label: 'High', color: '#10b981', Icon: CheckCircle };
  }
  if (confidence > 0.7) {
    return { label: 'Moderate', color: '#f59e0b', Icon: Info };
  }
  if (confidence > 0.5) {
    return { label: 'Low', color: '#ef4444', Icon: AlertTriangle };
  }
  return { label: 'Very Low', color: '#dc2626', Icon: HelpCircle };
};

const clampInterval = (interval = []) => {
  if (!Array.isArray(interval) || interval.length !== 2) {
    return [0, 1];
  }
  const [min, max] = interval;
  return [Math.max(0, min), Math.min(1, max)];
};

const UncertaintyIndicator = ({
  confidence = 0,
  uncertainty = 0,
  confidenceInterval = [0, 1],
  explanation = '',
  shouldEscalate = false,
  showDetails = false,
}) => {
  const [expanded, setExpanded] = useState(showDetails);
  const meta = getConfidenceMeta(confidence);
  const [lower, upper] = clampInterval(confidenceInterval);
  const confidencePercent = Math.round(confidence * 100);
  const uncertaintyPercent = Math.max(0, Math.min(100, uncertainty * 100));

  return (
    <div className="uncertainty-indicator" data-escalate={shouldEscalate}>
      <button
        type="button"
        className="uncertainty-header"
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
      >
        <div className="confidence-badge" style={{ backgroundColor: meta.color }}>
          <meta.Icon size={16} />
          <span>{confidencePercent}%</span>
        </div>
        <div className="confidence-bar" aria-hidden="true">
          <div className="confidence-fill" style={{ width: `${confidencePercent}%`, backgroundColor: meta.color }} />
          <div
            className="uncertainty-band"
            style={{
              left: `${lower * 100}%`,
              right: `${(1 - upper) * 100}%`,
              backgroundColor: meta.color,
            }}
          />
        </div>
        {shouldEscalate && (
          <div className="escalation-badge">
            <AlertTriangle size={14} />
            <span>Review Required</span>
          </div>
        )}
      </button>

      {(expanded || showDetails) && (
        <div className="uncertainty-details">
          <div className="detail-row">
            <span className="detail-label">Confidence Level</span>
            <span className="detail-value">{meta.label}</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Confidence</span>
            <span className="detail-value">{confidencePercent}%</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Uncertainty</span>
            <span className="detail-value">{uncertaintyPercent.toFixed(1)}%</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Confidence Interval</span>
            <span className="detail-value">
              [{Math.round(lower * 100)}%, {Math.round(upper * 100)}%]
            </span>
          </div>
          {explanation && (
            <div className="explanation">
              <Info size={14} />
              <span>{explanation}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default UncertaintyIndicator;
