import request from '@/api/request';

export interface PanelDataListParams {
  page?: number;
  page_size?: number;
  province?: string;
  city?: string;
  year?: number;
  keyword?: string;
}

export interface PanelDataFiltersParams {
  province?: string;
}

export interface PanelDataItem {
  id: number;
  province: string;
  city: string;
  year: number;
  pv_installed_capacity_wan_kw?: number | null;
  disposable_income_per_capita_yuan?: number | null;
  healthcare_expenditure_per_capita_yuan?: number | null;
  urban_rural_income_ratio?: number | null;
  mortality_per_mille?: number | null;
  pm25_annual_avg_ug_per_m3?: number | null;
  gdp_100m_yuan?: number | null;
  source_sheet?: string | null;
  source_workbook?: string | null;
}

export interface PanelDataPage {
  items: PanelDataItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface PanelDataFilters {
  provinces: string[];
  cities: string[];
  years: number[];
}

export interface PanelDataStatsItem {
  province?: string;
  year?: number;
  count: number;
  value: number;
}

export interface PanelDataStats {
  total_count: number;
  province_count: number;
  city_count: number;
  year_count: number;
  by_province: Array<Required<Pick<PanelDataStatsItem, 'province'>> & Pick<PanelDataStatsItem, 'count' | 'value'>>;
  by_year: Array<Required<Pick<PanelDataStatsItem, 'year'>> & Pick<PanelDataStatsItem, 'count' | 'value'>>;
}

export interface PanelDataMapItem {
  province: string;
  city: string;
  year: number;
  value: number;
  count: number;
}

export function getPanelDataListApi(params?: PanelDataListParams): Promise<PanelDataPage> {
  return request({
    url: '/panel-data',
    method: 'get',
    params,
  }) as Promise<PanelDataPage>;
}

export function getPanelDataFiltersApi(params?: PanelDataFiltersParams): Promise<PanelDataFilters> {
  return request({
    url: '/panel-data/filters',
    method: 'get',
    params,
  }) as Promise<PanelDataFilters>;
}

export function getPanelDataStatsApi(): Promise<PanelDataStats> {
  return request({
    url: '/panel-data/stats',
    method: 'get',
  }) as Promise<PanelDataStats>;
}

export function getPanelDataMapApi(params?: Omit<PanelDataListParams, 'page' | 'page_size'>): Promise<PanelDataMapItem[]> {
  return request({
    url: '/panel-data/map',
    method: 'get',
    params,
  }) as Promise<PanelDataMapItem[]>;
}
