import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000/api/v1';

function App() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [websocket, setWebsocket] = useState(null);
  const [orderQuantities, setOrderQuantities] = useState({});

  // Fetch products from API
  const fetchProducts = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/products`);
      const data = await response.json();
      setProducts(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching products:', error);
      setLoading(false);
    }
  };

  // Handle order submission
  const handleOrder = async (productId, quantity) => {
    if (!quantity || quantity <= 0) return;
    
    try {
      await fetch(`${API_BASE_URL}/orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          product_id: productId,
          quantity: parseInt(quantity),
        }),
      });
      
      // Refresh products after order
      fetchProducts();
      
      // Reset quantity input
      setOrderQuantities(prev => ({
        ...prev,
        [productId]: ''
      }));
    } catch (error) {
      console.error('Error placing order:', error);
    }
  };

  // Handle quantity change
  const handleQuantityChange = (productId, value) => {
    setOrderQuantities(prev => ({
      ...prev,
      [productId]: value
    }));
  };

  // Connect to WebSocket
  useEffect(() => {
    // Fetch initial products
    fetchProducts();
    
    // Connect to WebSocket
    const ws = new WebSocket('ws://localhost:8000/api/v1/ws/products');
    
    ws.onopen = () => {
      console.log('Connected to WebSocket');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Received WebSocket message:', data);
      
      // Update product with recommendations
      setProducts(prevProducts => 
        prevProducts.map(product => 
          product.id === data.product_id 
            ? { 
                ...product, 
                pricingRecommendation: data.pricing_recommendation,
                reorderRecommendation: data.reorder_recommendation
              } 
            : product
        )
      );
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };
    
    setWebsocket(ws);
    
    // Cleanup on unmount
    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, []);

  if (loading) {
    return <div className="App">Loading...</div>;
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>StockPulse - AI-Driven Inventory Management</h1>
      </header>
      
      <main>
        <section className="demo-section">
          <h2>Inventory Management Dashboard</h2>
          
          <div className="instructions">
            <h3>Demo Instructions:</h3>
            <ul>
              <li><strong>Low Stock Demo:</strong> Place orders for T-Shirt (PRD-003) until stock falls below 15</li>
              <li><strong>Demand Spike Demo:</strong> Place multiple orders quickly for Hoodie (PRD-008)</li>
            </ul>
          </div>
          
          <table className="products-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>SKU</th>
                <th>Category</th>
                <th>Price ($)</th>
                <th>Stock Level</th>
                <th>Threshold</th>
                <th>Demand Velocity</th>
                <th>Status</th>
                <th>Recommended Price</th>
                <th>Reorder Quantity</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => (
                <tr 
                  key={product.id} 
                  className={
                    product.status === 'PRICE_REVIEW_PENDING' ? 'review-pending' : 
                    product.stock_level < product.reorder_threshold ? 'low-stock' : ''
                  }
                >
                  <td>{product.id}</td>
                  <td>{product.name}</td>
                  <td>{product.sku}</td>
                  <td>{product.category}</td>
                  <td>{product.current_price.toFixed(2)}</td>
                  <td>{product.stock_level}</td>
                  <td>{product.reorder_threshold}</td>
                  <td>{product.demand_velocity}</td>
                  <td>
                    <span className={`status ${product.status.toLowerCase().replace('_', '-')}`}>
                      {product.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td>
                    {product.pricingRecommendation ? (
                      <div>
                        <div>${product.pricingRecommendation.recommendedPrice.toFixed(2)}</div>
                        <small>({product.pricingRecommendation.direction})</small>
                      </div>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td>
                    {product.reorderRecommendation ? (
                      <div>
                        <div>{product.reorderRecommendation.recommendedQuantity}</div>
                        <small>Conf: {(product.reorderRecommendation.confidence * 100).toFixed(0)}%</small>
                      </div>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td>
                    <div className="order-controls">
                      <input
                        type="number"
                        min="1"
                        max={product.stock_level}
                        value={orderQuantities[product.id] || ''}
                        onChange={(e) => handleQuantityChange(product.id, e.target.value)}
                        placeholder="Qty"
                      />
                      <button 
                        onClick={() => handleOrder(product.id, orderQuantities[product.id])}
                        disabled={!orderQuantities[product.id] || orderQuantities[product.id] <= 0}
                      >
                        Order
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {/* Table will be added in next step */}
        </section>
      </main>
    </div>
  );
}

export default App;
