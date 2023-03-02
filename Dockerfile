FROM python:3.10.2-buster
ENV APP_HOME /app
RUN mkdir $APP_HOME
RUN mkdir $APP_HOME/config
RUN mkdir $APP_HOME/input
RUN mkdir $APP_HOME/media
RUN mkdir $APP_HOME/state
WORKDIR $APP_HOME
RUN apt-get update -y
RUN apt install libgl1-mesa-glx -y
RUN apt-get install 'ffmpeg'\
    'libsm6'\
    'libxext6'  -y
COPY requirements requirements
RUN pip install -r requirements/development.txt
COPY . /app
ENV PYTHONPATH "$APP_HOME:${PYTHONPATH}"
ENV POSTGRESQL_HOSTNAME $POSTGRESQL_HOSTNAME
ENV POSTGRESQL_DATABASE $POSTGRESQL_DATABASE
ENV POSTGRESQL_USERNAME $POSTGRESQL_USERNAME
ENV POSTGRESQL_PASSWORD $POSTGRESQL_PASSWORD
CMD exec uvicorn app:app --reload --host 0.0.0.0 --port $PORT
