# 📁 Structure du Dossier Apps

Ce dossier contient toutes les applications Frappe utilisées dans le projet **ERP SaaS Cloud PRESSE v16**.

## 🏗️ Structure

```
apps/
├── frappe/              # Frappe Framework v16 (develop)
├── press/               # Frappe Press v0.7.0 (officiel)
├── storage_integration/ # Storage Integration app
└── press_selfhosted/    # Notre app custom (overrides et extensions)
```

## 📦 Applications

### 1. **frappe/** - Frappe Framework
- **Source**: https://github.com/frappe/frappe.git
- **Branche**: develop
- **Version**: v16.x-develop
- **Description**: Framework Python pour applications web et ERP
- **Rôle**: Framework de base pour toutes les apps

### 2. **press/** - Frappe Press
- **Source**: https://github.com/frappe/press.git
- **Branche**: develop
- **Version**: v0.7.0
- **Description**: Plateforme officielle de gestion d'hébergement Frappe/ERPNext
- **Rôle**: App principale pour gestion des sites, serveurs, déploiements

### 3. **storage_integration/** - Storage Integration
- **Source**: https://github.com/frappe/storage_integration.git
- **Branche**: develop
- **Version**: v0.0.1
- **Description**: Intégration S3/MinIO pour stockage fichiers
- **Rôle**: Gestion du stockage d'objets (backups, fichiers)

### 4. **press_selfhosted/** - Notre App Custom
- **Source**: Développement local (pas de repo git officiel)
- **Description**: Overrides et extensions pour Press Self-Hosted
- **Rôle**: Adaptations pour déploiement local sans cloud
- **Contenu**:
  - Overrides de DocTypes (Site, Bench, Backup)
  - Services custom (site_provisioner, database_manager)
  - Intégrations locales (MinIO, Traefik)
  - API endpoints supplémentaires

## 🔧 Installation dans le Container

Ces apps sont installées dans le container via le Dockerfile :

```dockerfile
# Clone des apps officielles
RUN git clone --branch develop --depth 1 https://github.com/frappe/frappe.git apps/frappe
RUN git clone --branch develop --depth 1 https://github.com/frappe/press.git apps/press
RUN git clone --branch develop --depth 1 https://github.com/frappe/storage_integration.git apps/storage_integration

# Installation des apps
RUN bench get-app press
RUN bench get-app storage_integration
```

## 🐍 PYTHONPATH Configuration

Pour que Python puisse importer les modules correctement, le PYTHONPATH doit inclure :

```bash
PYTHONPATH=/home/frappe/frappe-bench/apps:\
/home/frappe/frappe-bench/apps/press:\
/home/frappe/frappe-bench/apps/storage_integration
```

Ceci est configuré dans `docker-compose-c16-press.yml`.

## 📝 Notes Importantes

1. **Ne pas modifier directement** les apps officielles (frappe, press, storage_integration)
2. **Toutes les customisations** doivent aller dans `press_selfhosted/`
3. **Git repositories** : frappe, press, et storage_integration sont des clones git officiels
4. **Updates** : Pour mettre à jour, faire `git pull` dans chaque dossier

## 🔄 Mise à Jour des Apps

```bash
# Frappe Framework
cd apps/frappe && git pull origin develop

# Press
cd apps/press && git pull origin develop

# Storage Integration
cd apps/storage_integration && git pull origin develop
```

## ⚠️ Backup Précédent

Un backup de l'ancienne structure a été créé :
- `apps_backup_20251223_030345.tar.gz` (89M)
- Contient l'ancienne structure avec `apps/apps/` dupliqué

## 📊 Tailles

- frappe: ~60M
- press: ~12M
- storage_integration: ~2M
- press_selfhosted: ~100K (notre code)

---

**Dernière mise à jour**: 2025-12-23
**Structure nettoyée et réorganisée** : Suppression des dossiers vides et duplication
