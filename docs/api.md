# The Calliope Service and API

## FastAPI Framework
Calliope is built as a [FastAPI](https://fastapi.tiangolo.com/) service. This architecture provides several advantages:

* **Asynchronous Processing**: Enables Calliope to serve and make API and I/O requests asynchronously with very low latency
* **Strong Typing with Pydantic**: Uses [Pydantic](https://docs.pydantic.dev/latest/) to fully specify the schema of data flowing in and out of Calliope
* **Auto-generated Documentation**: Creates interactive API documentation automatically
* **Modern Python Features**: Takes advantage of modern Python's async/await syntax and type annotations
 
## API Overview

The API is accessible at:
- Local development: `http://localhost:8008`
- Production: `https://calliope-ugaidvq5sa-uc.a.run.app`

Auto-generated API documentation is available at:
- Local development: `http://localhost:8008/docs`
- Production: `https://calliope-ugaidvq5sa-uc.a.run.app/docs`

The API has three main components:

1. **Story API**: Endpoints for generating and retrieving story frames
2. **Media API**: Endpoints for managing media files (images, audio)
3. **Admin Interface**: Web interface for configuration (replacing the former config API)

## Authentication

Calliope uses API key authentication. The API key can be provided in two ways:

1. **HTTP Header** (preferred): Include the API key in the `X-Api-Key` header
   ```
   X-Api-Key: your_api_key_here
   ```

2. **Query Parameter** (for GET requests): Include the API key as the `api_key` query parameter
   ```
   /v1/frames/?api_key=your_api_key_here
   ```

For local development, you can set the API key in your `.env` file:
```
CALLIOPE_API_KEY=your_chosen_api_key
```

For access to the production API key, please contact the project administrators.

## Story API Endpoints

### GET/POST `/v1/frames/`

Generate new frames of a story based on various inputs.

#### Request Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `client_id` | string | **Required**. Unique identifier for the calling device or application |
| `client_type` | string | Optional type of the calling client (e.g., "clio", "sparrow") |
| `input_image` | string | Optional base64-encoded image to influence the story |
| `input_audio` | string | Optional base64-encoded audio sample to influence the story |
| `input_text` | string | Optional text input to influence the story |
| `story_id` | string | Optional ID of an existing story to continue |
| `strategy` | string | Optional name of the story strategy to use (e.g., "fern", "tamarisk") |
| `output_image_format` | string | Optional format for output images (e.g., "png", "jpg", "rgb565", "grayscale16") |
| `output_image_width` | integer | Optional width for output images (default varies by strategy) |
| `output_image_height` | integer | Optional height for output images (default varies by strategy) |
| `output_image_style` | string | Optional style prefix for images (e.g., "A watercolor of", "A pencil drawing of") |
| `debug` | boolean | Optional flag to include extra diagnostic information |

**Note**: Some image generation models (like Stable Diffusion) constrain output image dimensions to multiples of 64. Calliope will automatically adjust dimensions to accommodate these constraints, then scale the result to match the requested size.

#### Response Format

```json
{
  "frames": [
    {
      "image": {
        "format": "image/png",
        "width": 512,
        "height": 512,
        "url": "media/output_12345.png"
      },
      "text": "The story text for this frame...",
      "metadata": {}
    }
  ],
  "story_id": "story_12345",
  "story_frame_count": 5,
  "append_to_prior_frames": false,
  "strategy": "fern",
  "request_id": "req_67890",
  "generation_date": "2023-05-10 14:30:22.123456",
  "debug_data": {},
  "errors": []
}
```

### GET `/v1/story/`

Retrieve all frames from an existing story.

#### Request Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `client_id` | string | **Required**. Unique identifier for the calling device |
| `story_id` | string | Optional ID of the story to retrieve (defaults to client's current story) |
| `debug` | boolean | Optional flag to include extra diagnostic information |

#### Response Format

Same as the `/v1/frames/` endpoint, but returns all frames in the story.

### GET `/v1/stories/`

Retrieve a list of stories created by a client.

#### Request Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `client_id` | string | **Required**. Unique identifier for the calling device |

#### Response Format

```json
{
  "stories": [
    {
      "story_id": "story_12345",
      "title": "The Adventure Begins",
      "story_frame_count": 5,
      "is_bookmarked": false,
      "is_current": true,
      "is_read_only": false,
      "strategy_name": "fern",
      "created_for_sparrow_id": "client_67890",
      "thumbnail_image": {
        "format": "image/png",
        "width": 512,
        "height": 512,
        "url": "media/thumb_12345.png"
      },
      "date_created": "2023-05-10",
      "date_updated": "2023-05-11"
    }
  ],
  "request_id": "req_67890",
  "generation_date": "2023-05-12 09:45:33.123456"
}
```

### PUT `/v1/story/reset/`

Reset a client's story state, forcing Calliope to begin a new story.

#### Request Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `client_id` | string | **Required**. Unique identifier for the calling device |

#### Response

No content on success.

## Media API

### GET/PUT `/media/{filename}`

Get or upload media files used in story frames.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `filename` | string | The name of the media file |

#### PUT Request Body

The binary content of the media file.

#### GET Response

The binary content of the requested media file.

## Example API Usage

### Creating a New Story Frame with an Image Input

```bash
curl -X POST "http://localhost:8008/v1/frames/" \
  -H "X-Api-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "browser_12345",
    "client_type": "clio",
    "strategy": "fern",
    "input_image": "base64_encoded_image_data",
    "output_image_width": 512,
    "output_image_height": 512,
    "debug": true
  }'
```

### Continuing a Story with Text Input

```bash
curl -X POST "http://localhost:8008/v1/frames/" \
  -H "X-Api-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "browser_12345",
    "story_id": "story_67890",
    "input_text": "The dragon appeared suddenly from behind the mountain",
    "debug": true
  }'
```

### Retrieving an Existing Story

```bash
curl -X GET "http://localhost:8008/v1/story/?client_id=browser_12345&story_id=story_67890" \
  -H "X-Api-Key: your_api_key"
```

## Related Documentation

- [Calliope Admin Interface](https://github.com/chrisimmel/calliope/tree/main/docs/Admin.md) - Web interface for configuration management
- [Story Strategies](https://github.com/chrisimmel/calliope/tree/main/docs/stories.md) - Available storytelling strategies
- [Inference Models](https://github.com/chrisimmel/calliope/tree/main/docs/inference.md) - AI models used for generating content
