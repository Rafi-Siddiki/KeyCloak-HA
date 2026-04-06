# Flask App — Keycloak Integration Setup

> Connect your Flask application to a Keycloak server for secure authentication.

---

## Prerequisites

- Keycloak Admin Console is running
- Flask project is cloned locally

---

## Step 1 — Create a Realm

1. Open your **Keycloak Admin Console**
2. Hover over the realm selector (top-left) → click **Create Realm**
3. Set the Realm name to:
   ```
   electronic-shop
   ```
4. Click **Create**

---

## Step 2 — Create a Client

1. Go to **Clients** in the left sidebar
2. Click **Create client**
3. Set the Client ID to:
   ```
   flask-app
   ```
4. Click **Next**

---

## Step 3 — Configure Capabilities

In the **Capability config** tab:

| Setting | Value |
|---|---|
| Client authentication | ✅ On |
| Direct access grants | ✅ Checked |

Click **Save**

---

## Step 4 — Get the Client Secret

1. Go to the **Credentials** tab (now visible after enabling Client authentication)
2. Copy the value from the **Client secret** field

---

## Step 5 — Update Your `.env` File

Open `.env` in your Flask project root and paste your secret:

```env
KEYCLOAK_CLIENT_SECRET=your_copied_secret_here
```

---

## Step 6 — Run the Application

Choose one of the two methods below:

### Option A — Run from Source Code

```bash
# Navigate to the source directory
cd KeyCloak-HA/flask-app/Code\ Base

# Run the app
python app.py
```

### Option B — Run with Docker Compose

```bash
# Clone and navigate to the project
cd KeyCloak-HA/flask-app

# Copy the example env file
cp .env.example .env

# Edit the env file and paste your secret
nano .env

# Start the container
docker compose up -d
```

> **Alternative:** Pull and run the pre-built image directly:
> ```bash
> docker run -p 5000:5000 --name my-app-container --env-file .env rafisiddiki/flask-app:1.0.0
> ```

---

## Quick Summary

```
Keycloak Admin
  └── Create Realm: electronic-shop
        └── Create Client: flask-app
              └── Enable Client Authentication
                    └── Copy Client Secret
                          └── Paste into .env → Run the app
```
