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

export interface GenerationTrendItem {
  year: number;
  installed_capacity_kw: number;
  annual_generation_kwh: number;
  annual_income_yuan: number;
}

export interface GenerationProvinceDistributionItem {
  name: string;
  value: number;
}

export interface GenerationSummary {
  total_installed_capacity_kw: number;
  total_annual_generation_kwh: number;
  total_annual_income_yuan: number;
  province_count: number;
  city_count: number;
  county_count: number;
  yearly_trend: GenerationTrendItem[];
  province_distribution: GenerationProvinceDistributionItem[];
}

export function getGenerationsApi(params?: { province?: string; project_type?: string; limit?: number }): Promise<GenerationItem[]> {
  return request({
    url: '/generations',
    method: 'get',
    params
  }) as Promise<GenerationItem[]>;
}

export function getGenerationSummaryApi(): Promise<GenerationSummary> {
  return request({
    url: '/generation/summary',
    method: 'get',
  }) as Promise<GenerationSummary>;
}

