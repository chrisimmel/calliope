/**
 * v3 schemas. These mirror the Pydantic models in
 * ``calliope2/apps/api/calliope2/api/v3/schemas.py``. Keep in sync.
 */

export type Image = {
  url: string;
};

export type Video = {
  url: string;
  width?: number;
  height?: number;
  duration_seconds?: number;
  frame_rate?: number;
};

export type Frame = {
  id: number;
  number: number;
  text?: string | null;
  image_url?: string | null;
  video_url?: string | null;
  created_at: string;
};

export type Story = {
  id: number;
  slug?: string | null;
  title?: string | null;
  storyteller_name?: string | null;
  created_at: string;
  updated_at: string;
};

export type StoryDetail = Story & {
  frames: Frame[];
};

export type Storyteller = {
  name: string;
  description: string;
  illustrator?: string | null;   // default illustrator, if any
};

export type Illustrator = {
  name: string;
  description: string;
  outputs: 'image' | 'video';
  experimental: boolean;
};

export type CreateStoryRequest = {
  storyteller: string;
  illustrator?: string | null;
  inputs?: Record<string, unknown>;
  title?: string | null;
};

export type CreateStoryResponse = {
  story_id: number;
  task_id: string;
};

export type FrameCreateRequest = {
  illustrator?: string | null;
  inputs?: Record<string, unknown>;
};

export type FrameCreateResponse = {
  task_id: string;
};

export type Bookmark = {
  id: number;
  story_id: number;
  frame_id?: number | null;
  list_name?: string | null;
  comments?: string | null;
  is_public: boolean;
  created_at: string;
};

export type BookmarkCreateRequest = {
  story_id: number;
  frame_id?: number | null;
  list_name?: string | null;
  comments?: string | null;
  is_public?: boolean;
};

export type SearchHit = {
  frame_id: number;
  story_id: number;
  story_title?: string | null;
  frame_number: number;
  frame_text?: string | null;
  image_url?: string | null;
  distance: number;
};

export type SearchResponse = {
  query: string;
  hits: SearchHit[];
};

/**
 * Mirror of ``calliope2.realtime.task_status.TaskRecord``. Subscribers receive
 * this shape from Firestore listeners in ``services/firebase.ts``.
 */
export type TaskStatus = {
  task_id?: string;
  user_id: number;
  story_id: number;
  type: 'create_story' | 'create_frame';
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  error?: string | null;
  started_at: string;
  completed_at?: string | null;
};

export type MediaDevice = {
  kind: string;
  label: string;
  deviceId: string;
};

export const DEVICE_ID_NONE = 'none';
export const DEVICE_ID_DEFAULT = 'default';

export type FrameSeedMediaType = 'photo' | 'audio' | 'none';
