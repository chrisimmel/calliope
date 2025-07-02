
# Development Setup

## Prerequisites

Install [uv](https://docs.astral.sh/uv/getting-started/installation/):
```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or using brew on macOS
brew install uv
```

## Local Development

Clone the repository and set up the environment:
```bash
git clone <repository-url>
cd calliope

# Install dependencies and create virtual environment
uv sync --dev

# Run the development server
uv run uvicorn calliope.app:app --reload --host 0.0.0.0 --port 8008
```

## Using Docker

```bash
docker build -t calliope .
docker run --env PORT=8080 --publish 127.0.0.1:8080:8080/tcp calliope
```

Or use docker-compose:
```bash
docker-compose up
```

# In the Cloud

Calliope is for now slightly coupled with GCP as a cloud provider just because that's
where I originally deployed it. However, it depends on very little in its cloud environment.
I believe that making it cloud agnostic would be just a matter of generalizing a few places
it explicitly uses Google Cloud Storage to alternately use s3 if in AWS or Azure Cloud
Storage if on Azure.

## Building and Deploying to Google Cloud

Do this once:
```
gcloud auth application-default login
gcloud config set project ardent-course-370411
```

Then do this for each build/deploy:
```
gcloud builds submit --tag <your project tag>
gcloud run deploy --image <your project tag> --platform managed
```


# Database Management

## Generating and Executing Migrations

Using uv locally:
```bash
# Generate new migration
uv run piccolo migrations new calliope --auto

# Apply migrations
uv run piccolo migrations forwards calliope

# Create admin user
uv run piccolo user create
```

Using Docker:
```bash
# Get bash in calliope container
docker-compose exec calliope /bin/bash

# From within container
piccolo migrations new calliope --auto
piccolo migrations forwards calliope
piccolo user create
```

Postgres
To get to bash in the postgres container:
```
docker-compose exec postgres /bin/bash
```

From bash in the postgres container:
```
psql -U postgres
```

From psql:
```
\dt
etc.
```



# Clio

To build:
```
cd clio
npm run build
```
This generates a new version of `static/main.js` that must be committed to Git. Also, to be
included in the cloud distribution, a new Google Cloud build must also be executed (see above).

Then it will be served at <calliope-host>/clio/
