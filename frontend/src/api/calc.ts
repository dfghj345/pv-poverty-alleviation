import request from '@/api/request';
import type { CalcRequest, CalcResponse } from '@/api/types';

const BASE = '/calc';

export function estimateCalc(body: CalcRequest): Promise<CalcResponse> {
  return request.post(`${BASE}/estimate`, body) as Promise<CalcResponse>;
}
