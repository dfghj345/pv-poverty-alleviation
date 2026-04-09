import request from '@/api/request';

// 1. 定义单条光伏项目的类型
export interface ProjectItem {
  id: number;
  name: string;
  capacity: number;
  commissioning_date: string;
  longitude: number;
  latitude: number;
}

// 2. 定义分页返回的类型
export interface ProjectPagination {
  total: number;
  items: ProjectItem[];
}

// 3. 定义看板返回的数据结构
export interface DashboardStats {
  total_capacity_mw: number;
  annual_generation_yi: number;
  farmers_benefited: number;
  carbon_reduction_wt: number;
  revenue_years: string[];
  revenue_data: number[];
  province_distribution: { name: string; value: number }[];
}

// 4. 获取地图点位列表 API (强制声明返回 Promise 解包后的类型)
export function getProjectListApi(skip = 0, limit = 500): Promise<ProjectPagination> {
  return request({
    url: '/projects/',
    method: 'get',
    params: { skip, limit }
  }) as Promise<ProjectPagination>;
}

// 5. 获取全局看板数据 API (强制声明返回 Promise 解包后的类型)
export function getDashboardStatsApi(): Promise<DashboardStats> {
  return request({
    url: '/projects/dashboard-stats',
    method: 'get'
  }) as Promise<DashboardStats>;
}

// 6. 触发收益计算 API
export function calculateRoiApi(projectId: number): Promise<any> {
  return request({
    url: `/projects/${projectId}/calculate-roi`,
    method: 'post'
  }) as Promise<any>;
}