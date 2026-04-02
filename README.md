Keycloak High Availability (HA) Deployment Documentation

What is KeyCloak?
Keycloak is an open-source Identity and Access Management (IAM) solution designed to secure modern applications and services, such as websites, APIs, and mobile apps, with minimal effort.
Executive Summary
This document details the architecture and deployment of a Level 2 High Availability (HA) IAM system using Keycloak. The system is designed to provide fault tolerance, high concurrency, and seamless failover for a Flask-based client application. The infrastructure is containerized (Docker) and orchestrated on Ubuntu VMs and utilizes Nginx as a reverse proxy and load balancer.
Architecture Overview
VM1 NGINX LB: 10.9.0.71 (native NGINX, port 80)
VM2 Keycloak Node1: 10.9.0.72 (Docker)
VM3 Keycloak Node2: 10.9.0.73 (Docker)
VM4 PostgreSQL: 10.9.0.74 (Docker)
System Overview
The architecture is visualized below. It demonstrates a clear separation of concerns using a Red/Green flow strategy:


Red Path (Request): Represents the flow of user credentials traveling "Down" the stack (User → App(Python Flask) → Nginx(LB) → Keycloak → Database).


Green Path (Response): Represents the return of the Authentication Token "Up" the stack to the User.

Prerequisites & Environment Setup
On the Ubuntu VMs (Server)
OS: Ubuntu 20.04/22.04 LTS.
Software: Docker Engine, Docker Compose, Nginx.
RAM : 2gb
CPU: 2 Core
Storage: 15-20 GB
On the Host Machine (Client)
Software: Python 3.x, pip.
Network: Must be able to ping the Ubuntu VM's IP addresses.

This guide uses:
Keycloak 26.1.0
Postgres 16
Docker installed via docker.io + docker-compose-v2
Keycloak cluster (Infinispan + JGroups) with jdbc-ping
NGINX sticky sessions (cookie-based, using AUTH_SESSION_ID)
0) Run on ALL VMs (71,72,73,74): install base packages

sudo apt update
sudo apt install -y ufw curl netcat-openbsd docker.io docker-compose-v2
sudo systemctl enable --now docker
docker --version
docker compose version
1) VM4 (10.9.0.74) — PostgreSQL in Docker
1.1 Deploy Postgres

sudo mkdir -p /opt/postgres
cd /opt/postgres


Create compose:

sudo tee /opt/postgres/docker-compose.yml > /dev/null <<'EOF'
services:
  postgres:
    image: postgres:16
    container_name: postgres-keycloak
    restart: unless-stopped
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: "ChangeMe_StrongPassword"
    volumes:
      - ./data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
EOF

Start:

cd /opt/postgres
sudo docker compose up -d
sudo docker ps

1.2 Firewall on VM4 (DB only from KC nodes)

sudo ufw allow 22/tcp
sudo ufw allow from 10.9.0.72 to any port 5432 proto tcp
sudo ufw allow from 10.9.0.73 to any port 5432 proto tcp
sudo ufw enable
sudo ufw status

2) VM2 (10.9.0.72) — Keycloak Node1 (Docker, host networking)
2.1 Deploy Keycloak node1

sudo mkdir -p /opt/keycloak
cd /opt/keycloak


Create compose:

sudo tee /opt/keycloak/docker-compose.yml > /dev/null <<'EOF'
services:
  keycloak:
    image: quay.io/keycloak/keycloak:26.1.0
    container_name: keycloak
    restart: unless-stopped

    # REQUIRED for multi-VM clustering (avoid 172.18.x.x addresses)
    network_mode: host

    environment:
      # Admin bootstrap
      KC_BOOTSTRAP_ADMIN_USERNAME: admin
      KC_BOOTSTRAP_ADMIN_PASSWORD: "ChangeMe_AdminStrongPassword"

      # Database
      KC_DB: postgres
      KC_DB_URL: "jdbc:postgresql://10.9.0.74:5432/keycloak"
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: "ChangeMe_StrongPassword"

      # Reverse proxy entry is NGINX IP (no domain)
      KC_PROXY_HEADERS: xforwarded
      KC_HTTP_ENABLED: "true"
      KC_HOSTNAME: "10.9.0.71"
      KC_HOSTNAME_STRICT: "false"

      # Cluster
      KC_CACHE: ispn
      KC_CACHE_STACK: jdbc-ping
      KC_NODE_NAME: kc1

      # Bind cluster traffic to VM IP (critical)
      JAVA_OPTS_APPEND: "-Djgroups.bind_addr=10.9.0.72"

      KC_HEALTH_ENABLED: "true"

    command:
      - start
      - --http-port=8080
EOF

Start:

cd /opt/keycloak
sudo docker compose down || true
sudo docker rm -f keycloak || true
sudo docker compose up -d
sudo docker logs -f keycloak

The docker-compose.yml file defines a containerized Keycloak node that runs using the VM’s host network, connects to the shared PostgreSQL database, and operates behind the NGINX reverse proxy and load balancer. The image variable specifies the Keycloak version to run, while container_name gives the container a fixed and recognizable name, and restart: unless-stopped ensures that the service automatically comes back after a failure or reboot. The environment variables control the main application behavior: KC_BOOTSTRAP_ADMIN_USERNAME and KC_BOOTSTRAP_ADMIN_PASSWORD create the initial administrator account during first startup; KC_DB, KC_DB_URL, KC_DB_USERNAME, and KC_DB_PASSWORD define the database type and the connection details Keycloak uses to access the shared PostgreSQL backend; KC_PROXY_HEADERS=xforwarded tells Keycloak to trust the forwarded headers sent by NGINX; KC_HTTP_ENABLED=true allows backend HTTP communication on port 8080; KC_HOSTNAME defines the public entry point that users access through the load balancer; and KC_HOSTNAME_STRICT=false was used to relax hostname validation during testing and reverse-proxy access troubleshooting. For clustering, KC_CACHE=ispn enables the Infinispan cache, KC_CACHE_STACK=jdbc-ping allows both Keycloak nodes to discover each other through the shared database, and KC_NODE_NAME uniquely identifies each cluster member, such as kc1 for node 1 and kc2 for node 2. The JAVA_OPTS_APPEND setting is used to bind JGroups cluster communication to the actual VM IP address of each node, ensuring that cluster traffic uses the real server network rather than Docker’s internal bridge addresses. Finally, KC_HEALTH_ENABLED=true enables health-check endpoints for service monitoring, while the command section starts Keycloak in standard server mode and makes it listen on HTTP port 8080, which is the backend port used by NGINX to forward authentication requests to the cluster.
2.2 Firewall on VM2
Allow:
SSH
NGINX LB to reach Keycloak on 8080
Node2 to reach cluster ports (7800 + 57800)

sudo ufw allow 22/tcp
sudo ufw allow from 10.9.0.71 to any port 8080 proto tcp
sudo ufw allow from 10.9.0.73 to any port 7800 proto tcp
sudo ufw allow from 10.9.0.73 to any port 57800 proto tcp
sudo ufw enable
sudo ufw status


3) VM3 (10.9.0.73) — Keycloak Node2 (Docker, host networking)
3.1 Deploy Keycloak node2

sudo mkdir -p /opt/keycloak
cd /opt/keycloak

Create compose:

sudo tee /opt/keycloak/docker-compose.yml > /dev/null <<'EOF'
services:
  keycloak:
    image: quay.io/keycloak/keycloak:26.1.0
    container_name: keycloak
    restart: unless-stopped
    network_mode: host

    environment:
      KC_BOOTSTRAP_ADMIN_USERNAME: admin
      KC_BOOTSTRAP_ADMIN_PASSWORD: "ChangeMe_AdminStrongPassword"

      KC_DB: postgres
      KC_DB_URL: "jdbc:postgresql://10.9.0.74:5432/keycloak"
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: "ChangeMe_StrongPassword"

      KC_PROXY_HEADERS: xforwarded
      KC_HTTP_ENABLED: "true"
      KC_HOSTNAME: "10.9.0.71"
      KC_HOSTNAME_STRICT: "false"

      KC_CACHE: ispn
      KC_CACHE_STACK: jdbc-ping
      KC_NODE_NAME: kc2

      JAVA_OPTS_APPEND: "-Djgroups.bind_addr=10.9.0.73"

      KC_HEALTH_ENABLED: "true"

    command:
      - start
      - --http-port=8080
EOF

Start:

cd /opt/keycloak
sudo docker compose down || true
sudo docker rm -f keycloak || true
sudo docker compose up -d
sudo docker logs -f keycloak

3.2 Firewall on VM3
Allow:
SSH
NGINX LB to reach Keycloak on 8080
Node1 to reach cluster ports (7800 + 57800)

sudo ufw allow 22/tcp
sudo ufw allow from 10.9.0.71 to any port 8080 proto tcp
sudo ufw allow from 10.9.0.72 to any port 7800 proto tcp
sudo ufw allow from 10.9.0.72 to any port 57800 proto tcp
sudo ufw enable
sudo ufw status


4) VM1 (10.9.0.71) — NGINX Load Balancer (sticky sessions)
4.1 Install NGINX + remove default site

sudo apt update
sudo apt install -y nginx ufw
sudo rm -f /etc/nginx/sites-enabled/default
sudo rm -f /etc/nginx/sites-available/default

4.2 Create NGINX config (use conf.d)
Create /etc/nginx/conf.d/keycloak.conf:

sudo tee /etc/nginx/conf.d/keycloak.conf > /dev/null <<'EOF'
# Sticky sessions using Keycloak cookie AUTH_SESSION_ID.
# If cookie not present yet, fall back to client IP.

map $cookie_AUTH_SESSION_ID $kc_sticky_key {
    default $cookie_AUTH_SESSION_ID;
    ""      $remote_addr;
}

upstream keycloak_upstream {
    hash $kc_sticky_key consistent;

    server 10.9.0.72:8080 max_fails=3 fail_timeout=10s;
    server 10.9.0.73:8080 max_fails=3 fail_timeout=10s;

    keepalive 32;
}

server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://keycloak_upstream;

        proxy_http_version 1.1;
        proxy_set_header Connection "";

        # Forwarded headers for Keycloak behind NGINX
        proxy_set_header Host              $http_host;
        proxy_set_header X-Forwarded-Host  $http_host;
        proxy_set_header X-Forwarded-Port  $server_port;

        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Debug header to confirm which upstream served this request
        add_header X-Upstream $upstream_addr always;

        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

Test + reload:

sudo nginx -t
sudo systemctl restart nginx

4.3 Firewall on VM1 (allow HTTP)

sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw enable
sudo ufw status

5) Verification (do in order)
5.1 DB connectivity checks
On VM2:

nc -zv 10.9.0.74 5432

On VM3:

nc -zv 10.9.0.74 5432

5.2 LB can reach both nodes
On VM1:

curl -I http://10.9.0.72:8080
curl -I http://10.9.0.73:8080

5.3 Cluster must show 2 members
On VM2 and VM3:

sudo docker logs keycloak | egrep -i "ISPN000094|cluster view|rebalance"

Expected output contains (2) members.
5.4 Open in browser
Go to:
http://10.9.0.71/
