import React, { useState } from 'react';

export default function ProductTable({
  products,
  onSimulateSale,
  onOpenStockModal,
  onManualPricing,
  onManualReorder,
  onSelectProduct,
  actionLoading
}) {
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [selectedStatus, setSelectedStatus] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [saleQuantities, setSaleQuantities] = useState({});

  const categories = ['ALL', 'ELECTRONICS', 'APPAREL', 'HOME'];
  const statuses = ['ALL', 'ACTIVE', 'PRICE_REVIEW_PENDING', 'OUT_OF_STOCK'];

  const filteredProducts = products.filter((p) => {
    if (selectedCategory !== 'ALL' && p.category !== selectedCategory) return false;
    if (selectedStatus !== 'ALL' && p.status !== selectedStatus) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        p.name.toLowerCase().includes(q) ||
        p.sku.toLowerCase().includes(q) ||
        p.id.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const handleQtyChange = (productId, val) => {
    setSaleQuantities((prev) => ({
      ...prev,
      [productId]: Math.max(1, parseInt(val, 10) || 1),
    }));
  };

  const handleSaleSubmit = (productId) => {
    const qty = saleQuantities[productId] || 1;
    onSimulateSale(productId, qty);
  };

  const renderStatusBadge = (status) => {
    switch (status) {
      case 'ACTIVE':
        return <span className="status-badge status-active">ACTIVE</span>;
      case 'PRICE_REVIEW_PENDING':
        return <span className="status-badge status-review">PRICE REVIEW PENDING</span>;
      case 'OUT_OF_STOCK':
        return <span className="status-badge status-out">OUT OF STOCK</span>;
      default:
        return <span className="status-badge">{status}</span>;
    }
  };

  return (
    <section className="catalog-section">
      <div className="catalog-header">
        <div className="catalog-title-group">
          <h2>Product Catalog & Merchandising Grid</h2>
          <span className="product-count-label">Showing {filteredProducts.length} of {products.length} products</span>
        </div>

        <div className="catalog-filters">
          <div className="search-box">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              placeholder="Search by SKU, product name, or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button className="clear-search" onClick={() => setSearchQuery('')}>✕</button>
            )}
          </div>

          <div className="category-pills">
            {categories.map((cat) => (
              <button
                key={cat}
                className={`category-pill ${selectedCategory === cat ? 'active' : ''}`}
                onClick={() => setSelectedCategory(cat)}
              >
                {cat}
              </button>
            ))}
          </div>

          <div className="status-select-wrap">
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="status-select"
            >
              {statuses.map((st) => (
                <option key={st} value={st}>
                  {st === 'ALL' ? 'All Statuses' : st.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="table-container">
        <table className="merch-table">
          <thead>
            <tr>
              <th>Product & SKU</th>
              <th>Category</th>
              <th>Current Price</th>
              <th>Inventory / Threshold</th>
              <th>24h Velocity</th>
              <th>Status</th>
              <th className="th-actions">Simulate Sale & Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredProducts.map((product) => {
              const isLowStock = product.stock_level > 0 && product.stock_level < product.reorder_threshold;
              const isOutOfStock = product.stock_level === 0;
              const isOrderProcessing = actionLoading === `sale-${product.id}`;
              const isPricingProcessing = actionLoading === `suggest-pricing-${product.id}`;
              const isReorderProcessing = actionLoading === `suggest-reorder-${product.id}`;

              return (
                <tr
                  key={product.id}
                  className={`product-row ${
                    product.status === 'PRICE_REVIEW_PENDING'
                      ? 'row-review-pending'
                      : isLowStock
                      ? 'row-low-stock'
                      : isOutOfStock
                      ? 'row-out-of-stock'
                      : ''
                  }`}
                >
                  <td className="td-product">
                    <div className="product-info-cell">
                      <button
                        className="btn-product-name"
                        onClick={() => onSelectProduct(product)}
                        title="Click to view full product details & metrics"
                      >
                        {product.name}
                      </button>
                      <div className="sku-id-line">
                        <span className="badge-sku">{product.sku}</span>
                        <span className="badge-id">{product.id}</span>
                      </div>
                    </div>
                  </td>

                  <td>
                    <span className={`badge-cat cat-${product.category.toLowerCase()}`}>
                      {product.category}
                    </span>
                  </td>

                  <td className="td-price">
                    <span className="price-display">${product.current_price.toFixed(2)}</span>
                  </td>

                  <td className="td-stock">
                    <div className="stock-cell">
                      <div className="stock-num-line">
                        <span className={`stock-val ${isOutOfStock ? 'val-out' : isLowStock ? 'val-low' : 'val-good'}`}>
                          {product.stock_level} units
                        </span>
                        <span className="threshold-val">/ {product.reorder_threshold} thres</span>
                      </div>
                      <div className="stock-meter-bg">
                        <div
                          className={`stock-meter-fill ${isOutOfStock ? 'meter-out' : isLowStock ? 'meter-low' : 'meter-good'}`}
                          style={{
                            width: `${Math.min(100, Math.round((product.stock_level / (product.reorder_threshold * 2)) * 100))}%`,
                          }}
                        ></div>
                      </div>
                      {isLowStock && <span className="low-stock-tag">⚠️ Low Stock</span>}
                    </div>
                  </td>

                  <td className="td-velocity">
                    <div className="velocity-badge">
                      <span className="vel-icon">⚡</span>
                      <span className="vel-val">{product.demand_velocity}</span>
                      <span className="vel-unit">/24h</span>
                    </div>
                  </td>

                  <td>{renderStatusBadge(product.status)}</td>

                  <td className="td-actions">
                    <div className="actions-cluster">
                      {/* Simulate Sale Controls */}
                      <div className="simulate-sale-box">
                        <input
                          type="number"
                          min="1"
                          max={product.stock_level || 1}
                          value={saleQuantities[product.id] || 1}
                          onChange={(e) => handleQtyChange(product.id, e.target.value)}
                          className="input-qty"
                          disabled={isOutOfStock || isOrderProcessing}
                          title="Enter quantity to simulate sale"
                        />
                        <button
                          className="btn-sell"
                          onClick={() => handleSaleSubmit(product.id)}
                          disabled={isOutOfStock || isOrderProcessing}
                          title="Simulate sale: atomically decrements stock and triggers agentic recommendation loop"
                        >
                          {isOrderProcessing ? '...' : '⚡ Sell'}
                        </button>
                      </div>

                      {/* Stock Adjust */}
                      <button
                        className="btn-action-icon"
                        onClick={() => onOpenStockModal(product)}
                        title="Directly update stock level"
                      >
                        📦 Stock
                      </button>

                      {/* Manual Suggestions */}
                      <button
                        className="btn-action-icon"
                        onClick={() => onManualPricing(product.id)}
                        disabled={isPricingProcessing}
                        title="Request on-demand pricing recommendation"
                      >
                        {isPricingProcessing ? '...' : '🏷️ Price'}
                      </button>

                      <button
                        className="btn-action-icon"
                        onClick={() => onManualReorder(product.id)}
                        disabled={isReorderProcessing}
                        title="Request on-demand reorder recommendation"
                      >
                        {isReorderProcessing ? '...' : '🔄 Reorder'}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
