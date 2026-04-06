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
- [Verification](#verification)
  - [PostgreSQL](#postgresql-verification)
  - [Keycloak Nodes](#keycloak-nodes-verification)
  - [NGINX](#nginx-verification)
  - [Flask Application](#flask-application-verification)
  - [Cluster Membership Check](#cluster-membership-check)

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
│   └── .env
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
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
```

---

## `/etc/hosts` Configuration

Edit the `/etc/hosts` file on **each VM** and add:

```bash
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
cd KeyCloak-HA/postgres
docker compose up -d
```

---

## 2. Keycloak Node 1 VM

**VM:** `10.9.0.72`  
**Hostname:** `kc-node1.xyz`

```bash
git clone https://github.com/Rafi-Siddiki/KeyCloak-HA.git
cd KeyCloak-HA/keycloak-node1
docker compose up -d
```

---

## 3. Keycloak Node 2 VM

**VM:** `10.9.0.73`  
**Hostname:** `kc-node2.xyz`

```bash
git clone https://github.com/Rafi-Siddiki/KeyCloak-HA.git
cd KeyCloak-HA/keycloak-node2
docker compose up -d
```

---

## 4. NGINX VM

**VM:** `10.9.0.71`  
**Hostname:** `auth.lb.xyz`

```bash
git clone https://github.com/Rafi-Siddiki/KeyCloak-HA.git
cd KeyCloak-HA/nginx
docker compose up -d
```

---

## 5. Flask Application Setup

The Flask application needs a properly configured Keycloak realm and client before it can authenticate users.

### Phase 1: Create Realm and Client

#### Create the Realm

1. Open the **Keycloak Admin Console**
2. Hover over the realm selector in the top-left corner
3. Click **Create Realm**
4. Set the realm name to:

```text
electronic-shop
```

#### Create the Client

1. Go to **Clients**
2. Click **Create client**
3. Set the **Client ID** to:

```text
flask-app
```

4. Click **Next**

---

### Phase 2: Configure Client Capabilities

To allow the Flask app to work as a secure backend client:

#### Enable Client Authentication

In the **Capability config** tab for `flask-app`:

- turn **Client authentication** = `On`

#### Configure Access Grants

Under **Authentication flow**:

- ensure **Direct access grants** is enabled

#### Save Changes

- click **Save**

---

### Phase 3: Retrieve Client Secret

Once client authentication is enabled, Keycloak generates a secret for the client.

#### Steps

1. Open the **Credentials** tab
2. Locate **Client secret**
3. Copy the generated secret

---

### Phase 4: Update Flask Environment File

Open the Flask app `.env` file and set:

```bash
KEYCLOAK_CLIENT_SECRET=your_copied_secret_here
```

---

### Run the Flask Application

You can run the Flask application either from:

- the code base
- Docker Compose

---

### Option A: Code Base

```bash
navigate to /KeyCloak-HA/flask-app/Code Base
```

Main application entry:

```bash
app.py
```

---

### Option B: Docker

If you are using Docker directly:

```bash
docker run -p 5000:5000 --name my-app-container --env-file .env rafisiddiki/flask-app:1.0.0
```

Or if you are using the repository deployment:

```bash
cd KeyCloak-HA/flask-app
cp .env.example .env
nano .env
docker compose up -d
```

---

## Verification

After deployment, verify each component separately.

---

## PostgreSQL Verification

```bash
docker ps
docker logs postgres-keycloak --tail 50
```

---

## Keycloak Nodes Verification

```bash
docker ps
docker logs keycloak --tail 50
curl -I http://127.0.0.1:8080
```

---

## NGINX Verification

```bash
docker ps
docker logs nginx-keycloak-lb --tail 50
curl -I http://127.0.0.1
```

---

## Flask Application Verification

```bash
docker ps
docker logs flask-app --tail 50
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

It is a strong improvement over a single-node Keycloak deployment, while still leaving room for future HA improvements in:

- PostgreSQL
- NGINX
- full end-to-end redundancy
