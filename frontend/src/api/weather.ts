import request from '@/api/request';

export interface WeatherRadiationItem {
  latitude: number;
  longitude: number;
  province?: string | null;
  city?: string | null;
  location_source?: string | null;
  day: string;
  shortwave_radiation_sum_kwh_m2: number;
  temperature_mean_c?: number | null;
  precipitation_sum_mm?: number | null;
  wind_speed_mean_m_s?: number | null;
  annual_radiation_sum_kwh_m2?: number | null;
  equivalent_hours_h?: number | null;
  source: string;
  source_url?: string | null;
}

export function getWeatherRadiationApi(params: {
  latitude?: number;
  longitude?: number;
  province?: string;
  city?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
}): Promise<WeatherRadiationItem[]> {
  return request({
    url: '/weather/radiation',
    method: 'get',
    params
  }) as Promise<WeatherRadiationItem[]>;
}
