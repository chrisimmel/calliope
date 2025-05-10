# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Calliope is an experimental agentic framework that brings modern AI tools (generative AI, computer vision, and vector databases) to bear in creating interactive art works. The system is a flexible framework, service, and API that enables artists to build repeatable interaction strategies. The API can accept inputs such as images, text, and voice, then process these through an artist-defined pipeline of AI models to generate text and image output.

The project has three main components:
- **Calliope**: The backend server that processes inputs through AI models to generate outputs
- **Clio**: A TypeScript-based web client for interacting with Calliope
- **Thoth**: A back-office UI for browsing, monitoring and searching stories

## Development Environment Setup

### Setting up Calliope Backend

#### Local Development with Docker
```bash
# Build the Docker image
docker build -t calliope .

# Run the container
docker run --env PORT=8080 --publish 127.0.0.1:8080:8080/tcp calliope

# Alternative: Use docker-compose
docker-compose up
```

#### Accessing Postgres in Docker
```bash
# Access postgres container shell
docker-compose exec postgres /bin/bash

# From bash in the postgres container
psql -U postgres
```

### Database Migrations
```bash
# Access bash in the calliope container
docker-compose exec calliope /bin/bash

# From within bash in container
piccolo migrations new calliope --auto
piccolo migrations forwards calliope
piccolo user create
```

### Running Locally Without Docker
```bash
# Start the FastAPI server with hot reload
uvicorn calliope.app:app --reload --host 0.0.0.0 --port 8008
```

### Building Clio (Frontend)
```bash
# Build the client code
cd clio
npm run build
```
This generates a new version of `static/main.js` that must be committed to Git.

## Architecture

### Core Components

1. **Story Strategies**: Pluggable modules (called "storytellers" in Clio) that define how stories are generated and presented
2. **AI Models**: Integration with various providers (OpenAI, Anthropic, HuggingFace, Stability, Replicate, Runway, Azure)
3. **Image Analysis**: Uses multimodal LLMs and Azure computer vision API to interpret images and generate rich text descriptions
4. **Vector Database**: Semantic search using Pinecone for indexing generated media
5. **Configuration System**: Supports Sparrows (individual clients) and Flocks (groups of clients) with cascading configuration options

### Key Files and Components

- `calliope/app.py`: Main FastAPI application setup and configuration
- `calliope/routes/v1/story.py`: Story API endpoints for retrieving and creating frames
- `calliope/strategies/`: Different storytelling strategies
- `calliope/inference/`: Integration with AI model providers
- `clio/src/ClioApp.tsx`: Main React/TypeScript component for Clio web interface
- `client/story_loop.py`: Alternative client for Calliope that captures images and generates stories

## Database Structure

The project uses Piccolo ORM with PostgreSQL. Key tables include:
- `Story`: Stores story metadata
- `StoryFrame`: Individual frames within a story
- `Image`: Image data and metadata
- `StrategyConfig`: Configuration for different storytelling strategies
- `ModelConfig`: Configuration for AI models

## Common Development Tasks

### Adding a New Strategy

New story strategies should be placed in `calliope/strategies/` and registered in `calliope/strategies/registry.py`.

### Adding a New AI Model Provider

Integration with new AI providers should be added in `calliope/inference/engines/`.

### Testing

To test API endpoints:
- The API is available at http://localhost:8008 (or your configured port)
- Clio client at http://localhost:8008/clio/
- Admin interface at http://localhost:8008/admin/

### Environment Configuration

Calliope requires various API keys for the AI services it uses:
- OpenAI
- Pinecone 
- Azure Vision
- Other optional providers (Anthropic, HuggingFace, Stability, Replicate, Runway)

These can be configured via:
- Environment variables
- A `.env` file
- The configuration system for Sparrows and Flocks

Configuration variables in the docker-compose.yml file:
```
POSTGRESQL_HOSTNAME=postgres
POSTGRESQL_USERNAME=postgres
POSTGRESQL_PASSWORD=postgres
POSTGRESQL_DATABASE=calliope
OPENAI_API_KEY
PINECONE_API_KEY
PINECONE_ENVIRONMENT=us-west1-gcp-free
SEMANTIC_SEARCH_INDEX=story-semantic-search
```

## Code Conventions

- Python code is formatted with Black (line length 89)
- Import sorting with isort
- TypeScript for the Clio frontend