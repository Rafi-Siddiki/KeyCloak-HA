# KeyCloak-HA

## Why High Available KeyCloak?

In our current setup, only a single Keycloak instance is running. That means the authentication tier is **not fault tolerant**: if that one Keycloak node becomes unavailable because of a service crash, VM failure, maintenance window, or network problem, authentication requests can no longer be served by another Keycloak node. This repository provides an improved design by deploying **two Keycloak nodes in a cluster** and establishing node discovery through **JGroups/Infinispan with `jdbc-ping`**, so that both nodes can participate in the same Keycloak cluster while sharing a common PostgreSQL database. According to the current Keycloak caching documentation, when Keycloak runs in production mode, distributed caching is enabled and nodes are discovered by default using the **`jdbc-ping` stack**, which uses the configured database to track cluster members. This makes `jdbc-ping` a suitable mechanism for building a multi-node Keycloak deployment on separate virtual machines.

> Important: this repository improves **Keycloak-tier availability**, but it is **not full end-to-end fault tolerance** yet, because the documented architecture still contains a **single NGINX load balancer VM** and a **single PostgreSQL VM**. In other words, the Keycloak layer becomes redundant, but NGINX and PostgreSQL remain single points of failure unless they are also made highly available.

## Architecture overview

This repository follows the 4-VM architecture from the deployment document:

- **VM1** — NGINX load balancer: `10.9.0.71`
- **VM2** — Keycloak node 1: `10.9.0.72`
- **VM3** — Keycloak node 2: `10.9.0.73`
- **VM4** — PostgreSQL: `10.9.0.74`

The documented request flow is:

**User → Flask App → NGINX Load Balancer → Keycloak Cluster → PostgreSQL**

and the response returns back up the same path after authentication succeeds.

## Architecture diagram

![Keycloak HA Architecture](diagram.png)

The diagram above reflects the HA model described in the deployment document: the Flask application sends authentication requests to the NGINX reverse proxy and load balancer, NGINX distributes those requests to two Keycloak nodes, the two Keycloak nodes synchronize cluster state through Infinispan/JGroups, and both nodes use the shared PostgreSQL database as their persistent backend.

## Repository layout

```text
KeyCloak-HA/
├── postgres/
│   ├── docker-compose.yml
│   └── .env.example
├── keycloak-node1/
│   ├── docker-compose.yml
│   └── .env.example
├── keycloak-node2/
│   ├── docker-compose.yml
│   └── .env.example
├── nginx/
│   ├── docker-compose.yml
│   ├── .env.example
│   └── default.conf.template
├── flask-app/
│   ├── docker-compose.yml
│   └── .env.example
├── .gitignore
└── README.md
```

## Technology stack

- Keycloak `26.1.0`
- PostgreSQL `16`
- Docker Engine
- Docker Compose v2
- NGINX reverse proxy / load balancer
- Infinispan + JGroups clustering
- `jdbc-ping` for Keycloak node discovery
- Sticky sessions using `AUTH_SESSION_ID`

## How the cluster works

Each Keycloak node runs as an independent container on its own VM, but both nodes point to the same PostgreSQL database and are configured with distributed caching. In this design, `KC_CACHE=ispn` enables Infinispan, `KC_CACHE_STACK=jdbc-ping` allows the nodes to discover each other through the shared database, and `JAVA_OPTS_APPEND` binds JGroups traffic to the real VM IP of each Keycloak node. NGINX sits in front of both nodes and forwards authentication traffic to them using sticky sessions, so that a user session remains consistently associated with the same backend node when possible.

## Important note about NGINX in this repository

The original deployment document uses **native NGINX installed directly on VM1**. This repository packages NGINX with Docker Compose for easier version-controlled deployment, but preserves the same functional role: listening on port `80`, forwarding traffic to `10.9.0.72:8080` and `10.9.0.73:8080`, forwarding the required `X-Forwarded-*` headers, and using sticky-session behavior based on Keycloak's `AUTH_SESSION_ID` cookie. If you prefer to match the document exactly, you can install NGINX natively and use the repository's NGINX configuration as the source template.

## Deployment prerequisites

Prepare the Ubuntu VMs with:

- Ubuntu `20.04` or `22.04` LTS
- Docker Engine
- Docker Compose v2

Example base installation used by the deployment document:

```bash
sudo apt update
```
```bash
sudo apt install -y docker.io docker-compose-v2
```
```bash
sudo systemctl enable --now docker
```

## Deployment steps by VM

Clone the same repository on every VM, but only deploy the directory that belongs to that VM.

### 1. PostgreSQL VM (`10.9.0.74`)

```bash
git clone https://github.com/Rafi-Siddiki/KeyCloak-HA.git
```
```bash
cd KeyCloak-HA/postgres
```
```bash
docker compose up -d
```


### 2. Keycloak node 1 VM (`10.9.0.72`)

```bash
git clone https://github.com/Rafi-Siddiki/KeyCloak-HA.git
```
```bash
cd KeyCloak-HA/keycloak-node1
```

```bash
docker compose up -d
```

### 3. Keycloak node 2 VM (`10.9.0.73`)

```bash
git clone https://github.com/Rafi-Siddiki/KeyCloak-HA.git
```
```bash
cd KeyCloak-HA/keycloak-node2
```

```bash
docker compose up -d
```

### 4. NGINX VM (`10.9.0.71`)

```bash
git clone https://github.com/Rafi-Siddiki/KeyCloak-HA.git
```
```bash
cd KeyCloak-HA/nginx
```
```bash
docker compose up -d
```

### 5. Flask application VM

```bash
git clone docker run -p 5000:5000 --name my-app-container --env-file .env rafisiddiki/flask-app:1.0.0
```
```bash
cd KeyCloak-HA/flask-app
```
```bash
cp .env.example .env
```
```bash
nano .env
```
```bash
docker compose up -d
```

## Verification

### PostgreSQL

```bash
docker ps
```
```bash
docker logs postgres-keycloak --tail 50
```

### Keycloak nodes

```bash
docker ps
```
```bash
docker logs keycloak --tail 50
```
```bash
curl -I http://127.0.0.1:8080
```

### NGINX

```bash
docker ps
```
```bash
docker logs nginx-keycloak-lb --tail 50
```
```bash
curl -I http://127.0.0.1
```

### Flask application

```bash
docker ps
```
```bash
docker logs flask-app --tail 50
```
```bash
curl http://127.0.0.1:5000
```

### Cluster membership check

Run this on both Keycloak VMs:

```bash
sudo docker logs keycloak | egrep -i "ISPN000094|cluster view|rebalance"
```

A successful cluster formation should show a view containing **2 members**.

