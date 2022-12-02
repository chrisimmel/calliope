FROM python:3.10.2-buster
ENV APP_HOME /app
RUN mkdir $APP_HOME
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
CMD exec uvicorn app:app --reload --host 0.0.0.0 --port 8000
