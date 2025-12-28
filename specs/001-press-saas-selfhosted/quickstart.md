# Quickstart: Plateforme Cloud SaaS Self-Hosted

**Objectif**: Deployer la plateforme Press self-hosted en moins de 30 minutes.

---

## Prerequisites

### Systeme

- Linux Ubuntu 22.04+ (ou compatible)
- 8 CPU cores minimum
- 16 GB RAM minimum
- 200 GB SSD disponible

### Logiciels

- Docker 24+ ou Podman 4+
- Docker Compose v2+ (ou podman-compose)
- Git
- mkcert (pour dev local)

### Verification

Verifier les prerequisites:

```
docker --version
docker compose version
git --version
```

Pour Podman:

```
podman --version
podman-compose --version
```

---

## Step 1: Clone le Repository (2 min)

```
git clone https://github.com/votre-org/erp-saas-cloud-press.git
cd erp-saas-cloud-press
```

---

## Step 2: Configuration Initiale (5 min)

### Copier le fichier d environnement

```
cp config/.env.example config/.env
```

### Editer les variables essentielles

```
# config/.env

# Domain configuration
DOMAIN=platform.local
PRESS_SUBDOMAIN=press

# MinIO credentials
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=CHANGE_ME_SECURE_PASSWORD

# MariaDB credentials
MARIADB_ROOT_PASSWORD=CHANGE_ME_ROOT_PASSWORD
MARIADB_PASSWORD=CHANGE_ME_USER_PASSWORD

# Redis password
REDIS_PASSWORD=CHANGE_ME_REDIS_PASSWORD

# Admin credentials
ADMIN_PASSWORD=CHANGE_ME_ADMIN_PASSWORD

# Traefik email (pour Let's Encrypt)
ACME_EMAIL=admin@example.com
```

### Generer les secrets (recommande)

```
# Generer des passwords securises
openssl rand -base64 32  # Pour MINIO_SECRET_KEY
openssl rand -base64 32  # Pour MARIADB_ROOT_PASSWORD
openssl rand -base64 32  # Pour REDIS_PASSWORD
```

---

## Step 3: Certificats SSL (3 min)

### Mode Developpement (mkcert)

```
# Installer mkcert si necessaire
# Ubuntu/Debian
sudo apt install mkcert

# Fedora
sudo dnf install mkcert

# macOS
brew install mkcert

# Generer le CA local
mkcert -install

# Generer les certificats wildcard
cd docker/config/traefik/certs
mkcert "*.platform.local" platform.local
```

### Mode Production (Let's Encrypt)

Les certificats seront generes automatiquement par Traefik.
Assurez-vous que:
1. Le domaine pointe vers votre serveur
2. Les ports 80/443 sont accessibles depuis Internet
3. ACME_EMAIL est configure

---

## Step 4: Configuration DNS (2 min)

### Mode Developpement

Ajouter au fichier /etc/hosts (Linux/Mac) ou C:\Windows\System32\drivers\etc\hosts (Windows):

```
127.0.0.1 platform.local
127.0.0.1 press.platform.local
127.0.0.1 minio.platform.local
127.0.0.1 grafana.platform.local
```

### Mode Production

Configurer les enregistrements DNS A:
- platform.local -> IP_SERVEUR
- *.platform.local -> IP_SERVEUR (wildcard)

---

## Step 5: Demarrage des Services (10 min)

### Demarrer l infrastructure de base

```
cd docker/compose

# Demarrer dans l ordre
docker compose -f mariadb.yml up -d
docker compose -f redis.yml up -d
docker compose -f minio.yml up -d
docker compose -f traefik.yml up -d

# Attendre que MariaDB soit pret
docker compose -f mariadb.yml logs -f
# Ctrl+C quand "ready for connections" apparait
```

### Demarrer Press

```
docker compose -f press.yml up -d
```

### Verifier le statut

```
docker compose ps
```

Tous les conteneurs doivent etre en etat "running" ou "healthy".

---

## Step 6: Initialisation Press (5 min)

### Creer le site Press

```
docker exec -it erp-saas-cloud-c16-press bench new-site press.platform.local \
  --admin-password $ADMIN_PASSWORD \
  --mariadb-root-password $MARIADB_ROOT_PASSWORD
```

### Installer l app Press

```
docker exec -it erp-saas-cloud-c16-press bench --site press.platform.local \
  install-app press
```

### Activer le scheduler

```
docker exec -it erp-saas-cloud-c16-press bench --site press.platform.local \
  enable-scheduler
```

---

## Step 7: Verification (3 min)

### Acceder au dashboard Press

Ouvrir dans le navigateur:
- URL: https://press.platform.local:32443
- Login: Administrator
- Password: (le ADMIN_PASSWORD configure)

### Verifier les services

| Service | URL | Expected |
|---------|-----|----------|
| Press | https://press.platform.local:32443 | Page login |
| Traefik | http://localhost:32381 | Dashboard |
| MinIO | http://localhost:32391 | Console |
| Grafana | http://localhost:32393 | Dashboard |

### Test de sante

```
curl -k https://press.platform.local:32443/api/method/ping
```

Reponse attendue: {"message": "pong"}

---

## Step 8: Creer un Premier Site Tenant

### Via le dashboard

1. Connectez-vous au dashboard Press
2. Allez dans "Sites" > "Add Site"
3. Remplissez:
   - Subdomain: demo
   - Plan: Free
   - Apps: frappe (minimum)
4. Cliquez "Create"
5. Attendez que le statut passe a "Active"

### Via CLI

```
docker exec -it erp-saas-cloud-c16-press bench --site press.platform.local \
  execute press.api.site.new --args '{"subdomain": "demo", "apps": ["frappe"]}'
```

### Acceder au site tenant

URL: https://demo.platform.local:32443

---

## Troubleshooting

### Les conteneurs ne demarrent pas

```
# Verifier les logs
docker compose logs erp-saas-cloud-c16-press

# Verifier l espace disque
df -h

# Verifier la memoire
free -h
```

### Erreur de connexion MariaDB

```
# Verifier que MariaDB est pret
docker exec -it erp-saas-cloud-c16-mariadb mysql -u root -p -e "SELECT 1"
```

### Certificat SSL invalide

En dev local avec mkcert:
```
# Reinstaller le CA
mkcert -install

# Regenerer les certs
mkcert "*.platform.local"
```

### MinIO inaccessible

```
# Verifier le conteneur
docker logs erp-saas-cloud-c16-minio

# Tester la connexion S3
aws --endpoint-url http://localhost:32390 s3 ls
```

---

## Next Steps

1. **Configurer les backups automatiques** - Voir la documentation backups
2. **Ajouter le monitoring** - Deployer Prometheus/Grafana/Wazuh
3. **Configurer les alertes** - Definir les seuils et notifications
4. **Creer des Release Groups** - Pour deployer des apps custom

---

## Commandes Utiles

```
# Arreter tous les services
docker compose down

# Voir les logs en temps reel
docker compose logs -f

# Redemarrer un service
docker compose restart erp-saas-cloud-c16-press

# Backup manuel
docker exec erp-saas-cloud-c16-press bench --site press.platform.local backup

# Console Frappe
docker exec -it erp-saas-cloud-c16-press bench --site press.platform.local console
```

---

## Support

- Documentation: /specs/001-press-saas-selfhosted/
- Issues: GitHub Issues
- Forum: Frappe Forum
