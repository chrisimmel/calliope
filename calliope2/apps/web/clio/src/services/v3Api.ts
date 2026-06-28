/**
 * Typed wrappers for the Calliope ``/v3`` API. Every call sends the current
 * user's Firebase ID token in the Authorization header; if there is no signed-in
 * user, the call throws ``NotAuthenticatedError`` before reaching the network.
 *
 * Use a single axios instance so a global interceptor handles auth in one place.
 */

import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

import {
  Bookmark,
  BookmarkCreateRequest,
  CreateStoryRequest,
  CreateStoryResponse,
  FrameCreateRequest,
  FrameCreateResponse,
  Illustrator,
  SearchResponse,
  Story,
  StoryDetail,
  Storyteller,
} from '../story/storyTypes';
import { currentIdToken } from './firebase';

export class NotAuthenticatedError extends Error {
  constructor() {
    super('not signed in');
    this.name = 'NotAuthenticatedError';
  }
}

const client: AxiosInstance = axios.create({
  baseURL: process.env.API_BASE_URL || '',
  timeout: 30_000,
});

client.interceptors.request.use(async config => {
  const token = await currentIdToken();
  if (!token) throw new NotAuthenticatedError();
  config.headers = config.headers ?? {};
  config.headers.Authorization = `Bearer ${token}`;
  return config;
});

async function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const r = await client.get<T>(url, config);
  return r.data;
}

async function post<T>(url: string, body?: unknown): Promise<T> {
  const r = await client.post<T>(url, body);
  return r.data;
}

async function del(url: string): Promise<void> {
  await client.delete(url);
}

// ----- Storytellers -----

export async function listStorytellers(): Promise<Storyteller[]> {
  return get('/v3/storytellers');
}

// ----- Illustrators -----

export async function listIllustrators(): Promise<Illustrator[]> {
  return get('/v3/illustrators');
}

// ----- Stories -----

export async function listStories(): Promise<Story[]> {
  return get('/v3/stories');
}

export async function getStory(id: number): Promise<StoryDetail> {
  return get(`/v3/stories/${id}`);
}

/** Resolve a shared/deep-linked story by slug. Non-owners get is_read_only. */
export async function getStoryBySlug(slug: string): Promise<StoryDetail> {
  return get(`/v3/stories/slug/${encodeURIComponent(slug)}`);
}

export async function createStory(
  body: CreateStoryRequest
): Promise<CreateStoryResponse> {
  return post('/v3/stories', body);
}

export async function createFrame(
  storyId: number,
  body: FrameCreateRequest
): Promise<FrameCreateResponse> {
  return post(`/v3/stories/${storyId}/frames`, body);
}

// ----- Bookmarks -----

export async function listBookmarks(): Promise<Bookmark[]> {
  return get('/v3/bookmarks');
}

export async function createBookmark(
  body: BookmarkCreateRequest
): Promise<Bookmark> {
  return post('/v3/bookmarks', body);
}

export async function deleteBookmark(id: number): Promise<void> {
  await del(`/v3/bookmarks/${id}`);
}

// ----- Search -----

export async function search(q: string, limit = 20): Promise<SearchResponse> {
  return get('/v3/search', { params: { q, limit } });
}
