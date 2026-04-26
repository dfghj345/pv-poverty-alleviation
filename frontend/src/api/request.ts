import axios from 'axios';
import type { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import { useProjectStore } from '@/store/project';
import type { HttpErrorBody } from '@/api/types';

const rawApiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || '/api/v1';
const normalizedApiBaseUrl = rawApiBaseUrl.replace(/\/+$/, '') || '/api/v1';

const request: AxiosInstance = axios.create({
  baseURL: normalizedApiBaseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' }
});

let activeRequestCount = 0;

function showLoading(): void {
  if (activeRequestCount === 0) {
    useProjectStore().setLoading(true);
  }
  activeRequestCount++;
}

function hideLoading(): void {
  activeRequestCount--;
  if (activeRequestCount === 0) {
    useProjectStore().setLoading(false);
  }
}

request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    showLoading();
    return config;
  },
  (error: AxiosError) => {
    hideLoading();
    return Promise.reject(error);
  }
);

request.interceptors.response.use(
  (response: AxiosResponse) => {
    hideLoading();
    const body = response.data as Record<string, unknown> | undefined;
    if (body && typeof body === 'object' && 'data' in body) {
      const status = (body as any).status;
      const code = (body as any).code;
      const success = (body as any).success;
      if (success === true || status === 'success' || code === 200) {
        return (body as any).data as AxiosResponse['data'];
      }
    }
    return response.data as AxiosResponse['data'];
  },
  (error: AxiosError) => {
    hideLoading();
    const data = error.response?.data as HttpErrorBody | undefined;
    const detail = data?.detail;
    const message = data?.message ?? (typeof detail === 'string' ? detail : undefined);
    let errorMsg = message || '网络请求异常，请检查网络连接';
    const status = error.response?.status;
    if (!message && status) {
      switch (status) {
        case 400: errorMsg = '请求参数错误 (400)'; break;
        case 401: errorMsg = '未授权，请重新登录 (401)'; break;
        case 404: errorMsg = '未找到资源 (404)'; break;
        case 500: errorMsg = '后端服务器异常 (500)'; break;
        case 504: errorMsg = '网关超时 (504)'; break;
      }
    }
    console.error('[API Error]', errorMsg, error);
    return Promise.reject(new Error(errorMsg));
  }
);

export default request;
