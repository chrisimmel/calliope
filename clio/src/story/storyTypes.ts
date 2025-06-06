
type Image = {
    url: string
}

type Video = {
    url: string,
    width?: number,
    height?: number,
    duration_seconds?: number,
    frame_rate?: number
}

type Snippet = {
    snippet_type: "image" | "audio" | "text" | "video",
    content: string,
    metadata: Record<string, any>
}

interface FrameMetadata {
    situation: string;
    [key: string]: any;
}

type Frame = {
    image?: Image,
    video?: Video,
    text?: string,
    metadata?: FrameMetadata,
}
type MediaDevice = {
    kind: string,
    label: string,
    deviceId: string,
}
const DEVICE_ID_NONE = "none";
const DEVICE_ID_DEFAULT = "default";

type Strategy = {
    is_default_for_client: boolean,
    is_experimental: boolean,
    slug: string,
}

type StoryStatus = {
    status: string;
    title?: string;
    created_at?: string;
    client_id?: string;
    strategy?: string;
    frame_count?: number;
    task_id?: string;
    processing_started_at?: string;
    progress?: string;
    error?: string;
    error_time?: string;
    completed_at?: string;
    updated_at?: string;
}

type StoryUpdate = {
    id: string;
    type: string;
    timestamp: string;
    task_id?: string;
    snippet_count?: number;
    image_url?: string;
    prompt?: string;
    frame_number?: number;
    has_image?: boolean;
    analysis_summary?: string;
}

type Story = {
    story_id: string
    title: string
    slug?: string | null
    story_frame_count: number
    is_bookmarked: boolean
    is_current: boolean
    is_read_only: boolean

    strategy_name: string
    created_for_sparrow_id: string
    thumbnail_image: Image | null

    date_created: string
    date_updated: string

    // Real-time status information
    status?: StoryStatus;
}

type FrameSeedMediaType = "photo" | "audio" | "none";

type Bookmark = {
    id: number;
    story_id: string;
    frame_number: number;
    frame_id: number;
    sparrow_id: string;
    comments?: string;
    date_created: string;
    date_updated: string;
    frame_text?: string;
    frame_image_url?: string;
}

type BookmarksResponse = {
    bookmarks: Bookmark[];
    request_id: string;
    generation_date: string;
}

export {DEVICE_ID_DEFAULT, DEVICE_ID_NONE, Frame, Image, Video, Snippet, Story, Strategy, MediaDevice, FrameSeedMediaType, Bookmark, BookmarksResponse, StoryStatus, StoryUpdate};
