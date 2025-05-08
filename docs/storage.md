# Storage

Calliope uses a multi-tiered storage architecture to handle different types of data with appropriate persistence and access patterns.

## Database Storage

All persistent application data is stored in PostgreSQL, accessed through the [Piccolo ORM](https://piccolo-orm.com/). This includes:

- **Story Data**: Story metadata, text content, frame sequences
- **Configuration**: System settings, model configurations, inference parameters
- **Client Information**: Sparrow and Flock configurations, client state
- **User Management**: Admin user accounts, authentication data

### Database Schema

The main database tables include:

- `Story`: Core story metadata and properties
- `StoryFrame`: Individual frames within a story
- `Image`: Metadata about generated images
- `ModelConfig`: Configuration for inference models
- `InferenceModel`: Definition of AI models used by the system
- `SparrowState`: State tracking for individual clients
- `SparrowConfig`: Configuration for individual clients
- `FlockConfig`: Configuration for groups of clients

## Ephemeral File Storage

During request processing, Calliope uses the local file system for temporary storage of:

- **Input Images**: Images captured and uploaded from clients (webcam, etc.)
- **Input Audio**: Audio clips captured from clients for transcription
- **Generated Images**: Images created by the inference engines

In cloud environments (GCP), these files disappear whenever the serverless worker is deallocated. When running locally, these files remain in place, which is useful for debugging.

File paths typically follow these patterns:
- Input files: `input/{client_id}_{timestamp}_in.{ext}`
- Generated images: `media/{uuid}.{ext}`

## Persistent Media Storage

To ensure generated media remains accessible for story viewing, Calliope uses persistent storage for finalized media:

- In **Google Cloud**: Images are stored in Google Cloud Storage
  - Path format: `gs://{bucket-name}/media/{uuid}.{ext}`
  - Automatically synced when running in GCP environments
  
- In **Local Development**: Images remain in the local `media/` directory

### Media Storage Process

When a story frame is generated:

1. The image is initially created in the local filesystem
2. The image is processed (resized, format converted) as needed
3. If running in GCP, the image is uploaded to Cloud Storage
4. The image URL is stored in the database, referencing either the local path or Cloud Storage path

## Vector Database

For semantic search functionality, Calliope uses Pinecone to index and search story content:

- **Index Name**: Configured via `SEMANTIC_SEARCH_INDEX` (default: "story-semantic-search") 
- **Data Indexed**: Story text, image descriptions, and metadata
- **Embedding Model**: Vector embeddings are generated using OpenAI's models

## Storage Configuration

Storage configuration is managed through environment variables:

- **Database Connection**:
  ```
  POSTGRESQL_HOSTNAME=postgres
  POSTGRESQL_USERNAME=postgres
  POSTGRESQL_PASSWORD=postgres
  POSTGRESQL_DATABASE=calliope
  ```

- **Cloud Storage**:
  ```
  GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
  CLOUD_ENV=local|gcp
  ```

- **Vector Search**:
  ```
  PINECONE_API_KEY=your_pinecone_key
  PINECONE_ENVIRONMENT=us-west1-gcp-free
  SEMANTIC_SEARCH_INDEX=story-semantic-search
  ```

## Storage Management

### Migrations

Database schema changes are managed through Piccolo migrations:

```bash
# Generate a new migration
piccolo migrations new calliope --auto

# Apply pending migrations
piccolo migrations forwards calliope
```

### Media Cleanup

Currently, there is no automatic cleanup of media files. For production deployments, consider implementing a cleanup policy for older media files to manage storage costs.

### Backups

For production deployments, regular database backups are recommended:

- PostgreSQL database can be backed up using standard tools like `pg_dump`
- GCS media files can be backed up using GCS transfer services
