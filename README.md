# Keycloak HA Deployment

A structured, multi-VM Keycloak high-availability deployment using Docker Compose, PostgreSQL, and NGINX.

---

## Table of Contents

- [Overview](#overview)
- [Why High Availability for Keycloak?](#why-high-availability-for-keycloak)
- [Current Limitation](#current-limitation)
- [Architecture Overview](#architecture-overview)
- [Architecture Diagram](#architecture-diagram)
- [Repository Layout](#repository-layout)
- [Technology Stack](#technology-stack)
- [How the Cluster Works](#how-the-cluster-works)
- [NGINX Note](#nginx-note)
- [Prerequisites](#prerequisites)
- [/etc/hosts Configuration](#etchosts-configuration)
- [Deployment Steps](#deployment-steps)
  - [1. PostgreSQL VM](#1-postgresql-vm)
  - [2. Keycloak Node 1 VM](#2-keycloak-node-1-vm)
  - [3. Keycloak Node 2 VM](#3-keycloak-node-2-vm)
  - [4. NGINX VM](#4-nginx-vm)
  - [5. Flask Application Setup](#5-flask-application-setup)
- [Run Flask App as a Background Service](#run-flask-app-as-a-background-service)
- [Verification](#verification)
  - [PostgreSQL](#postgresql-verification)
  - [Keycloak Nodes](#keycloak-nodes-verification)
  - [NGINX](#nginx-verification)
  - [Flask Application](#flask-application-verification)
  - [Cluster Membership Check](#cluster-membership-check)
- [Summary](#summary)

---

## Overview

This repository provides a **high-availability Keycloak deployment** by running **two Keycloak nodes in a cluster** behind an **NGINX load balancer**, with **PostgreSQL** as the shared backend database.

The cluster uses:

- **Infinispan**
- **JGroups**
- **`jdbc-ping`** for node discovery
- **sticky sessions** through NGINX

This setup improves Keycloak service availability compared to a single-node deployment.

---

## Why High Availability for Keycloak?

In a single-node Keycloak setup, the authentication tier is **not fault tolerant**. If that one Keycloak instance goes down due to:

- service crash
- VM failure
- maintenance
- network issue

then authentication requests can no longer be served.

This repository improves that design by deploying:

- **2 Keycloak nodes**
- **shared PostgreSQL database**
- **cluster discovery via `jdbc-ping`**
- **load balancing via NGINX**

According to the current Keycloak clustering model, when Keycloak runs in production mode, distributed caching is enabled and nodes can use the **`jdbc-ping` stack** to discover each other through the configured database.

---

## Current Limitation

> This repository improves **Keycloak-tier availability only**. It is **not yet full end-to-end fault tolerant**.

The following components are still **single points of failure**:

- **NGINX VM**
- **PostgreSQL VM**

That means:

- Keycloak becomes redundant
- but NGINX and PostgreSQL still remain non-HA unless they are also redesigned for high availability

---

## Architecture Overview

This deployment uses a **4-VM architecture**:

| VM | Role | Hostname |
|---|---|---|
| VM1 | NGINX Load Balancer | `auth.lb.xyz` |
| VM2 | Keycloak Node 1 | `kc-node1.xyz` |
| VM3 | Keycloak Node 2 | `kc-node2.xyz` |
| VM4 | PostgreSQL | `postgres.db.xyz` |

### Request Flow

```text
User → Flask App → NGINX Load Balancer → Keycloak Cluster → PostgreSQL
```

The response returns back through the same path after successful authentication.

---

## Architecture Diagram

![Keycloak HA Architecture](diagram.png)

The architecture works as follows:

- The **Flask application** sends authentication requests to the **NGINX reverse proxy**
- **NGINX** forwards requests to one of the two **Keycloak nodes**
- The two **Keycloak nodes** synchronize cluster state through **Infinispan/JGroups**
- Both Keycloak nodes use the same **PostgreSQL database** for persistence

---

## Repository Layout

```text
KeyCloak-HA/
├── postgres/
│   ├── docker-compose.yml
│   └── .env
├── keycloak-node1/
│   ├── docker-compose.yml
│   └── .env
├── keycloak-node2/
│   ├── docker-compose.yml
│   └── .env
├── nginx/
│   ├── docker-compose.yml
│   ├── .env
│   └── default.conf.template
├── flask-app/
│   ├── docker-compose.yml
│   ├── .env
│   ├── app.py
│   ├── requirements.txt
│   └── flask-app.service
├── .gitignore
└── README.md
```

---

## Technology Stack

- Keycloak `26.1.0`
- PostgreSQL `16`
- Docker Engine
- Docker Compose v2
- NGINX reverse proxy / load balancer
- Infinispan + JGroups clustering
- `jdbc-ping` for Keycloak node discovery
- Sticky sessions using `AUTH_SESSION_ID`
- `systemd` for running the Flask app as a background service

---

## How the Cluster Works

Each Keycloak node runs in its own container on its own VM, but both nodes:

- connect to the same PostgreSQL database
- use distributed caching
- participate in the same Keycloak cluster

### Important environment behavior

- `KC_CACHE=ispn` enables **Infinispan**
- `KC_CACHE_STACK=jdbc-ping` allows nodes to discover each other using the **shared database**
- `JAVA_OPTS_APPEND` binds JGroups traffic to the **real VM IP** of each Keycloak node

### Load balancing behavior

NGINX sits in front of both Keycloak nodes and forwards authentication traffic to them using **sticky sessions**, so a user remains associated with the same backend node when possible.

---

## NGINX Note

The original deployment design uses **native NGINX installed directly on VM1**.

This repository instead packages NGINX with **Docker Compose** for easier deployment and version control, while keeping the same functional behavior:

- listens on port `80`
- forwards traffic to:
  - `10.9.0.72:8080`
  - `10.9.0.73:8080`
- passes required `X-Forwarded-*` headers
- uses sticky-session behavior based on Keycloak’s `AUTH_SESSION_ID` cookie

If you want to match the original design exactly, you can install NGINX natively and reuse the provided configuration as a template.

---

## Prerequisites

Prepare the Ubuntu VMs with:

- Ubuntu `20.04` or `22.04` LTS
- Docker Engine
- Docker Compose v2

### Install base packages

```bash
sudo apt update
```

```bash
sudo apt install -y docker.io docker-compose-v2
```

```bash
sudo systemctl enable --now docker
```

---

## `/etc/hosts` Configuration

Edit the `/etc/hosts` file on **each VM** and add:

```text
10.9.0.74  postgres.db.xyz
10.9.0.71  auth.lb.xyz
10.9.0.72  kc-node1.xyz
10.9.0.73  kc-node2.xyz
```

This allows each VM to resolve the others using consistent internal hostnames.

---

## Deployment Steps

Clone the same repository on every VM, but only run the service directory that belongs to that VM.

---

## 1. PostgreSQL VM

**VM:** `10.9.0.74`  
**Hostname:** `postgres.db.xyz`

```bash
git clone https://github.com/Rafi-Siddiki/KeyCloak-HA.git
```

```bash
cd KeyCloak-HA/postgres
```

```bash
docker compose up -d
```

---

## 2. Keycloak Node 1 VM

**VM:** `10.9.0.72`  
**Hostname:** `kc-node1.xyz`

```bash
git clone https://github.com/Rafi-Siddiki/KeyCloak-HA.git
```

```bash
cd KeyCloak-HA/keycloak-node1
```

```bash
docker compose up -d
```

---

## 3. Keycloak Node 2 VM

**VM:** `10.9.0.73`  
**Hostname:** `kc-node2.xyz`

```bash
git clone https://github.com/Rafi-Siddiki/KeyCloak-HA.git
```

```bash
cd KeyCloak-HA/keycloak-node2
```

```bash
docker compose up -d
```

---

## 4. NGINX VM

**VM:** `10.9.0.71`  
**Hostname:** `auth.lb.xyz`

```bash
git clone https://github.com/Rafi-Siddiki/KeyCloak-HA.git
```

```bash
cd KeyCloak-HA/nginx
```

```bash
docker compose up -d
```

---

## 5. Flask Application Setup

The Flask application needs a properly configured Keycloak realm and client before it can authenticate users.

### Phase 1: Create Realm

1. Open the **Keycloak Admin Console**
2. Hover over the realm selector in the top-left corner
3. Click **Create Realm**
4. Set the realm name to:

```text
electronic-shop
```

#### Image placeholder

```md
![Create Realm Screenshot](images/flask-app/create-realm.png)
```

---

### Phase 2: Create Client

1. Go to **Clients**
2. Click **Create client**
3. Set the **Client ID** to:

```text
flask-app
```

4. Click **Next**

#### Image placeholder

```md
![Create Client Screenshot](images/flask-app/create-client.png)
```

---

### Phase 3: Configure Client Capabilities

To allow the Flask app to work as a secure backend client:

#### Enable Client Authentication

In the **Capability config** tab for `flask-app`:

- turn **Client authentication** = `On`

#### Configure Access Grants

Under **Authentication flow**:

- ensure **Direct access grants** is enabled

#### Save Changes

- click **Save**

#### Image placeholder

```md
![Client Capability Configuration](images/flask-app/client-capabilities.png)
```

---

### Phase 4: Retrieve Client Secret

Once client authentication is enabled, Keycloak generates a secret for the client.

#### Steps

1. Open the **Credentials** tab
2. Locate **Client secret**
3. Copy the generated secret

#### Image placeholder

```md
![Client Secret Screenshot](images/flask-app/client-secret.png)
```

---

### Phase 5: Update Flask Environment File

Open the Flask app `.env` file and set:

```bash
KEYCLOAK_CLIENT_SECRET=your_copied_secret_here
```

#### Image placeholder

```md
![Flask Env Update Screenshot](images/flask-app/update-env.png)
```

---

## Run Flask App as a Background Service

This section replaces the earlier “run manually” approach and uses **systemd** so the Flask app runs in the background and restarts automatically.

### Recommended project structure for Flask VM

```text
/opt/flask-app/
├── app.py
├── requirements.txt
├── .env
└── venv/
```

### 1. Install required packages

```bash
sudo apt update
```

```bash
sudo apt install -y python3 python3-pip python3-venv
```

### 2. Create application directory

```bash
sudo mkdir -p /opt/flask-app
```

### 3. Copy application files

```bash
sudo cp -r KeyCloak-HA/flask-app/* /opt/flask-app/
```

### 4. Create Python virtual environment

```bash
cd /opt/flask-app
```

```bash
python3 -m venv venv
```

### 5. Install Python dependencies

```bash
source venv/bin/activate
```

```bash
pip install --upgrade pip
```

```bash
pip install -r requirements.txt
```

### 6. Create or edit the environment file

```bash
nano /opt/flask-app/.env
```

Example:

```bash
KEYCLOAK_CLIENT_SECRET=your_copied_secret_here
```

### 7. Create the systemd service file

```bash
sudo nano /etc/systemd/system/flask-app.service
```

Paste this into the file:

```ini
[Unit]
Description=Flask Application Service
After=network.target

[Service]
User=root
WorkingDirectory=/opt/flask-app
EnvironmentFile=/opt/flask-app/.env
ExecStart=/opt/flask-app/venv/bin/python /opt/flask-app/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 8. Reload systemd

```bash
sudo systemctl daemon-reload
```

### 9. Enable the service at boot

```bash
sudo systemctl enable flask-app
```

### 10. Start the service

```bash
sudo systemctl start flask-app
```

### 11. Check service status

```bash
sudo systemctl status flask-app
```

### 12. View service logs

```bash
sudo journalctl -u flask-app -f
```

#### Image placeholders for service setup

```md
![Create Flask Service File](images/flask-app/create-service-file.png)
```

```md
![Flask Service Status](images/flask-app/flask-service-status.png)
```

---

## Verification

After deployment, verify each component separately.

---

## PostgreSQL Verification

```bash
docker ps
```

```bash
docker logs postgres-keycloak --tail 50
```

---

## Keycloak Nodes Verification

```bash
docker ps
```

```bash
docker logs keycloak --tail 50
```

```bash
curl -I http://127.0.0.1:8080
```

---

## NGINX Verification

```bash
docker ps
```

```bash
docker logs nginx-keycloak-lb --tail 50
```

```bash
curl -I http://127.0.0.1
```

---

## Flask Application Verification

```bash
sudo systemctl status flask-app
```

```bash
sudo journalctl -u flask-app -n 50
```

```bash
curl http://127.0.0.1:5000
```

---

## Cluster Membership Check

Run this on **both Keycloak VMs**:

```bash
sudo docker logs keycloak | egrep -i "ISPN000094|cluster view|rebalance"
```

A healthy cluster should show a view containing **2 members**.

---

## Summary

This repository provides:

- a **2-node Keycloak HA design**
- **shared PostgreSQL persistence**
- **NGINX load balancing**
- **cluster discovery with `jdbc-ping`**
- **sticky sessions for client continuity**
- **background Flask execution using `systemd`**

It is a strong improvement over a single-node Keycloak deployment, while still leaving room for future HA improvements in:

- PostgreSQL
- NGINX
- full end-to-end redundancy
