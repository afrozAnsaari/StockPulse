import React, { useState, useEffect } from 'react';
import { fetchProductPricingSuggestions, fetchProductReorderSuggestions } from '../api/products';

export default function ProductDetailModal({
  product,
  onClose,
  onSimulateSale,
  onOpenStockModal,
  onManualPricing,
  onManualReorder,
  onAcceptPricing,
  onRejectPricing,
  onAcceptReorder,
  onRejectReorder,
  processingId
}) {
  const [pricingHistory, setPricingHistory] = useState([]);
  const [reorderHistory, setReorderHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [saleQty, setSaleQty] = useState(1);

  useEffect(() => {
    if (!product) return;
    let isMounted = true;
    setLoadingHistory(true);

    Promise.all([
      fetchProductPricingSuggestions(product.id),
      fetchProductReorderSuggestions(product.id),
    ])
      .then(([pSuggestions, rSuggestions]) => {
        if (isMounted) {
          setPricingHistory(pSuggestions);
          setReorderHistory(rSuggestions);
          setLoadingHistory(false);
        }
      })
      .catch((err) => {
        console.error('Error fetching product suggestions history:', err);
        if (isMounted) setLoadingHistory(false);
      });

    return () => {
      isMounted = false;
    };
  }, [product, processingId]);

  if (!product) return null;

  const runwayDays =
    product.demand_velocity > 0
      ? (product.stock_level / product.demand_velocity).toFixed(1)
      : '∞ (No 24h demand)';

  const grossMargin =
    product.cost_price && product.current_price > 0
      ? (((product.current_price - product.cost_price) / product.current_price) * 100).toFixed(1)
      : null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content product-detail-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="modal-badge-sku">{product.sku}</span>
            <h2>{product.name}</h2>
            <span className="modal-id">ID: {product.id}</span>
          </div>
          <button className="btn-close-modal" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          {/* Top Metrics Grid */}
          <div className="detail-metrics-grid">
            <div className="metric-box">
              <span className="metric-lbl">Current Price</span>
              <span className="metric-val price">${product.current_price.toFixed(2)}</span>
              {product.cost_price && (
                <span className="metric-sub">Cost: ${product.cost_price.toFixed(2)} {grossMargin && `(${grossMargin}% margin)`}</span>
              )}
            </div>

            <div className="metric-box">
              <span className="metric-lbl">Stock Level</span>
              <span className={`metric-val ${product.stock_level === 0 ? 'out' : product.stock_level < product.reorder_threshold ? 'low' : ''}`}>
                {product.stock_level} units
              </span>
              <span className="metric-sub">Reorder Threshold: {product.reorder_threshold} units</span>
            </div>

            <div className="metric-box">
              <span className="metric-lbl">24h Demand Velocity</span>
              <span className="metric-val velocity">{product.demand_velocity} orders/24h</span>
              <span className="metric-sub">Estimated Runway: ~{runwayDays} days</span>
            </div>

            <div className="metric-box">
              <span className="metric-lbl">Lifecycle Status</span>
              <span className={`status-pill ${product.status.toLowerCase().replace(/_/g, '-')}`}>
                {product.status.replace(/_/g, ' ')}
              </span>
              {product.supplier_id && (
                <span className="metric-sub">Supplier: {product.supplier_id}</span>
              )}
            </div>
          </div>

          {/* Direct Simulation & Action Bar */}
          <div className="modal-actions-bar">
            <div className="sim-group">
              <label>Simulate Sale:</label>
              <input
                type="number"
                min="1"
                max={product.stock_level || 1}
                value={saleQty}
                onChange={(e) => setSaleQty(Math.max(1, parseInt(e.target.value, 10) || 1))}
                className="input-modal-qty"
                disabled={product.stock_level === 0}
              />
              <button
                className="btn-modal-sell"
                onClick={() => onSimulateSale(product.id, saleQty)}
                disabled={product.stock_level === 0}
              >
                ⚡ Sell {saleQty} {saleQty === 1 ? 'Unit' : 'Units'}
              </button>
            </div>

            <div className="trigger-group">
              <button className="btn-modal-trigger" onClick={() => onOpenStockModal(product)}>
                📦 Adjust Stock
              </button>
              <button className="btn-modal-trigger" onClick={() => onManualPricing(product.id)}>
                🏷️ Request Pricing Recommendation
              </button>
              <button className="btn-modal-trigger" onClick={() => onManualReorder(product.id)}>
                🔄 Request Reorder Recommendation
              </button>
            </div>
          </div>

          {/* Recommendations History Section */}
          <div className="history-sections">
            <div className="history-pane">
              <h3>Pricing Recommendation History ({pricingHistory.length})</h3>
              {loadingHistory ? (
                <div className="history-loading">Loading recommendations...</div>
              ) : pricingHistory.length === 0 ? (
                <div className="history-empty">No pricing suggestions generated yet.</div>
              ) : (
                <div className="history-cards-list">
                  {pricingHistory.map((sugg) => (
                    <div key={sugg.id} className={`history-card status-${sugg.status.toLowerCase()}`}>
                      <div className="hcard-top">
                        <span className="hcard-price">${sugg.current_price.toFixed(2)} → <strong>${sugg.recommended_price.toFixed(2)}</strong></span>
                        <span className={`hcard-status badge-${sugg.status.toLowerCase()}`}>{sugg.status}</span>
                      </div>
                      <div className="hcard-meta">
                        <span>Trigger: <strong>{sugg.trigger_reason}</strong></span>
                        <span>Confidence: <strong>{Math.round(sugg.confidence * 100)}%</strong></span>
                      </div>
                      <p className="hcard-reasoning">{sugg.reasoning}</p>
                      {sugg.status === 'PENDING' && (
                        <div className="hcard-actions">
                          <button
                            className="btn-haccept"
                            onClick={() => onAcceptPricing(sugg.id)}
                            disabled={processingId === `pricing-${sugg.id}`}
                          >
                            ✓ Accept
                          </button>
                          <button
                            className="btn-hreject"
                            onClick={() => onRejectPricing(sugg.id)}
                            disabled={processingId === `pricing-${sugg.id}`}
                          >
                            ✕ Reject
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="history-pane">
              <h3>Reorder Recommendation History ({reorderHistory.length})</h3>
              {loadingHistory ? (
                <div className="history-loading">Loading recommendations...</div>
              ) : reorderHistory.length === 0 ? (
                <div className="history-empty">No reorder suggestions generated yet.</div>
              ) : (
                <div className="history-cards-list">
                  {reorderHistory.map((sugg) => (
                    <div key={sugg.id} className={`history-card status-${sugg.status.toLowerCase()}`}>
                      <div className="hcard-top">
                        <span className="hcard-price">Restock: <strong>+{sugg.recommended_quantity} units</strong> (from {sugg.current_stock})</span>
                        <span className={`hcard-status badge-${sugg.status.toLowerCase()}`}>{sugg.status}</span>
                      </div>
                      <div className="hcard-meta">
                        <span>Lead Time: <strong>{sugg.suggested_lead_time_days} days</strong></span>
                        <span>Confidence: <strong>{Math.round(sugg.confidence * 100)}%</strong></span>
                      </div>
                      <p className="hcard-reasoning">{sugg.reasoning}</p>
                      {sugg.status === 'PENDING' && (
                        <div className="hcard-actions">
                          <button
                            className="btn-haccept"
                            onClick={() => onAcceptReorder(sugg.id)}
                            disabled={processingId === `reorder-${sugg.id}`}
                          >
                            ✓ Accept Restock
                          </button>
                          <button
                            className="btn-hreject"
                            onClick={() => onRejectReorder(sugg.id)}
                            disabled={processingId === `reorder-${sugg.id}`}
                          >
                            ✕ Reject
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
