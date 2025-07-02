# Firebase Configuration

Calliope uses Firebase for real-time status updates between the server and clients. This document explains how to configure Firebase for both local development and production environments.

## Backend (Server) Configuration

The backend Firebase client requires proper configuration to connect to your Firebase project:

### Environment Variables

Add these environment variables to your Docker or local environment:

```
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
FIREBASE_DATABASE_ID=calliope-development  # or calliope-production
FIREBASE_CREDENTIALS_PATH=/path/to/credentials.json
```

For local Docker development, these are configured in `docker-compose.yml`:

```yaml
environment:
  - GOOGLE_CLOUD_PROJECT=your-gcp-project-id
  - FIREBASE_DATABASE_ID=calliope-development  # For multi-database setups
  - FIREBASE_CREDENTIALS_PATH=/gcp/config/application_default_credentials.json
```

#### Multi-Database Support

Firebase Firestore supports multiple databases within the same project. Calliope is configured to work with both single and multi-database setups:

- In a single database setup, you can omit the `FIREBASE_DATABASE_ID` environment variable
- In a multi-database setup, specify the database ID using the `FIREBASE_DATABASE_ID` environment variable
- If the specified database is not accessible, Calliope will fall back to the default database

### GCP Credentials

The backend will try to authenticate with Firebase using the following methods, in order:

1. In Google Cloud Run environments, it will use the default service account credentials
2. For local development, it will first try to use the credentials file specified in `FIREBASE_CREDENTIALS_PATH`
   - If this file is not in Firebase service account format, it will fall back to application default credentials
3. If no specific path is provided, it will use Google Application Default Credentials from the environment

#### Firebase Service Account vs GCP Application Default Credentials

There are two main types of credentials that can be used:

1. **Firebase Service Account Credentials**: A specific JSON file with Firebase permissions
   - Contains a `"type": "service_account"` field
   - Available in Firebase Console → Project Settings → Service Accounts → Generate New Private Key

2. **GCP Application Default Credentials**: Standard GCP credentials
   - Set up with `gcloud auth application-default login`
   - Works for most GCP services but may have limited Firebase permissions

For local development, you can use your application default credentials, but for production, it's recommended to set up specific Firebase service account credentials with appropriate permissions.

## Frontend (Clio) Configuration

The frontend Firebase client uses environment variables to securely store Firebase configuration:

### Setup Process

1. Copy the `.env.template` file to `.env` in the clio directory:
   ```
   cp clio/.env.template clio/.env
   ```

2. Fill in your Firebase Web SDK configuration values in the `.env` file. You can find these in your Firebase console under Project Settings > General > Your Apps > Web App.

3. **IMPORTANT**: Never commit the `.env` file to Git! It contains sensitive credentials.

### Required Environment Variables

```
FIREBASE_API_KEY=your-api-key
FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
FIREBASE_MESSAGING_SENDER_ID=your-sender-id
FIREBASE_APP_ID=your-app-id
FIREBASE_MEASUREMENT_ID=your-measurement-id
```

### Building the Frontend

When you build the Clio frontend with npm, the webpack configuration will automatically inject these environment variables into the application:

```
cd clio
npm run build
```

## Security Best Practices

1. **Never hardcode Firebase credentials** in your source code
2. Use different Firebase projects or database IDs for development and production
3. Configure Firebase Security Rules to restrict access appropriately
4. Regularly rotate API keys if they become compromised
5. Use the GCP console to monitor Firebase usage and detect unusual activity
