# Deploy playbook (production)

How to deploy `calliope2` to its production Cloud Run service. The legacy
`/calliope/` app runs as a **separate** service (`calliope`) and is never
touched by this process.

## The service

|            |                                                                                                                                                        |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Service    | `calliope-v3`                                                                                                                                          |
| Project    | `ardent-course-370411`                                                                                                                                 |
| Region     | `us-central1`                                                                                                                                          |
| URL        | https://calliope-v3-59295831264.us-central1.run.app                                                                                                    |
| Image repo | `us-central1-docker.pkg.dev/ardent-course-370411/cloud-run-source-deploy/calliope-v3`                                                                  |
| Build      | Cloud Run integrated Cloud Build, from [`calliope2/Dockerfile`](../../Dockerfile) (multi-stage: builds the Clio + Admin SPAs, then the Python runtime) |

## Prerequisites

- `gcloud` authenticated as a principal with deploy rights, and docker is **not**
  required (the build runs in Cloud Build, not locally):
  ```bash
  gcloud auth login
  gcloud config set project ardent-course-370411
  gcloud config set run/region us-central1
  ```
- Deploy from the **`calliope2/` directory** — the Dockerfile's `COPY` paths are
  relative to it (`apps/web/clio`, `apps/api`, `apps/cli`, `pyproject.toml`,
  `uv.lock`). `--source .` must be run from there.

## Config model — build-time vs runtime

Two distinct sets of configuration:

- **Build-time (Firebase _web_ config).** The Clio SPA bakes the Firebase
  browser config in at webpack build time, so it must be passed as **build env
  vars**. These are _not secret_ (they ship in every browser bundle), but a
  build **without** them produces a sign-in-broken bundle. They are stored on
  the service and passed via `--build-env-vars-file`.
- **Runtime (secrets + settings).** DB URL, OpenAI / Replicate keys, GCS bucket,
  Firebase project/database for the backend. These live as Cloud Run env vars +
  Secret Manager refs **already attached to the service** and are preserved
  across deploys — you do not re-specify them.

Recover the current build env vars from the running service into the file the
deploy expects:

```bash
gcloud run services describe calliope-v3 --region us-central1 \
  --format='value(metadata.annotations."run.googleapis.com/build-environment-variables")' \
| python3 -c 'import json,sys,yaml; yaml.safe_dump(json.load(sys.stdin), sys.stdout)' \
> /tmp/firebase-build-env.yaml
```

The keys (current values): `FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`,
`FIREBASE_PROJECT_ID`, `FIREBASE_STORAGE_BUCKET`, `FIREBASE_MESSAGING_SENDER_ID`,
`FIREBASE_APP_ID`, `FIREBASE_MEASUREMENT_ID`, `FIREBASE_DATABASE_ID`.

> Note: `--build-env-vars-file` **replaces** the build env set, so the file must
> contain _all_ of them.

## Deploy

```bash
cd calliope2
gcloud run deploy calliope-v3 \
  --source . \
  --region us-central1 \
  --project ardent-course-370411 \
  --build-env-vars-file /tmp/firebase-build-env.yaml \
  --quiet
```

- `--source .` rebuilds the image in Cloud Build (~14 min) and rolls a new
  revision. Unspecified runtime flags (env vars, secrets, service account,
  scaling) are inherited from the current revision.
- Deploying an **unmerged branch** is acceptable for this project today (single
  v3 user; prod is the test environment until a change is proven). Check out the
  branch locally and deploy from its `calliope2/`.

## Verify

```bash
URL=https://calliope-v3-59295831264.us-central1.run.app
curl -s $URL/v3/health                       # → {"status":"ok","version":"..."}
curl -s -o /dev/null -w '%{http_code}\n' $URL/clio/   # → 200 (SPA shell)
# Confirm the new revision is serving 100% traffic:
gcloud run services describe calliope-v3 --region us-central1 \
  --format='value(status.traffic)'
```

Then open `$URL/clio/` in a browser, sign in with Google, and confirm a story
loads.

## Rollback

```bash
# List revisions (newest first):
gcloud run revisions list --service calliope-v3 --region us-central1
# Send all traffic back to a known-good revision:
gcloud run services update-traffic calliope-v3 --region us-central1 \
  --to-revisions <GOOD_REVISION>=100
```

## Known follow-ups

- **Firestore database mismatch (realtime status):** the client build uses
  `FIREBASE_DATABASE_ID=calliope-production` while the backend writes task docs
  to `CALLIOPE2_FIREBASE_DATABASE_ID=calliope2-production`. If realtime
  frame-arrival/“generating…” updates don't fire, align these (most likely set
  the client build's `FIREBASE_DATABASE_ID` to `calliope2-production`). Left
  as-is here to keep the deploy faithful to the previous revision.
- No CI/CD or Cloud Build trigger exists yet; deploys are manual. A trigger on
  `main` (with the build env vars stored on it) would automate this once the
  prod-test-then-merge flow tightens up.
