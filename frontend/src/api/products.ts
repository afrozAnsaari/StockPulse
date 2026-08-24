import { apiClient } from './client';
import { Product, Order, PricingSuggestion, ReorderSuggestion } from '../types';

export const fetchProducts = async (params?: { category?: string; status?: string }): Promise<Product[]> => {
  const response = await apiClient.get<Product[]>('/products', { params });
  return response.data;
};

export const fetchProductById = async (id: string): Promise<Product> => {
  const response = await apiClient.get<Product>(`/products/${id}`);
  return response.data;
};

export const updateProductStock = async (id: string, stock_level: number): Promise<Product> => {
  const response = await apiClient.patch<Product>(`/products/${id}/stock`, { stock_level });
  return response.data;
};

export const simulateOrder = async (productId: string, quantity: number = 1): Promise<Order> => {
  const response = await apiClient.post<Order>(`/products/${productId}/orders`, { quantity });
  return response.data;
};

export const requestManualPricing = async (productId: string): Promise<PricingSuggestion> => {
  const response = await apiClient.post<PricingSuggestion>(`/products/${productId}/suggest-pricing`);
  return response.data;
};

export const requestManualReorder = async (productId: string): Promise<ReorderSuggestion> => {
  const response = await apiClient.post<ReorderSuggestion>(`/products/${productId}/suggest-reorder`);
  return response.data;
};

export const fetchProductPricingSuggestions = async (productId: string): Promise<PricingSuggestion[]> => {
  const response = await apiClient.get<PricingSuggestion[]>(`/products/${productId}/pricing-suggestions`);
  return response.data;
};

export const fetchProductReorderSuggestions = async (productId: string): Promise<ReorderSuggestion[]> => {
  const response = await apiClient.get<ReorderSuggestion[]>(`/products/${productId}/reorder-suggestions`);
  return response.data;
};
