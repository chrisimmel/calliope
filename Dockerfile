FROM python:3.11-buster
ENV APP_HOME /app
RUN mkdir $APP_HOME
RUN mkdir $APP_HOME/config
RUN mkdir $APP_HOME/input
RUN mkdir $APP_HOME/media
RUN mkdir $APP_HOME/state
WORKDIR $APP_HOME
RUN apt update -y
RUN apt upgrade -y
RUN apt install libgl1-mesa-glx -y
RUN apt remove ffmpeg -y
RUN apt install 'libsm6'\
    'libxext6'\
    'tzdata'  -y
COPY requirements requirements
RUN pip install -r requirements/development.txt
COPY . $APP_HOME
# Use a custom update script to install ffmpeg, because Debian is two major
# versions behind (4.x instead of the needed 6.x).
RUN bash $APP_HOME/scripts/update_ffmpeg.sh
ENV CLOUD_ENV $CLOUD_ENV
ENV OPENAI_API_KEY $OPENAI_API_KEY
ENV PINECONE_API_KEY $PINECONE_API_KEY
ENV PINECONE_ENVIRONMENT $PINECONE_ENVIRONMENT
ENV SEMANTIC_SEARCH_INDEX $SEMANTIC_SEARCH_INDEX
ENV POSTGRESQL_HOSTNAME $POSTGRESQL_HOSTNAME
ENV POSTGRESQL_DATABASE $POSTGRESQL_DATABASE
ENV POSTGRESQL_USERNAME $POSTGRESQL_USERNAME
ENV POSTGRESQL_PASSWORD $POSTGRESQL_PASSWORD
ENV PYTHONPATH "$APP_HOME:${PYTHONPATH}"
CMD exec uvicorn calliope.app:app --reload --host 0.0.0.0 --proxy-headers --port $PORT
