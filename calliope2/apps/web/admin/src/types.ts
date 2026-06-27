/**
 * Mirrors apps/api/calliope2/api/v3/admin/schemas.py. Keep in sync.
 */

export interface AdminUser {
  id: number;
  firebase_uid: string;
  email: string | null;
  display_name: string | null;
  is_admin: boolean;
  created_at: string;
}

export interface AdminStory {
  id: number;
  owner_id: number;
  owner_email: string | null;
  slug: string | null;
  title: string | null;
  storyteller_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminFrame {
  id: number;
  story_id: number;
  number: number;
  text: string | null;
  image_url: string | null;
  video_url: string | null;
  source_image_url: string | null;
  has_embedding: boolean;
  created_at: string;
}

export interface AdminStoryDetail extends AdminStory {
  metadata: Record<string, unknown> | null;
  frames: AdminFrame[];
}

export interface PageMeta {
  next_cursor: number | null;
  total: number | null;
}

export interface Paginated<T> {
  items: T[];
  page: PageMeta;
}

export interface AdminSearchHit {
  frame_id: number;
  story_id: number;
  story_title: string | null;
  owner_id: number | null;
  owner_email: string | null;
  frame_number: number;
  frame_text: string | null;
  image_url: string | null;
  distance: number;
}

export interface AdminSearchResponse {
  query: string;
  hits: AdminSearchHit[];
}
