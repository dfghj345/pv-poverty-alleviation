import request from '@/api/request';

export interface GenerationItem {
  project_name: string;
  province?: string | null;
  capacity_kw?: number | null;
  annual_generation_kwh?: number | null;
  annual_income_yuan?: number | null;
  project_type?: string | null;
  status?: string | null;
  effective_date?: string | null;
  source: string;
  source_url?: string | null;
}

export function getGenerationsApi(params?: { province?: string; project_type?: string; limit?: number }): Promise<GenerationItem[]> {
  return request({
    url: '/generations',
    method: 'get',
    params
  }) as Promise<GenerationItem[]>;
}

