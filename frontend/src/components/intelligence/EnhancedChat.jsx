import React, { useEffect, useRef, useState } from 'react';
import { AlertCircle, Brain, Send, TrendingUp } from 'lucide-react';
import UncertaintyIndicator from './UncertaintyIndicator';
import { apiFetch } from '../../lib/api';
import './styles/EnhancedChat.css';

const EnhancedChat = ({ projectId }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;
    containerRef.current.scrollTop = containerRef.current.scrollHeight;
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) {
      return;
    }
    const userMessage = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    try {
      const response = await apiFetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage.content }),
      });
      if (!response.ok) {
        throw new Error('Chat request failed');
      }
      const data = await response.json();
      const aiMessage = {
        id: `ai-${Date.now()}`,
        type: 'ai',
        content: data.response,
        timestamp: new Date().toISOString(),
        citations: data.context_docs || [],
        confidence: data.confidence,
        uncertaintyBounds: data.uncertainty_bounds,
        confidenceExplanation: data.confidence_explanation,
        causalAnalysis: data.causal_analysis,
        actionableInsight: data.actionable_insight,
      };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          type: 'error',
          content: error.message,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  const renderMessage = (message) => {
    if (message.type === 'user') {
      return (
        <div key={message.id} className="chat-message user-message">
          <div className="bubble">{message.content}</div>
          <time>{new Date(message.timestamp).toLocaleTimeString()}</time>
        </div>
      );
    }

    if (message.type === 'error') {
      return (
        <div key={message.id} className="chat-message error-message">
          <AlertCircle size={16} />
          <span>{message.content}</span>
        </div>
      );
    }

    return (
      <div key={message.id} className="chat-message ai-message">
        <div className="ai-header">
          <Brain size={18} />
          <span>Diriyah Intelligence</span>
          {typeof message.confidence === 'number' && (
            <UncertaintyIndicator
              confidence={message.confidence}
              uncertainty={1 - (message.confidence || 0)}
              confidenceInterval={message.uncertaintyBounds}
              explanation={message.confidenceExplanation}
              showDetails={false}
            />
          )}
        </div>
        <div className="bubble">{message.content}</div>
        {message.causalAnalysis?.identified && (
          <div className="ai-card">
            <div className="ai-card-header">
              <TrendingUp size={16} />
              <span>Root Cause Signals</span>
            </div>
            <div className="ai-card-body">
              {message.causalAnalysis.top_causes?.map(([cause, effect]) => (
                <div key={cause} className="cause-row">
                  <span>{cause}</span>
                  <strong>{(effect * 100).toFixed(1)}%</strong>
                </div>
              ))}
              {message.causalAnalysis.recommended_action && (
                <div className="recommended-action">
                  <strong>Recommended:</strong>
                  <span>{message.causalAnalysis.recommended_action.action}</span>
                </div>
              )}
            </div>
          </div>
        )}
        {message.actionableInsight && (
          <div className="ai-card highlight">
            <AlertCircle size={16} />
            <span>{message.actionableInsight}</span>
          </div>
        )}
        {message.citations && message.citations.length > 0 && (
          <ul className="citations">
            {message.citations.map((citation, idx) => (
              <li key={`${message.id}-citation-${idx}`}>
                <span className="citation-index">[{idx + 1}]</span>
                <span>{citation}</span>
              </li>
            ))}
          </ul>
        )}
        <time>{new Date(message.timestamp).toLocaleTimeString()}</time>
      </div>
    );
  };

  return (
    <div className="enhanced-chat">
      <header className="chat-header">
        <div>
          <h3>Intelligent Project Assistant</h3>
          <p>Answers enriched with uncertainty and causal analysis</p>
        </div>
      </header>
      <div className="chat-body" ref={containerRef}>
        {messages.map(renderMessage)}
        {loading && (
          <div className="chat-loading">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
        )}
      </div>
      <footer className="chat-input">
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="Ask about delays, costs, or project risks..."
          rows={2}
        />
        <button type="button" onClick={sendMessage} disabled={loading || !input.trim()}>
          <Send size={18} />
        </button>
      </footer>
    </div>
  );
};

export default EnhancedChat;
