import React, { useState } from 'react';

export default function StockModal({ product, onClose, onUpdateStock, isUpdating }) {
  const [newStock, setNewStock] = useState(product ? product.stock_level : 0);

  if (!product) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    onUpdateStock(product.id, newStock);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content stock-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Adjust Inventory: {product.name}</h3>
          <button className="btn-close-modal" onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body">
          <p className="stock-modal-info">
            Current Stock: <strong>{product.stock_level} units</strong> · Safety Threshold: <strong>{product.reorder_threshold} units</strong>
          </p>

          <div className="form-group">
            <label htmlFor="stock-input">New Stock Level:</label>
            <input
              id="stock-input"
              type="number"
              min="0"
              value={newStock}
              onChange={(e) => setNewStock(Math.max(0, parseInt(e.target.value, 10) || 0))}
              className="input-stock-field"
              required
              autoFocus
            />
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-modal-cancel" onClick={onClose} disabled={isUpdating}>
              Cancel
            </button>
            <button type="submit" className="btn-modal-save" disabled={isUpdating}>
              {isUpdating ? 'Updating...' : 'Save Stock Level'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
