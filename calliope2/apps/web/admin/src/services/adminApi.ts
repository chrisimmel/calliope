/**
 * Typed wrappers for /v3/admin/*. Every call carries the Firebase ID token;
 * a 403 from the server means the signed-in user lacks ``is_admin``.
 */

import axios, { AxiosInstance } from 'axios';

import {
  AdminSearchResponse,
  AdminStory,
  AdminStoryDetail,
  AdminUser,
  Paginated,
} from '../types';
import { currentIdToken } from './firebase';

export class NotAuthorizedError extends Error {
  constructor(message = 'not authorized') {
    super(message);
    this.name = 'NotAuthorizedError';
  }
}

const client: AxiosInstance = axios.create({
  baseURL: process.env.API_BASE_URL || '',
  timeout: 30_000,
});

client.interceptors.request.use(async config => {
  const token = await currentIdToken();
  if (!token) throw new NotAuthorizedError('not signed in');
  config.headers = config.headers ?? {};
  config.headers.Authorization = `Bearer ${token}`;
  return config;
});

client.interceptors.response.use(
  r => r,
  err => {
    if (err.response?.status === 403) {
      return Promise.reject(new NotAuthorizedError(err.response.data?.detail));
    }
    return Promise.reject(err);
  }
);

export async function listStories(
  cursor?: number,
  q?: string
): Promise<Paginated<AdminStory>> {
  const r = await client.get<Paginated<AdminStory>>('/v3/admin/stories', {
    params: { cursor, q, limit: 50 },
  });
  return r.data;
}

export async function getStory(id: number): Promise<AdminStoryDetail> {
  const r = await client.get<AdminStoryDetail>(`/v3/admin/stories/${id}`);
  return r.data;
}

export async function listUsers(cursor?: number): Promise<Paginated<AdminUser>> {
  const r = await client.get<Paginated<AdminUser>>('/v3/admin/users', {
    params: { cursor, limit: 50 },
  });
  return r.data;
}

export async function search(q: string): Promise<AdminSearchResponse> {
  const r = await client.get<AdminSearchResponse>('/v3/admin/search', {
    params: { q },
  });
  return r.data;
}
