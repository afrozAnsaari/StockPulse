import React, { useState, useEffect, useCallback, useRef } from 'react';
import Navbar from './components/Navbar';
import SummaryCards from './components/SummaryCards';
import PendingReviewsQueue from './components/PendingReviewsQueue';
import ProductTable from './components/ProductTable';
import ProductDetailModal from './components/ProductDetailModal';
import StockModal from './components/StockModal';
import Toast from './components/Toast';

import {
  fetchProducts,
  updateProductStock,
  simulateOrder,
  requestManualPricing,
  requestManualReorder
} from './api/products';
import {
  fetchPendingSuggestions,
  updatePricingSuggestion,
  updateReorderSuggestion,
  fetchStrategyConfig,
  switchStrategy,
  checkHealth
} from './api/suggestions';

export default function App() {
  const [products, setProducts] = useState([]);
  const [pendingPricing, setPendingPricing] = useState([]);
  const [pendingReorder, setPendingReorder] = useState([]);
  const [activeStrategy, setActiveStrategy] = useState('ai');
  const [connected, setConnected] = useState(false);
  const [loadingInitial, setLoadingInitial] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isSwitchingStrategy, setIsSwitchingStrategy] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [processingId, setProcessingId] = useState(null);

  // Modals & Selection
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [stockModalProduct, setStockModalProduct] = useState(null);
  const [isUpdatingStock, setIsUpdatingStock] = useState(false);

  // Toast notifications
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = 'info') => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  const dismissToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Map products by ID for fast lookup
  const productsMap = React.useMemo(() => {
    const map = {};
    products.forEach((p) => {
      map[p.id] = p;
    });
    return map;
  }, [products]);

  // Data fetching helper
  const loadData = useCallback(async (isSilent = false) => {
    if (!isSilent) setIsRefreshing(true);
    try {
      const [prodData, suggData, configData] = await Promise.all([
        fetchProducts(),
        fetchPendingSuggestions(),
        fetchStrategyConfig(),
      ]);

      setProducts(prodData);
      setPendingPricing(suggData.pricing_suggestions || []);
      setPendingReorder(suggData.reorder_suggestions || []);
      setActiveStrategy(configData.active_strategy || 'ai');
      setConnected(true);

      // Keep selectedProduct in sync if open
      setSelectedProduct((prev) => {
        if (!prev) return null;
        return prodData.find((p) => p.id === prev.id) || prev;
      });
    } catch (err) {
      console.error('Error loading StockPulse data:', err);
      setConnected(false);
      if (!isSilent) addToast(`Failed to connect to backend: ${err.message}`, 'error');
    } finally {
      if (!isSilent) setIsRefreshing(false);
      setLoadingInitial(false);
    }
  }, [addToast]);

  // Initial load
  useEffect(() => {
    loadData(false);
  }, [loadData]);

  // Lightweight Polling loop (2.5s) to capture async background recommendations
  useEffect(() => {
    const interval = setInterval(() => {
      loadData(true);
    }, 2500);

    return () => clearInterval(interval);
  }, [loadData]);

  // Strategy Mode Toggle
  const handleStrategyToggle = async () => {
    const target = activeStrategy === 'ai' ? 'rule' : 'ai';
    setIsSwitchingStrategy(true);
    try {
      await switchStrategy(target);
      setActiveStrategy(target);
      addToast(
        `Switched strategy mode to: ${target.toUpperCase()} (${target === 'ai' ? 'LLM Advisor' : 'Deterministic Rule Engine'})`,
        'success'
      );
    } catch (err) {
      addToast(`Failed to switch strategy: ${err.message}`, 'error');
    } finally {
      setIsSwitchingStrategy(false);
    }
  };

  // Simulate Sale Action
  const handleSimulateSale = async (productId, quantity) => {
    setActionLoading(`sale-${productId}`);
    try {
      const order = await simulateOrder(productId, quantity);
      addToast(
        `Sale simulated! Sold ${order.quantity} unit(s) of ${productId}. Background recommendation loop triggered.`,
        'success'
      );
      // Immediately refresh
      await loadData(true);
    } catch (err) {
      addToast(`Sale simulation failed: ${err.message}`, 'error');
    } finally {
      setActionLoading(null);
    }
  };

  // Stock Adjustment Action
  const handleUpdateStock = async (productId, newStock) => {
    setIsUpdatingStock(true);
    try {
      const updated = await updateProductStock(productId, newStock);
      addToast(
        `Stock for ${updated.name} updated to ${updated.stock_level} units. (Status: ${updated.status})`,
        'success'
      );
      setStockModalProduct(null);
      await loadData(true);
    } catch (err) {
      addToast(`Stock update failed: ${err.message}`, 'error');
    } finally {
      setIsUpdatingStock(false);
    }
  };

  // Manual Pricing Suggestion
  const handleManualPricing = async (productId) => {
    setActionLoading(`suggest-pricing-${productId}`);
    try {
      const sugg = await requestManualPricing(productId);
      addToast(
        `Generated pricing recommendation for ${productId}: $${sugg.recommended_price.toFixed(2)} (${sugg.direction})`,
        'success'
      );
      await loadData(true);
    } catch (err) {
      addToast(`Failed to generate pricing recommendation: ${err.message}`, 'error');
    } finally {
      setActionLoading(null);
    }
  };

  // Manual Reorder Suggestion
  const handleManualReorder = async (productId) => {
    setActionLoading(`suggest-reorder-${productId}`);
    try {
      const sugg = await requestManualReorder(productId);
      addToast(
        `Generated reorder recommendation for ${productId}: Restock +${sugg.recommended_quantity} units`,
        'success'
      );
      await loadData(true);
    } catch (err) {
      addToast(`Failed to generate reorder recommendation: ${err.message}`, 'error');
    } finally {
      setActionLoading(null);
    }
  };

  // Accept Pricing Suggestion
  const handleAcceptPricing = async (suggestionId) => {
    setProcessingId(`pricing-${suggestionId}`);
    try {
      const accepted = await updatePricingSuggestion(suggestionId, 'ACCEPTED');
      addToast(
        `Pricing recommendation ACCEPTED! Price for ${accepted.product_id} updated to $${accepted.recommended_price.toFixed(2)}.`,
        'success'
      );
      await loadData(true);
    } catch (err) {
      addToast(`Failed to accept pricing suggestion: ${err.message}`, 'error');
    } finally {
      setProcessingId(null);
    }
  };

  // Reject Pricing Suggestion
  const handleRejectPricing = async (suggestionId) => {
    setProcessingId(`pricing-${suggestionId}`);
    try {
      await updatePricingSuggestion(suggestionId, 'REJECTED');
      addToast(`Pricing recommendation REJECTED.`, 'info');
      await loadData(true);
    } catch (err) {
      addToast(`Failed to reject pricing suggestion: ${err.message}`, 'error');
    } finally {
      setProcessingId(null);
    }
  };

  // Accept Reorder Suggestion
  const handleAcceptReorder = async (suggestionId) => {
    setProcessingId(`reorder-${suggestionId}`);
    try {
      const accepted = await updateReorderSuggestion(suggestionId, 'ACCEPTED');
      addToast(
        `Reorder recommendation ACCEPTED! Received inbound shipment of +${accepted.recommended_quantity} units for ${accepted.product_id}.`,
        'success'
      );
      await loadData(true);
    } catch (err) {
      addToast(`Failed to accept reorder suggestion: ${err.message}`, 'error');
    } finally {
      setProcessingId(null);
    }
  };

  // Reject Reorder Suggestion
  const handleRejectReorder = async (suggestionId) => {
    setProcessingId(`reorder-${suggestionId}`);
    try {
      await updateReorderSuggestion(suggestionId, 'REJECTED');
      addToast(`Reorder recommendation REJECTED.`, 'info');
      await loadData(true);
    } catch (err) {
      addToast(`Failed to reject reorder suggestion: ${err.message}`, 'error');
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div className="stockpulse-app">
      <Navbar
        activeStrategy={activeStrategy}
        onStrategyToggle={handleStrategyToggle}
        isSwitchingStrategy={isSwitchingStrategy}
        onRefresh={() => loadData(false)}
        isRefreshing={isRefreshing}
        connected={connected}
      />

      <main className="main-content">
        {loadingInitial ? (
          <div className="initial-loading">
            <div className="spinner"></div>
            <p>Connecting to StockPulse Core & Loading Catalog...</p>
          </div>
        ) : (
          <>
            {/* KPI Summary Banner */}
            <SummaryCards
              products={products}
              pendingPricingCount={pendingPricing.length}
              pendingReorderCount={pendingReorder.length}
            />

            {/* Pending Recommendations Review Queue (Human Checkpoint) */}
            <PendingReviewsQueue
              pricingSuggestions={pendingPricing}
              reorderSuggestions={pendingReorder}
              productsMap={productsMap}
              onAcceptPricing={handleAcceptPricing}
              onRejectPricing={handleRejectPricing}
              onAcceptReorder={handleAcceptReorder}
              onRejectReorder={handleRejectReorder}
              processingId={processingId}
            />

            {/* Catalog & Merchandising Grid */}
            <ProductTable
              products={products}
              onSimulateSale={handleSimulateSale}
              onOpenStockModal={(prod) => setStockModalProduct(prod)}
              onManualPricing={handleManualPricing}
              onManualReorder={handleManualReorder}
              onSelectProduct={(prod) => setSelectedProduct(prod)}
              actionLoading={actionLoading}
            />
          </>
        )}
      </main>

      {/* Product Detail Modal */}
      {selectedProduct && (
        <ProductDetailModal
          product={selectedProduct}
          onClose={() => setSelectedProduct(null)}
          onSimulateSale={handleSimulateSale}
          onOpenStockModal={(prod) => setStockModalProduct(prod)}
          onManualPricing={handleManualPricing}
          onManualReorder={handleManualReorder}
          onAcceptPricing={handleAcceptPricing}
          onRejectPricing={handleRejectPricing}
          onAcceptReorder={handleAcceptReorder}
          onRejectReorder={handleRejectReorder}
          processingId={processingId}
        />
      )}

      {/* Stock Adjustment Modal */}
      {stockModalProduct && (
        <StockModal
          product={stockModalProduct}
          onClose={() => setStockModalProduct(null)}
          onUpdateStock={handleUpdateStock}
          isUpdating={isUpdatingStock}
        />
      )}

      {/* Toast Notifications */}
      <Toast toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
