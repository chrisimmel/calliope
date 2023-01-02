
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


# Clio

To build:
```
cd clio
npm run build
```
This generates a new version of `static/main.js` that must be committed to Git. Also, to be
included in the cloud distribution, a new Google Cloud build must also be executed (see above).

Then it will be served at <calliope-host>/clio/

