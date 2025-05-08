# Running Calliope

Calliope can be run locally from the command line, in a local Docker container, or in Google Cloud.

## Local Development Setup

### Prerequisites
- Python 3.11 or later
- Poetry (recommended) or pip for dependency management
- FFmpeg for audio processing
- PostgreSQL database

### Environment Variables
Create a `.env` file with the following variables:
```
POSTGRESQL_HOSTNAME=localhost
POSTGRESQL_USERNAME=postgres
POSTGRESQL_PASSWORD=postgres
POSTGRESQL_DATABASE=calliope
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
AZURE_API_KEY=your_azure_api_key
HUGGINGFACE_API_KEY=your_huggingface_api_key
REPLICATE_API_TOKEN=your_replicate_token
CALLIOPE_API_KEY=your_chosen_api_key
```

### Running with Docker Compose (Recommended)
The easiest way to run Calliope locally is with Docker Compose, which sets up both the PostgreSQL database and the Calliope server:

```bash
docker-compose up
```

This will make the Calliope service available at http://localhost:8008.

### Running Standalone Server
To start a local Calliope server without Docker:

1. Make sure PostgreSQL is running and accessible with the credentials in your `.env` file
2. Run the FastAPI server:
```bash
uvicorn calliope.app:app --reload --host 0.0.0.0 --port 8008
```

## Accessing the Applications

### Calliope API
The API will be available at:
- http://localhost:8008 (local development)
- https://your-cloud-url (when deployed to Google Cloud)

The API documentation is available at:
- http://localhost:8008/docs (local development)
- https://your-cloud-url/docs (when deployed)

### Clio Client
Clio is a Calliope client that can be run in a Web browser, located at:
- http://localhost:8008/clio/ (local development)
- https://your-cloud-url/clio/ (when deployed)

It will ask to use your Web cam. If you allow it, Clio will use still images from the camera to help feed the Calliope story strategies. It shows images and text from the story.

### Thoth Admin Interface
The Thoth interface for browsing and searching stories is available at:
- http://localhost:8008/thoth/ (local development)
- https://your-cloud-url/thoth/ (when deployed)

### Calliope Admin
The admin interface for managing the Calliope configuration is available at:
- http://localhost:8008/admin/ (local development)
- https://your-cloud-url/admin/ (when deployed)

## Setting Up Initial Data

After the first run, you'll need to create an admin user and set up initial configuration:

```bash
# Get a shell in the container
docker-compose exec calliope /bin/bash

# Create an admin user
piccolo user create

# Run any pending migrations
piccolo migrations forwards calliope
```

## Development Workflow

1. Start the server with the `--reload` flag as shown above
2. Make changes to the code - the server will automatically reload
3. Test your changes via the API or one of the web interfaces
4. Run migrations if you've changed the database models:
   ```bash
   piccolo migrations new calliope --auto
   piccolo migrations forwards calliope
   ```

## Logs and Debugging

When running with Docker Compose, view logs with:
```bash
docker-compose logs -f calliope
```

For standalone operation, logs will be displayed in the terminal where you started the uvicorn server.