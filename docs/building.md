
# Locally, with Docker
```
docker build -t calliope .
docker run --env PORT=8080 --publish 127.0.0.1:8080:8080/tcp calliope
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


# Generating and Executing Migrations
To get to bash in calliope container:
```
docker-compose exec calliope /bin/bash
```

From within bash in container:
```
piccolo migrations new calliope --auto
piccolo migrations forwards calliope
# python calliope/storage/config_manager.py
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
