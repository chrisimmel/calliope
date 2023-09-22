# Storage

Calliope uses three classes of storage:
* All configuration, client, user management, and story data is stored in PostgreSQL, accessed through the [Piccolo ORM](https://piccolo-orm.com/).
* During request processing, input and output images are stored ephemerally on the server file system. In GCP, these disappear anytime the serverless worker is deallocated. When running locally, it's useful that these remain in place to help with debugging.
* Just before a story frame is delivered in an API response, the output image is stored persistently to Google Cloud Storage (when running in GCP). This ensures that we can still see the generated images later when reviewing a story in Thoth or Clio.
