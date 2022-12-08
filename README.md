# Calliope

![Calliope](https://user-images.githubusercontent.com/17924059/204841825-e21a5387-4348-4b0c-9b8e-bce636e6eb0d.jpg)

# Running Calliope

Client/server:

Start the server (in one terminal):
```
uvicorn app:app --reload
```

Start the client (in another terminal):
```
python -m client.main
```

Altogether:
```
python -m client.story_loop
```


# With Docker
```
docker build -t calliope .
docker run --env PORT=8080 --publish 127.0.0.1:8080:8080/tcp calliope
```

# Building and Deploying to Google Cloud

```
gcloud auth application-default login
gcloud builds submit --tag gcr.io/ardent-course-370411/calliope
gcloud run deploy --image gcr.io/ardent-course-370411/calliope --platform managed
```