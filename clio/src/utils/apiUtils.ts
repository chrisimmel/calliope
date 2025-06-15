/**
 * Utility functions for working with the Calliope API
 */

import { Snippet } from '../story/storyTypes';

/**
 * Converts image or audio data to a snippet object for the v2 API
 *
 * @param image Base64 encoded image data (optional)
 * @param audio Base64 encoded audio data (optional)
 * @returns Array of snippet objects for the API
 */
export function createSnippets(image: string | null, audio: string | null): Snippet[] {
  const snippets: Snippet[] = [];

  // Process image if provided
  if (image) {
    // Extract base64 data if it includes the data URI prefix
    const parts = image.split(",");
    const base64Data = (parts.length > 1) ? parts[1] : image;

    snippets.push({
      snippet_type: "image",
      content: base64Data,
      metadata: {}
    });
  }

  // Process audio if provided
  if (audio) {
    // Extract base64 data if it includes the data URI prefix
    const parts = audio.split(",");
    const base64Data = (parts.length > 1) ? parts[1] : audio;

    snippets.push({
      snippet_type: "audio",
      content: base64Data,
      metadata: {}
    });
  }

  return snippets;
}

/**
 * Creates an API request payload for the v2 API
 */
export function createFrameRequestPayload(
  clientId: string,
  image: string | null = null,
  audio: string | null = null,
  strategy: string | null = null,
  generateVideo: boolean = false
) {
  // Create snippets from media
  const snippets = createSnippets(image, audio);

  // Create the request payload
  const payload: any = {
    snippets: snippets,
    extra_parameters: {
      client_type: "clio",
      client_id: clientId,
      generate_video: generateVideo
    }
  };

  // Add optional strategy if provided
  if (strategy) {
    payload.extra_parameters.strategy = strategy;
  }

  return payload;
}

/**
 * Creates a story creation request payload for the v2 API
 */
export function createStoryRequestPayload(
  clientId: string,
  strategy: string | null = null,
  title: string | null = null,
  image: string | null = null,
  audio: string | null = null,
  generateVideo: boolean = false
) {
  // Create snippets from media
  const snippets = createSnippets(image, audio);

  // Create the request payload
  const payload: any = {
    client_id: clientId,
    snippets: snippets,
    extra_parameters: {
      client_type: "clio",
      generate_video: generateVideo
    }
  };

  // Add optional fields if provided
  if (strategy) {
    payload.strategy = strategy;
  }

  if (title) {
    payload.title = title;
  }

  return payload;
}
