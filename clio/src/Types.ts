
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

type Strategy = {
    is_default_for_client: boolean,
    slug: string,
}

export {Frame, Image, Strategy, MediaDevice};
