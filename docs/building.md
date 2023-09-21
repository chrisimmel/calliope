
# With Docker
```
docker build -t calliope .
docker run --env PORT=8080 --publish 127.0.0.1:8080:8080/tcp calliope
```

# Building and Deploying to Google Cloud

```
gcloud auth application-default login
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
To get to bash in postgres container:
```
docker-compose exec postgres /bin/bash
```

From bash in postgres container:
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

