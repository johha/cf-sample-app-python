# CF Sample App Python

A simple Python Flask application that demonstrates Cloud Foundry service binding capabilities and environment inspection.

## Purpose

This application serves as a testing and demonstration tool for Cloud Foundry deployments. It displays:

- **Application metadata** - CF API endpoint, app name, URIs, instance details, memory/disk limits, space and organization information
- **Service bindings** - Services bound via `VCAP_SERVICES` environment variable
- **File-based VCAP services** - Services loaded from file-based VCAP configuration
- **Kubernetes service bindings** - Services mounted in Kubernetes environments

The app automatically redacts sensitive information (passwords, secrets, API keys) when displaying service credentials, making it safe for demos and troubleshooting.

## Endpoints

- `/` - Main dashboard showing all application and service information
- `/health` - Health check endpoint
- `/bindings.json` - JSON API for service bindings (add `?reveal=1` to show unredacted data)

## Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python app.py
   ```

3. Access the app at `http://localhost:8080`

## Deploying to Cloud Foundry

1. **Prerequisites**: Ensure you have the CF CLI installed and are logged into your Cloud Foundry environment.

2. **Push the application**:
   ```bash
   cf push
   ```

   The app uses the configuration in `manifest.yml`:
   - App name: `cf-test-app`
   - Memory: 128M
   - Instances: 1
   - Random route enabled
   - Python buildpack

3. **Bind services** (optional):
   ```bash
   cf bind-service cf-test-app your-service-name
   cf restage cf-test-app
   ```

4. **Access your app**:
   ```bash
   cf apps
   ```
   Then visit the URL shown for your application.

## Customization

- Modify `manifest.yml` to change app name, memory, or other deployment settings
- Update the sensitive keys list in `app.py` if you need to redact additional credential fields
- Customize the UI by editing `templates/index.html` and `static/style.css`

## File Structure

```
├── app.py              # Main Flask application
├── manifest.yml        # Cloud Foundry deployment manifest
├── Procfile           # Process file for CF deployment
├── requirements.txt   # Python dependencies
├── static/
│   └── style.css      # Application styles
└── templates/
    └── index.html     # Main template
```
