import React from 'react';

export default function SummaryCards({ products, pendingPricingCount, pendingReorderCount }) {
  const totalProducts = products.length;
  const lowStockProducts = products.filter(
    (p) => p.stock_level > 0 && p.stock_level < p.reorder_threshold
  ).length;
  const reviewPendingProducts = products.filter(
    (p) => p.status === 'PRICE_REVIEW_PENDING'
  ).length;
  const outOfStockProducts = products.filter(
    (p) => p.stock_level === 0 || p.status === 'OUT_OF_STOCK'
  ).length;
  const totalPendingRecommendations = pendingPricingCount + pendingReorderCount;

  const cards = [
    {
      title: 'Total Products',
      value: totalProducts,
      icon: '📦',
      color: 'blue',
      subtitle: 'Active catalog SKUs',
    },
    {
      title: 'Low Stock Alerts',
      value: lowStockProducts,
      icon: '⚠️',
      color: 'amber',
      subtitle: 'Below safety threshold',
    },
    {
      title: 'Pending Reviews',
      value: reviewPendingProducts,
      icon: '📋',
      color: 'purple',
      subtitle: 'Products awaiting human review',
    },
    {
      title: 'Out of Stock',
      value: outOfStockProducts,
      icon: '🚫',
      color: 'rose',
      subtitle: 'Zero inventory runway',
    },
    {
      title: 'AI Recommendations',
      value: totalPendingRecommendations,
      icon: '✨',
      color: 'cyan',
      subtitle: `${pendingPricingCount} pricing · ${pendingReorderCount} reorders`,
    },
  ];

  return (
    <div className="summary-cards-grid">
      {cards.map((card, idx) => (
        <div key={idx} className={`summary-card card-${card.color}`}>
          <div className="card-header">
            <span className="card-title">{card.title}</span>
            <span className="card-icon">{card.icon}</span>
          </div>
          <div className="card-value">{card.value}</div>
          <div className="card-subtitle">{card.subtitle}</div>
        </div>
      ))}
    </div>
  );
}
