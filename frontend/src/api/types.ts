// ========== 与后端 Pydantic 对齐 ==========

export interface ProjectInDB {
  id: number;
  name: string;
  capacity: number;
  commissioning_date: string;
  longitude: number;
  latitude: number;
}

export interface ProjectPagination {
  total: number;
  items: ProjectInDB[];
}

export interface CalcRequest {
  capacity_kw: number;
  equivalent_hours: number;
  total_investment: number;
  electricity_price: number;
  loan_ratio?: number;
  annual_degradation?: number;
}

export interface CalcResponse {
  npv: number;
  irr: number;
  lcoe: number;
  annual_cash_flows: number[];
}

export interface CalcROIResponse extends CalcResponse {
  source_equivalent_hours: number;
  location: { lon: number; lat: number };
  total_generation_discounted: number;
}

/** 后端 HTTPException 响应体 */
export interface HttpErrorBody {
  message?: string;
  detail?: string | string[] | Record<string, unknown>;
}

// ========== 地图与业务扩展 ==========

export interface GeoPoint {
  type: 'Point';
  coordinates: [number, number];
}

export interface StationProperties {
  project_id?: number;
  site_id: string;
  address: string;
  area_sqm: number;
  installed_capacity: number;
  status: 'planning' | 'constructing' | 'operating';
  built_year?: number;
  province?: string;
}

export interface PowerStationFeature {
  type: 'Feature';
  geometry: GeoPoint;
  properties: StationProperties;
}

/** 兼容旧决策引擎的测算结果（summary + yearly_details） */
export interface CalcSummary {
  total_investment: number;
  total_20y_profit: number;
  npv: number;
  irr: number | null;
  payback_period: number;
  is_viable: boolean;
}

export interface YearlyDetail {
  year: number;
  generation_kwh: number;
  net_profit: number;
  cumulative_profit: number;
}

export interface CalcResultData {
  summary: CalcSummary;
  yearly_details: YearlyDetail[];
}

export interface PolicyRecord {
  id: number;
  province: string;
  price: number;
  policy_date: string;
  created_at?: string;
}
