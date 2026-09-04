FROM python:3.11-bookworm

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV APP_HOME /app
RUN mkdir $APP_HOME
RUN mkdir $APP_HOME/config
RUN mkdir $APP_HOME/input
RUN mkdir $APP_HOME/media
RUN mkdir $APP_HOME/state
WORKDIR $APP_HOME

# Install system dependencies
RUN apt update -y && apt upgrade -y
RUN apt install -y \
    jq \
    curl \
    ffmpeg \
    tzdata

# Copy dependency files first for better Docker layer caching
COPY pyproject.toml uv.lock ./

# Install Python dependencies with uv
RUN uv sync --frozen --no-dev

# Copy application code
COPY calliope ./calliope
COPY . .

# Environment variables
ENV CLOUD_ENV=$CLOUD_ENV
ENV OPENAI_API_KEY=$OPENAI_API_KEY
ENV PINECONE_API_KEY=$PINECONE_API_KEY
ENV PINECONE_ENVIRONMENT=$PINECONE_ENVIRONMENT
ENV SEMANTIC_SEARCH_INDEX=$SEMANTIC_SEARCH_INDEX
ENV POSTGRESQL_HOSTNAME=$POSTGRESQL_HOSTNAME
ENV POSTGRESQL_DATABASE=$POSTGRESQL_DATABASE
ENV POSTGRESQL_USERNAME=$POSTGRESQL_USERNAME
ENV POSTGRESQL_PASSWORD=$POSTGRESQL_PASSWORD
ENV PYTHONPATH="$APP_HOME:${PYTHONPATH}"

# Add virtual environment to PATH so Python can find installed packages
ENV PATH="$APP_HOME/.venv/bin:$PATH"

# Use uv to run the application (removed --reload for production)
# --forwarded-allow-ips="*" is required in addition to --proxy-headers: without
# it uvicorn only trusts X-Forwarded-* from 127.0.0.1, so behind Cloud Run's
# TLS-terminating proxy it ignores X-Forwarded-Proto and treats requests as
# http. That made generated redirects (e.g. trailing-slash 307s) use http://,
# which browsers block as mixed content on the https page. Trusting "*" is safe
# here because only the Cloud Run front end can reach the container.
CMD ["uv", "run", "--", "uvicorn", "calliope.app:app", "--host", "0.0.0.0", "--proxy-headers", "--forwarded-allow-ips", "*", "--port", "8080"]
