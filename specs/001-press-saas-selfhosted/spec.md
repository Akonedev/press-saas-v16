# Feature Specification: Plateforme Cloud SaaS Self-Hosted

**Feature Branch**: `001-press-saas-selfhosted`
**Created**: 2025-12-20
**Status**: Draft
**Input**: Plateforme Cloud SaaS Self-Hosted B2B/B2C avec Frappe Press v16

## Executive Summary

Déploiement d'une plateforme Cloud SaaS entièrement self-hosted basée sur Frappe Press v16,
permettant d'offrir des services B2B et B2C sans dépendance aux providers cloud externes.
Tous les composants externes (AWS S3, Route53, DigitalOcean, Stripe) seront remplacés par
des alternatives open-source locales (MinIO, Traefik, PowerDNS, etc.).

## Research Summary

### Solutions Officielles Identifiées

| Composant | Solution Officielle | Source |
| --------- | ------------------- | ------ |
| Plateforme | frappe/press (AGPL-3.0) | [GitHub](https://github.com/frappe/press) |
| Docker Images | frappe/frappe_docker | [GitHub](https://github.com/frappe/frappe_docker) |
| Storage S3 | frappe/storage_integration | [GitHub](https://github.com/frappe/storage_integration) |
| Multi-tenant | frappe_docker single-server | [Docs](https://github.com/frappe/frappe_docker/blob/main/docs/single-server-example.md) |

### Providers à Remplacer

| Provider Actuel | Remplacement Local | Justification |
| --------------- | ------------------ | ------------- |
| AWS S3 | MinIO | S3-compatible, open-source, self-hosted |
| AWS Route53 | PowerDNS / CoreDNS | DNS local administrable |
| Hetzner/DigitalOcean | Docker/Podman local | Infrastructure locale |
| DigitalOcean Registry | Harbor / Docker Registry | Registry privé local |
| Cloudflare | Traefik | Reverse proxy + SSL + load balancing |
| Stripe | Optionnel (module billing) | Billing interne ou désactivé |
| Email externe | Postal / Mailhog | Serveur email local |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Déploiement Initial de la Plateforme (Priority: P1)

En tant qu'administrateur système, je veux déployer la plateforme Press complète sur mon
infrastructure locale avec Docker/Podman afin d'avoir un environnement SaaS fonctionnel
sans dépendances cloud externes.

**Why this priority**: C'est le fondement de toute la solution. Sans une plateforme
fonctionnelle, aucune autre fonctionnalité ne peut être utilisée.

**Independent Test**: La plateforme peut être déployée avec une seule commande
`docker-compose up` et affiche le dashboard Press accessible via navigateur.

**Acceptance Scenarios**:

1. **Given** un serveur Linux avec Docker/Podman installé, **When** j'exécute la commande
   de déploiement, **Then** tous les conteneurs démarrent et la page de login Press s'affiche

2. **Given** la plateforme déployée, **When** je me connecte avec les credentials admin,
   **Then** j'accède au dashboard d'administration Press

3. **Given** la plateforme active, **When** je vérifie les services de santé,
   **Then** tous les composants (MariaDB, Redis, Workers) sont opérationnels

---

### User Story 2 - Création d'un Site Tenant (Priority: P1)

En tant qu'administrateur Press, je veux créer un nouveau site tenant depuis l'interface
utilisateur afin de provisionner un espace client isolé.

**Why this priority**: La création de sites est la fonctionnalité core de Press,
indispensable pour le modèle SaaS multi-tenant.

**Independent Test**: Créer un site "demo.local" depuis le dashboard et y accéder
via navigateur avec SSL valide.

**Acceptance Scenarios**:

1. **Given** un administrateur connecté au dashboard Press, **When** je clique sur
   "Add Site" et renseigne un nom de domaine, **Then** le site est créé en moins de 5 minutes

2. **Given** un site en cours de création, **When** le processus termine,
   **Then** le site est accessible via son URL avec certificat SSL valide

3. **Given** un site tenant créé, **When** je me connecte au site,
   **Then** l'interface Frappe s'affiche avec les apps installées

---

### User Story 3 - Stockage sur MinIO (Priority: P1)

En tant qu'administrateur, je veux que tous les fichiers et backups soient stockés
sur MinIO local afin de ne pas dépendre d'AWS S3.

**Why this priority**: Le stockage est critique pour l'autonomie complète
de la plateforme self-hosted.

**Independent Test**: Uploader un fichier depuis un site tenant et vérifier
qu'il est stocké dans MinIO via la console MinIO.

**Acceptance Scenarios**:

1. **Given** MinIO configuré et connecté à Press, **When** un utilisateur uploade
   un fichier, **Then** le fichier apparaît dans le bucket MinIO correspondant

2. **Given** un backup planifié, **When** le backup s'exécute,
   **Then** les fichiers de backup sont stockés dans MinIO

3. **Given** un fichier stocké dans MinIO, **When** un utilisateur demande
   le téléchargement, **Then** le fichier est servi correctement

---

### User Story 4 - Routage et SSL avec Traefik (Priority: P1)

En tant qu'administrateur, je veux que Traefik gère le routage multi-tenant
et les certificats SSL afin d'avoir une gestion centralisée du trafic.

**Why this priority**: Le reverse proxy est essentiel pour le multi-tenancy
et la sécurité HTTPS.

**Independent Test**: Accéder à plusieurs sites tenants via leurs domaines
respectifs avec HTTPS valide.

**Acceptance Scenarios**:

1. **Given** Traefik configuré, **When** un nouveau site est créé,
   **Then** Traefik route automatiquement le trafic vers le bon conteneur

2. **Given** un domaine configuré, **When** j'accède au site,
   **Then** un certificat SSL valide est présenté

3. **Given** plusieurs sites actifs, **When** j'accède à chaque site,
   **Then** chaque site répond correctement sans interférence

---

### User Story 5 - Monitoring et Observabilité (Priority: P2)

En tant qu'administrateur, je veux surveiller l'état de la plateforme
via un dashboard centralisé afin de détecter et résoudre les problèmes rapidement.

**Why this priority**: L'observabilité est importante mais la plateforme
peut fonctionner initialement sans monitoring avancé.

**Independent Test**: Accéder au dashboard Wazuh/Grafana et voir les métriques
de tous les conteneurs.

**Acceptance Scenarios**:

1. **Given** Wazuh/Prometheus/Grafana déployés, **When** j'accède au dashboard,
   **Then** je vois les métriques CPU/RAM/Disk de tous les services

2. **Given** une alerte configurée, **When** un seuil est dépassé,
   **Then** une notification est envoyée

3. **Given** des logs collectés, **When** je recherche un événement,
   **Then** je trouve les logs pertinents avec contexte

---

### User Story 6 - Administration Centralisée UI (Priority: P2)

En tant qu'administrateur, je veux gérer toute la plateforme depuis une interface
web unifiée afin de ne pas avoir besoin d'accès SSH pour les opérations courantes.

**Why this priority**: Améliore l'expérience d'administration mais les
opérations peuvent être faites en CLI initialement.

**Independent Test**: Effectuer toutes les opérations d'administration
(créer site, backup, restart) depuis le dashboard sans SSH.

**Acceptance Scenarios**:

1. **Given** un administrateur connecté, **When** je navigue dans le dashboard,
   **Then** je peux voir tous les serveurs, sites et leur état

2. **Given** un site actif, **When** je clique sur "Backup",
   **Then** un backup est déclenché et visible dans l'historique

3. **Given** un site problématique, **When** je clique sur "Restart",
   **Then** le site redémarre et revient en ligne

---

### User Story 7 - Gestion DNS Locale (Priority: P3)

En tant qu'administrateur, je veux gérer les entrées DNS localement
afin de ne pas dépendre de Route53 ou autre DNS externe.

**Why this priority**: Le DNS local est un nice-to-have, le système
peut fonctionner avec des entrées /etc/hosts ou DNS externe initialement.

**Independent Test**: Créer une entrée DNS via l'UI et vérifier
la résolution depuis un client.

**Acceptance Scenarios**:

1. **Given** PowerDNS configuré, **When** un nouveau site est créé,
   **Then** une entrée DNS est automatiquement ajoutée

2. **Given** une entrée DNS existante, **When** je la modifie via UI,
   **Then** la modification est effective immédiatement

---

### Edge Cases

- Que se passe-t-il si MinIO est indisponible pendant un upload ?
  → Le système doit afficher un message d'erreur clair et retenter automatiquement

- Comment gérer la création de site si le quota de stockage est atteint ?
  → Afficher une alerte et bloquer la création avec message explicatif

- Que faire si un certificat SSL expire et ne peut être renouvelé ?
  → Envoyer une alerte 30 jours avant expiration, fallback sur certificat auto-signé

- Comment gérer la perte de connexion au registry Docker pendant un déploiement ?
  → Utiliser les images cachées localement, alerter l'administrateur

---

## Requirements *(mandatory)*

### Functional Requirements

#### Infrastructure Core

- **FR-001**: Le système DOIT pouvoir être déployé sur Docker ou Podman
- **FR-002**: Le système DOIT utiliser le préfixe `erp-saas-cloud-c16-` pour tous les conteneurs
- **FR-003**: Le système DOIT utiliser uniquement les ports 32300-32500
- **FR-004**: Le système DOIT être compatible avec Frappe Framework v16 (branche develop)

#### Multi-Tenancy

- **FR-005**: Le système DOIT permettre la création de sites tenants isolés
- **FR-006**: Chaque tenant DOIT avoir sa propre base de données
- **FR-007**: Les fichiers de chaque tenant DOIVENT être isolés dans MinIO
- **FR-008**: Le système DOIT supporter au minimum 50 sites tenants simultanés

#### Stockage

- **FR-009**: Le système DOIT utiliser MinIO comme backend de stockage S3
- **FR-010**: Tous les backups DOIVENT être stockés dans MinIO
- **FR-011**: Le système DOIT supporter les presigned URLs pour le streaming
- **FR-012**: L'intégration DOIT utiliser frappe/storage_integration ou dfp_external_storage

#### Reverse Proxy & SSL

- **FR-013**: Traefik DOIT gérer tout le routage HTTP/HTTPS
- **FR-014**: Les certificats SSL DOIVENT être générés automatiquement (Let's Encrypt ou CA locale)
- **FR-015**: Le système DOIT supporter le routage wildcard (*.domaine.local)
- **FR-016**: Traefik DOIT exposer uniquement les ports 80 et 443

#### Observabilité

- **FR-017**: Le système DOIT collecter les métriques de tous les conteneurs
- **FR-018**: Le système DOIT centraliser les logs de tous les services
- **FR-019**: Le système DOIT permettre la définition d'alertes personnalisées
- **FR-020**: Un dashboard DOIT présenter l'état de santé global

#### Administration UI

- **FR-021**: Toutes les opérations d'administration DOIVENT être possibles via UI
- **FR-022**: Le dashboard DOIT afficher l'état en temps réel des services
- **FR-023**: Le système DOIT permettre les backups/restores depuis l'UI
- **FR-024**: Le système DOIT afficher les logs depuis l'UI

### Key Entities

- **Cluster**: Groupe de serveurs gérant un ensemble de sites
- **Server**: Machine physique ou virtuelle (Proxy, App, Database)
- **Bench**: Environnement d'exécution Frappe avec un ensemble d'apps
- **Site**: Instance tenant avec sa propre base de données et fichiers
- **Release Group**: Ensemble de versions d'apps déployables
- **Backup**: Sauvegarde d'un site (database + files)
- **TLS Certificate**: Certificat SSL pour un domaine

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un administrateur peut déployer la plateforme complète en moins de 30 minutes
- **SC-002**: La création d'un nouveau site tenant prend moins de 5 minutes
- **SC-003**: Le système supporte 50 sites tenants actifs simultanément sans dégradation
- **SC-004**: Le temps de réponse des pages est inférieur à 3 secondes (p95)
- **SC-005**: Les backups automatiques s'exécutent avec 99.9% de succès
- **SC-006**: Le système atteint 99.5% de disponibilité mensuelle
- **SC-007**: 100% des opérations d'administration sont possibles via UI
- **SC-008**: Aucune dépendance à un service cloud externe n'est requise

---

## Assumptions

Les hypothèses suivantes ont été faites en l'absence de spécifications explicites :

1. **Environnement cible**: Linux (Ubuntu 22.04+) avec Docker 24+ ou Podman 4+
2. **Ressources minimales**: 8 CPU, 16GB RAM, 200GB SSD pour la plateforme
3. **Mode réseau**: Les sites seront accessibles via sous-domaines (site1.platform.local)
4. **Certificats SSL**: Let's Encrypt pour production, mkcert pour développement local
5. **Authentification**: L'authentification Frappe standard sera utilisée (email/password)
6. **Billing**: Le module billing Stripe sera désactivé initialement
7. **Email**: Mailhog pour dev, Postal pour production (configuration ultérieure)
8. **DNS externe**: Les utilisateurs configureront leur DNS externe pour pointer vers la plateforme

---

## Constitution Alignment *(mandatory)*

### Testing Requirements (Principle I & IV)

- [x] TDD approach defined (tests written BEFORE implementation)
- [x] Unit tests coverage target: ≥80%
- [x] Integration tests for service interactions
- [x] E2E tests for critical user journeys (création site, backup, etc.)

### Performance Requirements (Principle VI)

- [x] Page load time target: <3s FCP
- [x] API response time target: <500ms p95
- [x] Pagination for lists >100 items

### Security Requirements (Principle VII)

- [x] Input validation defined
- [x] Authentication/Authorization requirements (Frappe built-in)
- [x] No hardcoded secrets (environment variables via .env)
- [x] OWASP compliance verified

### UX Requirements (Principle V)

- [x] Frappe UI components used
- [x] WCAG 2.1 AA accessibility (Frappe built-in)
- [x] Responsive design (mobile-first) - Press Dashboard
- [x] i18n ready (Frappe built-in)

---

## Technical Research References

### Documentation Officielle

- [Frappe Press Repository](https://github.com/frappe/press)
- [Frappe Docker](https://github.com/frappe/frappe_docker)
- [Press Local Setup Guide](https://docs.frappe.io/cloud/local-fc-setup)
- [Frappe Framework v16](https://github.com/frappe/frappe/releases/tag/v16.0.0-beta.1)

### Solutions d'Intégration

- [Storage Integration](https://github.com/frappe/storage_integration)
- [DFP External Storage](https://github.com/developmentforpeople/dfp_external_storage)
- [Wazuh Docker](https://github.com/wazuh/wazuh-docker)
- [MinIO Docker](https://github.com/minio/minio)

### Guides de Référence

- [Traefik avec Frappe](https://github.com/frappe/frappe_docker/blob/main/docs/single-server-example.md)
- [Podman avec Frappe](https://github.com/frappe/frappe_docker/blob/main/docs/custom-apps-podman.md)
- [Self-hosting avec Dokploy](https://frappe.io/blog/tutorial/self-hosting-frappe-erpnext-apps-with-dokploy)
Renommer le dossier tracked en minuscule et conserver 