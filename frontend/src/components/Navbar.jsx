import React from 'react';

export default function Navbar({
  activeStrategy,
  onStrategyToggle,
  isSwitchingStrategy,
  onRefresh,
  isRefreshing,
  connected
}) {
  return (
    <header className="navbar">
      <div className="nav-brand">
        <div className="brand-icon">⚡</div>
        <div className="brand-text">
          <h1>StockPulse</h1>
          <span className="brand-subtitle">AI-Driven Merchandising & Dynamic Pricing</span>
        </div>
      </div>

      <div className="nav-controls">
        <div className="system-status">
          <span className={`status-dot ${connected ? 'online' : 'offline'}`}></span>
          <span className="status-label">{connected ? 'Backend Live' : 'Connecting...'}</span>
        </div>

        <div className="strategy-switcher">
          <span className="strategy-label">Strategy Mode:</span>
          <button
            className={`strategy-btn ${activeStrategy === 'ai' ? 'active-ai' : 'active-rule'}`}
            onClick={onStrategyToggle}
            disabled={isSwitchingStrategy}
            title="Click to switch between AI LLM Advisor and Rule-Based Engine"
          >
            {activeStrategy === 'ai' ? (
              <>
                <span className="ai-icon">✨</span>
                <span>AI Advisor (LLM)</span>
              </>
            ) : (
              <>
                <span className="rule-icon">⚙️</span>
                <span>Rule Engine (Deterministic)</span>
              </>
            )}
          </button>
        </div>

        <button
          className="refresh-btn"
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Manual refresh catalog & pending reviews"
        >
          <span className={`refresh-icon ${isRefreshing ? 'spin' : ''}`}>🔄</span>
          <span>Refresh</span>
        </button>
      </div>
    </header>
  );
}
