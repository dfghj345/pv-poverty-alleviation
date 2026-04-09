import request from '@/api/request';

export type RegionDomain = 'all' | 'weather' | 'policy' | 'poverty' | 'cost' | 'generation';

export interface RegionLocation {
  province: string;
  city: string;
  latitude: number;
  longitude: number;
  source: string;
}

export function getRegionProvincesApi(domain: RegionDomain = 'all'): Promise<string[]> {
  return request({
    url: '/regions/provinces',
    method: 'get',
    params: { domain }
  }) as Promise<string[]>;
}

export function getRegionCitiesApi(params: { province: string; domain?: RegionDomain }): Promise<string[]> {
  return request({
    url: '/regions/cities',
    method: 'get',
    params
  }) as Promise<string[]>;
}

export function getRegionLocationApi(params: { province: string; city: string }): Promise<RegionLocation | null> {
  return request({
    url: '/regions/location',
    method: 'get',
    params
  }) as Promise<RegionLocation | null>;
}

export function getRegionWeatherLocationApi(params: { province: string; city: string }): Promise<RegionLocation | null> {
  return request({
    url: '/regions/weather-location',
    method: 'get',
    params
  }) as Promise<RegionLocation | null>;
}

export function reverseRegionByCoordinateApi(params: { latitude: number; longitude: number }): Promise<RegionLocation | null> {
  return request({
    url: '/regions/reverse',
    method: 'get',
    params
  }) as Promise<RegionLocation | null>;
}
