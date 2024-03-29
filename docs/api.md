# The Calliope Service and API

# FastAPI
Calliope is run as a [FastAPI](https://fastapi.tiangolo.com/) service. This has several advantages:

* It enables Calliope to serve and make API and I/O requests asynchronously with very low latency.
* It enables the use of [Pydantic](https://docs.pydantic.dev/latest/) to fully specify the schema of data flowing in and out of Calliope.
* It auto-generates API documentation.
 
# The API

The auto-generated API documentation is available at https://calliope-ugaidvq5sa-uc.a.run.app/docs.

The API consists mainly of two parts: serving a story (the _story_ API) and configuring sparrows and
flocks (the _config_ API). In addition, there are endpoints to help download and upload media files
used in support of a story.

## Authentication
Authentication to the Calliope API is done via an API key. To run locally, you can set the key to whatever
you like via the `CALLIOPE_API_KEY` environment variable. For access to the production API key, please contact
Chris Immel or Mikal Hart.

The API key is normally sent as the value of the `X-Api-Header` HTTP header, but for HTTP get requests (generally
for development and testing) can also be given as the value of the `api_key` query parameter on the URL.

## The Story API
The story API consists of the `/v1/frames/` endpoint, which delivers frames of a story in response
to either a POST or GET request.

### `/v1/frames/` parameters

* `client_id`: string - the ID of the calling client. A required string that should uniquely identify the calling device or application.
* `client_type`: string - the type of the calling client. An optional string identifying the _kind_ of calling device or application.
* `input_image`: string - An input image, encoded in base64, optional (harvested image, for now, common web image formats work, jpg, png, etc.).
* `input_audio`: string - An audio sample, encoded in base64, optional (harvested sound).
* `location`: string - The geolocation of the client, optional.
* `input_text`: string - Harvested text from client environment, or an arbitrary string sent from the client.
* `output_image_format`: string - The requested image format. Can be ,
* `output_image_width`: int - The requested image width. The final image may be padded or cropped to fit this dimension.
* `output_image_height`: int - The requested image height. The final image may be padded or cropped to fit this dimension.
* `output_image_style`: string - The requested image style, given as English text, like "A watercolor of" or "A pencil drawing of".
* `output_text_style`: string - The requested text style (currently unused).
* `max_output_text_length`: int - The maximum output text length (currently unused).
* `strategy`: string - The name of the strategy to be used to generate the frames.
* `debug`: boolean - Whether to include extra diagnostic information in the response.

Hint: Some image generation models (notably Stable Diffusion) constrain output image dimensions to multiples of 64.
When asked for an image size that doesn't fit this constraint, Calliope will use the nearest greater multiple of 64
in both width and height, then scale, pad, or crop as needed to fit the resulting image to the requested size.

## The Media API
The media API allows a caller to either PUT or GET a media file for use in story frames at `/media/{filename}`.

## The Configuration API
(The former configuration API has been replaced by the [Calliope Admin](https://github.com/chrisimmel/calliope/tree/main/docs/Admin.md) application.)
