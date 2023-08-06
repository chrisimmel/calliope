
type Image = {
    url: string
}
type Frame = {
    image?: Image,
    text?: string,
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
    slug: string,
}

export {DEVICE_ID_DEFAULT, DEVICE_ID_NONE, Frame, Image, Strategy, MediaDevice};
