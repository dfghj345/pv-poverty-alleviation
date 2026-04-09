import request from '@/api/request';

export interface PovertyCountyItem {
  province: string;
  city?: string | null;
  county: string;
  population?: number | null;
  income_per_capita_yuan?: number | null;
  energy_condition?: string | null;
  tags?: string | null;
  adcode?: string | null;
  source: string;
  source_url?: string | null;
}

export function getPovertyCountiesApi(params?: {
  province?: string;
  city?: string;
  skip?: number;
  limit?: number;
}): Promise<PovertyCountyItem[]> {
  return request({
    url: '/poverty/counties',
    method: 'get',
    params
  }) as Promise<PovertyCountyItem[]>;
}
