# Deployment Guide for The Library on IONOS VPS

## Prerequisites
- VPS with Docker and Docker Compose installed
- Traefik already running (from retcon-black-mountain project)
- DNS A record: `thelibrary.retconblackmountain.info` → your VPS IP

## Step 1: Prepare on Local Machine

```bash
# Navigate to project directory
cd /path/to/the-library

# Build and test the index locally (optional but recommended)
python indexer/build_index.py

# Verify docker-compose.prod.yml is present
ls docker-compose.prod.yml
```

## Step 2: Upload Project to VPS

```bash
# From your local machine, upload the project
# Replace USER and VPS_IP with your credentials
rsync -avz --exclude 'node_modules' --exclude '__pycache__' --exclude '.git' \
  ./ USER@VPS_IP:/opt/the-library/

# Or use scp
tar -czf the-library.tar.gz --exclude='node_modules' --exclude='__pycache__' --exclude='.git' .
scp the-library.tar.gz USER@VPS_IP:/opt/
```

## Step 3: Deploy on VPS

```bash
# SSH into your VPS
ssh USER@VPS_IP

# Navigate to project directory
cd /opt/the-library

# Build and start containers
docker-compose -f docker-compose.prod.yml up -d --build

# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Verify containers are running
docker ps | grep library
```

## Step 4: Build the Index

```bash
# Enter the API container
docker exec -it library-api bash

# Build the search index
python indexer/build_index.py

# Exit container
exit
```

## Step 5: Verify Deployment

- Visit: https://thelibrary.retconblackmountain.info
- Traefik will automatically provision SSL certificate via Let's Encrypt
- First certificate request may take 30-60 seconds

## Useful Commands

### View logs
```bash
docker-compose -f docker-compose.prod.yml logs -f library-nginx
docker-compose -f docker-compose.prod.yml logs -f library-api
docker-compose -f docker-compose.prod.yml logs -f library-ui
```

### Restart services
```bash
docker-compose -f docker-compose.prod.yml restart
```

### Stop services
```bash
docker-compose -f docker-compose.prod.yml down
```

### Rebuild after code changes
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

### Rebuild index
```bash
docker exec -it library-api python indexer/build_index.py
```

### Backup database
```bash
docker exec library-api cp /app/index/library.db /app/index/library_backup_$(date +%Y%m%d).db
docker cp library-api:/app/index/library_backup_*.db ./backups/
```

## Network Architecture

```
Internet
   ↓
Traefik (ports 80/443)
   ├→ retconblackmountain.info → [existing retcon-bm containers]
   └→ thelibrary.retconblackmountain.info → library-nginx
                                              ↓
                                         library-ui (React)
                                         library-api (FastAPI)
```

All containers share the `rbm-network` Docker network.

## Troubleshooting

### Certificate not provisioning
```bash
# Check Traefik logs
docker logs traefik

# Verify DNS propagation
dig thelibrary.retconblackmountain.info
```

### Container won't start
```bash
# Check if rbm-network exists
docker network ls | grep rbm

# View container logs
docker-compose -f docker-compose.prod.yml logs library-api
```

### Search not working
```bash
# Verify index exists
docker exec library-api ls -lh /app/index/

# Check if index needs building
docker exec -it library-api python indexer/build_index.py
```

## Updating the Application

```bash
# On local machine: push changes to git
git add .
git commit -m "Update"
git push

# On VPS: pull and rebuild
cd /opt/the-library
git pull
docker-compose -f docker-compose.prod.yml up -d --build
```
