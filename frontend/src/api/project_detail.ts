import request from '@/api/request';

export interface ProjectDetail {
  id: number;
  name: string;
  capacity_kw: number;
  commissioning_date: string;
  longitude: number;
  latitude: number;
  province: string;
}

export function getProjectDetailApi(projectId: number): Promise<ProjectDetail> {
  return request({
    url: `/projects/${projectId}`,
    method: 'get'
  }) as Promise<ProjectDetail>;
}

