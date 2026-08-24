export type ProductCategory = 'ELECTRONICS' | 'APPAREL' | 'HOME';

export type ProductStatus = 'ACTIVE' | 'PRICE_REVIEW_PENDING' | 'OUT_OF_STOCK';

export type PricingDirection = 'INCREASE' | 'DECREASE' | 'HOLD';

export type SuggestionStatus = 'PENDING' | 'ACCEPTED' | 'REJECTED';

export type TriggerReason = 'INITIAL' | 'INVENTORY_LOW' | 'DEMAND_SPIKE' | 'MANUAL';

export interface Product {
  id: string;
  sku: string;
  name: string;
  category: ProductCategory;
  current_price: number;
  stock_level: number;
  reorder_threshold: number;
  demand_velocity: number;
  status: ProductStatus;
  cost_price?: number | null;
  supplier_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PricingSuggestion {
  id: number;
  product_id: string;
  current_price: number;
  recommended_price: number;
  direction: PricingDirection;
  confidence: number;
  reasoning: string;
  status: SuggestionStatus;
  trigger_reason: TriggerReason;
  created_at: string;
  updated_at: string;
}

export interface ReorderSuggestion {
  id: number;
  product_id: string;
  current_stock: number;
  recommended_quantity: number;
  suggested_lead_time_days: number;
  confidence: number;
  reasoning: string;
  status: SuggestionStatus;
  trigger_reason: TriggerReason;
  created_at: string;
  updated_at: string;
}

export interface Order {
  order_id: number;
  product_id: string;
  quantity: number;
  timestamp: string;
}

export interface PendingSuggestionsResponse {
  pricing_suggestions: PricingSuggestion[];
  reorder_suggestions: ReorderSuggestion[];
}

export interface StrategyConfig {
  active_strategy: 'ai' | 'rule';
  project_name: string;
  llm_model: string;
  llm_base_url: string;
  demand_spike_multiplier: number;
  price_max_multiplier: number;
  price_min_multiplier: number;
}
