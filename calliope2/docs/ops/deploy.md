# Deploy playbook (production)

How to deploy `calliope2` to its production Cloud Run service. The legacy
`/calliope/` app runs as a **separate** service (`calliope`) and is never
touched by this process.

## The service

|         |                                                                                                                                                                                           |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Service | `calliope-v3`                                                                                                                                                                             |
| Project | `ardent-course-370411`                                                                                                                                                                    |
| Region  | `us-central1`                                                                                                                                                                             |
| URL     | https://calliope-v3-59295831264.us-central1.run.app                                                                                                                                       |
| Image   | `us-central1-docker.pkg.dev/ardent-course-370411/cloud-run-source-deploy/calliope-v3:firebase`                                                                                            |
| Build   | Cloud Build from [`calliope2/Dockerfile`](../../Dockerfile) via [`calliope2/cloudbuild.yaml`](../../cloudbuild.yaml) (multi-stage: builds the Clio + Admin SPAs, then the Python runtime) |

## Prerequisites

```bash
gcloud auth login
gcloud config set project ardent-course-370411
gcloud config set run/region us-central1
```

Deploy from the **`calliope2/` directory** — the Dockerfile's `COPY` paths and
the build context are relative to it. Local Docker is not required; the build
runs in Cloud Build.

## Config model — build-time vs runtime

- **Build-time (Firebase _web_ config).** The Clio SPA bakes the Firebase
  browser config in at webpack build time, so it must reach the Docker build as
  **`--build-arg`s** (the Dockerfile declares them as `ARG`s). These are _not
  secret_ (they ship in every browser bundle), but a build **without** them
  produces a bundle with sign-in disabled.

  > Important: Cloud Run's `gcloud run deploy --source --build-env-vars` does
  > **not** pass these to a Dockerfile build — the bundle ships config-less.
  > Use `cloudbuild.yaml` (below), which forwards them as `--build-arg`s.

- **Runtime (secrets + settings).** DB URL, OpenAI / Replicate keys, GCS bucket,
  Firebase project/database for the backend. These are Cloud Run env vars +
  Secret Manager refs **already attached to the service**; `gcloud run deploy`
  preserves them across deploys — do not re-specify them.

The Firebase web config values are mirrored on the service for reference:

```bash
gcloud run services describe calliope-v3 --region us-central1 \
  --format='value(metadata.annotations."run.googleapis.com/build-environment-variables")'
```

Keys: `FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`, `FIREBASE_PROJECT_ID`,
`FIREBASE_STORAGE_BUCKET`, `FIREBASE_MESSAGING_SENDER_ID`, `FIREBASE_APP_ID`,
`FIREBASE_MEASUREMENT_ID`, `FIREBASE_DATABASE_ID`. `FIREBASE_DATABASE_ID` must
match the backend's `CALLIOPE2_FIREBASE_DATABASE_ID` (`calliope2-production`) or
realtime status updates won't reach the client.

## Deploy

Two steps: build the image (with Firebase args baked), then roll the revision.

```bash
cd calliope2

# 1. Build + push the image (~14 min). Fill in the Firebase web config values.
gcloud builds submit --config cloudbuild.yaml --project ardent-course-370411 \
  --substitutions=\
_FIREBASE_API_KEY=...,\
_FIREBASE_AUTH_DOMAIN=ardent-course-370411.firebaseapp.com,\
_FIREBASE_PROJECT_ID=ardent-course-370411,\
_FIREBASE_STORAGE_BUCKET=ardent-course-370411.firebasestorage.app,\
_FIREBASE_MESSAGING_SENDER_ID=59295831264,\
_FIREBASE_APP_ID=...,\
_FIREBASE_MEASUREMENT_ID=...,\
_FIREBASE_DATABASE_ID=calliope2-production

# 2. Deploy the freshly built image (runtime env/secrets are preserved).
gcloud run deploy calliope-v3 \
  --image us-central1-docker.pkg.dev/ardent-course-370411/cloud-run-source-deploy/calliope-v3:firebase \
  --region us-central1 --project ardent-course-370411 --quiet
```

Deploying an **unmerged branch** is acceptable for this project today (single v3
user; prod is the test environment until a change is proven). Check out the
branch and run the steps from its `calliope2/`.

## Verify

```bash
URL=https://calliope-v3-59295831264.us-central1.run.app
curl -s $URL/v3/health                                   # → {"status":"ok",...}
curl -s -o /dev/null -w '%{http_code}\n' $URL/clio/      # → 200
# Confirm the Firebase config actually baked into the bundle:
MAIN=$(curl -s $URL/clio/ | grep -oE 'main\.js\?[a-z0-9]+')
curl -s "$URL/clio/$MAIN" | grep -oE 'firebaseapp\.com' | head -1   # → firebaseapp.com
```

Then open `$URL/clio/`, sign in with Google, and confirm a story loads and that
new-frame generation status clears (realtime).

## Rollback

```bash
gcloud run revisions list --service calliope-v3 --region us-central1
gcloud run services update-traffic calliope-v3 --region us-central1 \
  --to-revisions <GOOD_REVISION>=100
```

## Notes

- No CI/CD trigger yet; deploys are manual. A Cloud Build trigger on `main`
  (substitutions carrying the Firebase config) would automate this once the
  prod-test-then-merge flow tightens up.
