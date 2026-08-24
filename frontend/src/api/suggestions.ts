import { apiClient } from './client';
import {
  PendingSuggestionsResponse,
  PricingSuggestion,
  ReorderSuggestion,
  StrategyConfig
} from '../types';

export const fetchPendingSuggestions = async (): Promise<PendingSuggestionsResponse> => {
  const response = await apiClient.get<PendingSuggestionsResponse>('/suggestions/pending');
  return response.data;
};

export const updatePricingSuggestion = async (
  suggestionId: number,
  action: 'ACCEPTED' | 'REJECTED'
): Promise<PricingSuggestion> => {
  const response = await apiClient.patch<PricingSuggestion>(`/pricing-suggestions/${suggestionId}`, {
    status: action,
  });
  return response.data;
};

export const updateReorderSuggestion = async (
  suggestionId: number,
  action: 'ACCEPTED' | 'REJECTED'
): Promise<ReorderSuggestion> => {
  const response = await apiClient.patch<ReorderSuggestion>(`/reorder-suggestions/${suggestionId}`, {
    status: action,
  });
  return response.data;
};

export const fetchStrategyConfig = async (): Promise<StrategyConfig> => {
  const response = await apiClient.get<StrategyConfig>('/config/strategy');
  return response.data;
};

export const switchStrategy = async (active_strategy: 'ai' | 'rule'): Promise<StrategyConfig> => {
  const response = await apiClient.patch<StrategyConfig>('/config/strategy', {
    active_strategy,
  });
  return response.data;
};

export const checkHealth = async (): Promise<{ status: string; database: string; active_strategy: string }> => {
  const response = await apiClient.get('/health');
  return response.data;
};
