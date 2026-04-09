import request from '@/api/request';

export interface CostItem {
  name: string;
  category: string;
  province?: string | null;
  unit_cost_yuan_per_kw?: number | null;
  component_price_yuan_per_w?: number | null;
  effective_date?: string | null;
  source: string;
  source_url?: string | null;
}

export function getCostsApi(params?: { category?: string; province?: string; limit?: number }): Promise<CostItem[]> {
  return request({
    url: '/costs',
    method: 'get',
    params
  }) as Promise<CostItem[]>;
}

