
type Image = {
    url: string
}
interface FrameMetadata {
    situation: string;
    [key: string]: any;
}
type Frame = {
    image?: Image,
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

type Story = {
    story_id: string
    title: string
    story_frame_count: number
    is_bookmarked: boolean
    is_current: boolean
    is_read_only: boolean

    strategy_name: string
    created_for_sparrow_id: string
    thumbnail_image: Image | null

    date_created: string
    date_updated: string
}

type FrameSeedMediaType = "photo" | "audio" | "none";


export {DEVICE_ID_DEFAULT, DEVICE_ID_NONE, Frame, Image, Story, Strategy, MediaDevice, FrameSeedMediaType};
