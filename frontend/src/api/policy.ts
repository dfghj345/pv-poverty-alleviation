import request from '@/api/request';

export interface PolicyTariffItem {
  province: string;
  benchmark_price_yuan_per_kwh: number;
  subsidy_yuan_per_kwh?: number | null;
  policy_date?: string | null;
  policy_type?: string | null;
  source_url?: string | null;
}

export function getPoliciesApi(params?: { province?: string; limit?: number }): Promise<PolicyTariffItem[]> {
  return request({
    url: '/policies',
    method: 'get',
    params
  }) as Promise<PolicyTariffItem[]>;
}

