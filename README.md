# KeyCloak-HA

This repository mirrors the 4-VM high-availability Keycloak layout:

- NGINX load balancer: `10.9.0.71`
- Keycloak node 1: `10.9.0.72`
- Keycloak node 2: `10.9.0.73`
- PostgreSQL: `10.9.0.74`
- Flask app image: `rafisiddiki/flask-app:1.0.0`

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

## How to use it

Clone the same repository on every VM, but run only the folder that belongs to that VM.

### 1) PostgreSQL VM (10.9.0.74)

```bash
git clone <your-repo-url>
cd KeyCloak-HA/postgres
cp .env.example .env
nano .env
docker compose --env-file .env up -d
```

### 2) Keycloak node 1 VM (10.9.0.72)

```bash
git clone <your-repo-url>
cd KeyCloak-HA/keycloak-node1
cp .env.example .env
nano .env
docker compose --env-file .env up -d
```

### 3) Keycloak node 2 VM (10.9.0.73)

```bash
git clone <your-repo-url>
cd KeyCloak-HA/keycloak-node2
cp .env.example .env
nano .env
docker compose --env-file .env up -d
```

### 4) NGINX VM (10.9.0.71)

```bash
git clone <your-repo-url>
cd KeyCloak-HA/nginx
cp .env.example .env
nano .env
docker compose --env-file .env up -d
```

### 5) Flask app VM

```bash
git clone <your-repo-url>
cd KeyCloak-HA/flask-app
cp .env.example .env
nano .env
docker compose --env-file .env up -d
```

## Update flow

When you release a new Flask image, push a new tag to Docker Hub, then update `FLASK_IMAGE` in `flask-app/.env`.

Example:

```env
FLASK_IMAGE=rafisiddiki/flask-app:1.0.1
```

Then redeploy:

```bash
docker compose --env-file .env pull
docker compose --env-file .env up -d
```

## Verification

### PostgreSQL

```bash
docker ps
docker logs postgres-keycloak --tail 50
```

### Keycloak nodes

```bash
docker ps
docker logs keycloak --tail 50
curl -I http://127.0.0.1:8080
```

### NGINX

```bash
docker ps
docker logs nginx-keycloak-lb --tail 50
curl -I http://127.0.0.1
```

### Flask app

```bash
docker ps
docker logs flask-app --tail 50
curl http://127.0.0.1:5000
```

## Push this repository to GitHub

From the root of the repository:

```bash
git init
git branch -M main
git add .
git commit -m "Initial Keycloak HA deployment repository"
git remote add origin <your-github-repo-url>
git push -u origin main
```

## Notes

- Do not commit real `.env` files.
- Do not commit the PostgreSQL `data/` directory.
- Change all placeholder passwords before production use.
- If you want to keep NGINX native instead of Dockerized, use only the `default.conf.template` as reference and install NGINX directly on the VM.
