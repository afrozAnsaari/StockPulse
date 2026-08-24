import React from 'react';

export default function PendingReviewsQueue({
  pricingSuggestions,
  reorderSuggestions,
  productsMap,
  onAcceptPricing,
  onRejectPricing,
  onAcceptReorder,
  onRejectReorder,
  processingId
}) {
  const totalPending = pricingSuggestions.length + reorderSuggestions.length;

  if (totalPending === 0) {
    return (
      <div className="review-queue-empty">
        <div className="empty-icon">✅</div>
        <h3>Review Queue Clean</h3>
        <p>No pending pricing or reorder recommendations requiring merchandiser approval.</p>
        <div className="empty-hint">
          Simulate a sale on <strong>PRD-003</strong> (Low Stock) or <strong>PRD-008</strong> (Demand Spike) to trigger the agentic loop.
        </div>
      </div>
    );
  }

  const renderTriggerBadge = (trigger) => {
    switch (trigger) {
      case 'INVENTORY_LOW':
        return <span className="trigger-badge trigger-low">⚠️ INVENTORY_LOW</span>;
      case 'DEMAND_SPIKE':
        return <span className="trigger-badge trigger-spike">🔥 DEMAND_SPIKE</span>;
      case 'INITIAL':
        return <span className="trigger-badge trigger-initial">📌 INITIAL</span>;
      case 'MANUAL':
      default:
        return <span className="trigger-badge trigger-manual">👤 MANUAL</span>;
    }
  };

  return (
    <section className="review-queue-section">
      <div className="section-header">
        <div className="section-title-group">
          <h2>Pending Review Queue (Human Checkpoint)</h2>
          <span className="queue-count-badge">{totalPending} Pending</span>
        </div>
        <p className="section-desc">
          StockPulse operates on an agentic human-in-the-loop paradigm: Recommendations are autonomously reasoned and proposed, but require explicit merchandiser approval before mutating live prices or inventory.
        </p>
      </div>

      <div className="queue-columns">
        {/* Pricing Suggestions Column */}
        <div className="queue-column">
          <div className="column-header">
            <h3>🏷️ Pricing Recommendations ({pricingSuggestions.length})</h3>
          </div>

          {pricingSuggestions.length === 0 ? (
            <div className="column-empty">No pending pricing reviews</div>
          ) : (
            <div className="suggestions-list">
              {pricingSuggestions.map((sugg) => {
                const product = productsMap[sugg.product_id] || {
                  name: sugg.product_id,
                  sku: sugg.product_id,
                };
                const priceDiff = sugg.recommended_price - sugg.current_price;
                const percentDiff = ((priceDiff / sugg.current_price) * 100).toFixed(1);
                const isProcessing = processingId === `pricing-${sugg.id}`;

                return (
                  <div key={`pricing-${sugg.id}`} className="suggestion-card pricing-card">
                    <div className="card-top">
                      <div className="product-meta">
                        <span className="product-sku">{product.sku}</span>
                        <span className="product-name">{product.name}</span>
                      </div>
                      {renderTriggerBadge(sugg.trigger_reason)}
                    </div>

                    <div className="price-comparison-box">
                      <div className="price-col">
                        <span className="price-label">Current</span>
                        <span className="price-val">${sugg.current_price.toFixed(2)}</span>
                      </div>
                      <div className="price-arrow">
                        <span className={`direction-badge dir-${sugg.direction.toLowerCase()}`}>
                          {sugg.direction === 'INCREASE' ? '↗' : sugg.direction === 'DECREASE' ? '↘' : '→'} {sugg.direction}
                        </span>
                        <span className="diff-val">
                          {priceDiff >= 0 ? `+${priceDiff.toFixed(2)}` : priceDiff.toFixed(2)} ({percentDiff}%)
                        </span>
                      </div>
                      <div className="price-col">
                        <span className="price-label">Proposed</span>
                        <span className="price-val proposed">${sugg.recommended_price.toFixed(2)}</span>
                      </div>
                    </div>

                    <div className="confidence-row">
                      <span className="conf-label">Confidence:</span>
                      <div className="conf-bar-bg">
                        <div
                          className="conf-bar-fill"
                          style={{ width: `${Math.round(sugg.confidence * 100)}%` }}
                        ></div>
                      </div>
                      <span className="conf-value">{Math.round(sugg.confidence * 100)}%</span>
                    </div>

                    <div className="reasoning-box">
                      <span className="reasoning-title">💡 Reasoning & Market Analysis:</span>
                      <p className="reasoning-text">{sugg.reasoning}</p>
                    </div>

                    <div className="card-actions">
                      <button
                        className="btn-accept"
                        onClick={() => onAcceptPricing(sugg.id)}
                        disabled={isProcessing}
                      >
                        {isProcessing ? 'Applying...' : `✓ Accept ($${sugg.recommended_price.toFixed(2)})`}
                      </button>
                      <button
                        className="btn-reject"
                        onClick={() => onRejectPricing(sugg.id)}
                        disabled={isProcessing}
                      >
                        ✕ Reject
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Reorder Suggestions Column */}
        <div className="queue-column">
          <div className="column-header">
            <h3>📦 Restocking & Reorder Recommendations ({reorderSuggestions.length})</h3>
          </div>

          {reorderSuggestions.length === 0 ? (
            <div className="column-empty">No pending reorder reviews</div>
          ) : (
            <div className="suggestions-list">
              {reorderSuggestions.map((sugg) => {
                const product = productsMap[sugg.product_id] || {
                  name: sugg.product_id,
                  sku: sugg.product_id,
                };
                const isProcessing = processingId === `reorder-${sugg.id}`;

                return (
                  <div key={`reorder-${sugg.id}`} className="suggestion-card reorder-card">
                    <div className="card-top">
                      <div className="product-meta">
                        <span className="product-sku">{product.sku}</span>
                        <span className="product-name">{product.name}</span>
                      </div>
                      {renderTriggerBadge(sugg.trigger_reason)}
                    </div>

                    <div className="reorder-stats-box">
                      <div className="stat-item">
                        <span className="stat-label">Current Stock</span>
                        <span className="stat-val">{sugg.current_stock} units</span>
                      </div>
                      <div className="stat-arrow">+</div>
                      <div className="stat-item highlight">
                        <span className="stat-label">Restock Order</span>
                        <span className="stat-val">+{sugg.recommended_quantity} units</span>
                      </div>
                      <div className="stat-arrow">=</div>
                      <div className="stat-item">
                        <span className="stat-label">Target Level</span>
                        <span className="stat-val">{sugg.current_stock + sugg.recommended_quantity} units</span>
                      </div>
                    </div>

                    <div className="meta-pills-row">
                      <span className="meta-pill">⏱️ Lead Time: {sugg.suggested_lead_time_days} days</span>
                      <span className="meta-pill">🎯 Confidence: {Math.round(sugg.confidence * 100)}%</span>
                    </div>

                    <div className="reasoning-box">
                      <span className="reasoning-title">💡 Inventory Runway & Replenishment Logic:</span>
                      <p className="reasoning-text">{sugg.reasoning}</p>
                    </div>

                    <div className="card-actions">
                      <button
                        className="btn-accept-reorder"
                        onClick={() => onAcceptReorder(sugg.id)}
                        disabled={isProcessing}
                      >
                        {isProcessing ? 'Receiving...' : `✓ Accept Restock (+${sugg.recommended_quantity} units)`}
                      </button>
                      <button
                        className="btn-reject"
                        onClick={() => onRejectReorder(sugg.id)}
                        disabled={isProcessing}
                      >
                        ✕ Reject
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
