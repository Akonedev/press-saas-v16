# Data Model: Plateforme Cloud SaaS Self-Hosted

**Feature**: `001-press-saas-selfhosted`
**Date**: 2025-12-20

## Overview

Ce document decrit les entites du systeme Press et leurs relations.
Les entites proviennent principalement de frappe/press avec des extensions
pour le mode self-hosted.

---

## Core Entities (from frappe/press)

### Cluster

Groupe logique de serveurs gerant un ensemble de sites.

| Field | Type | Description |
|-------|------|-------------|
| name | String | Identifiant unique (ex: "default") |
| title | String | Nom affichable |
| region | String | Region geographique |
| enabled | Boolean | Cluster actif ou non |

**Relations**:
- Has many: Server, Bench, Site

---

### Server

Machine physique ou virtuelle hebergeant des benches.

| Field | Type | Description |
|-------|------|-------------|
| name | String | Hostname (ex: "f1", "n1", "m1") |
| hostname | String | FQDN |
| ip | String | IP publique |
| private_ip | String | IP privee (reseau interne) |
| server_type | Enum | proxy, app, database |
| status | Enum | pending, active, maintenance |
| cluster | Link | Reference au Cluster |

**Server Types**:
- **Proxy (n)**: Traefik, gere le routage
- **App (f)**: Benches et sites Frappe
- **Database (m)**: MariaDB instances

**Self-Hosted Extension**:
En mode containerise, les "servers" sont des groupes de conteneurs
plutot que des VMs. Le champ `container_prefix` est ajoute.

| Field | Type | Description |
|-------|------|-------------|
| container_prefix | String | Prefixe Docker (ex: "erp-saas-cloud-c16") |
| docker_socket | String | Path au socket Docker |

---

### Bench

Environnement d'execution Frappe avec un ensemble d'applications.

| Field | Type | Description |
|-------|------|-------------|
| name | String | Identifiant unique |
| server | Link | Reference au Server (app) |
| status | Enum | pending, active, broken |
| group | Link | Reference au Release Group |
| apps | Table | Liste des apps installees |

**Relations**:
- Belongs to: Server, Release Group
- Has many: Site

---

### Site

Instance tenant avec sa propre base de donnees et fichiers.

| Field | Type | Description |
|-------|------|-------------|
| name | String | Nom du site (ex: "site1.platform.local") |
| bench | Link | Reference au Bench |
| status | Enum | pending, active, suspended, archived |
| database | Link | Reference a la Database |
| admin_password | Password | Mot de passe admin (encrypted) |
| plan | Link | Reference au Site Plan |

**Relations**:
- Belongs to: Bench
- Has one: Database
- Has many: Backup, SiteApp

---

### Release Group

Ensemble de versions d'applications deployables.

| Field | Type | Description |
|-------|------|-------------|
| name | String | Identifiant unique |
| title | String | Nom affichable |
| public | Boolean | Visible pour tous les utilisateurs |
| servers | Table | Serveurs ou deployer |
| apps | Table | Apps et leurs versions |

**Relations**:
- Has many: Bench, Deploy Candidate

---

### Deploy Candidate

Build candidat pour deploiement.

| Field | Type | Description |
|-------|------|-------------|
| name | String | Identifiant unique |
| group | Link | Reference au Release Group |
| status | Enum | draft, pending, running, success, failure |
| docker_image | String | Image Docker construite |
| docker_image_tag | String | Tag de l'image |

---

### App Source

Source d'une application Frappe.

| Field | Type | Description |
|-------|------|-------------|
| name | String | Identifiant unique |
| app | Link | Reference a l'App |
| repository_url | String | URL Git du repo |
| branch | String | Branche Git |
| version | String | Version (tag ou commit) |

---

### Backup

Sauvegarde d'un site.

| Field | Type | Description |
|-------|------|-------------|
| name | String | Identifiant unique |
| site | Link | Reference au Site |
| status | Enum | pending, running, success, failure |
| database_file | String | Path fichier DB dans MinIO |
| files_backup | String | Path fichier files dans MinIO |
| private_backup | String | Path fichier private dans MinIO |
| size | Int | Taille totale en bytes |

**Self-Hosted Extension**:

| Field | Type | Description |
|-------|------|-------------|
| minio_bucket | String | Bucket MinIO utilise |
| minio_prefix | String | Prefixe dans le bucket |

---

### TLS Certificate

Certificat SSL pour un domaine.

| Field | Type | Description |
|-------|------|-------------|
| name | String | Domaine (ex: "*.platform.local") |
| status | Enum | pending, active, expired |
| issuer | String | Let's Encrypt ou CA locale |
| expires | Datetime | Date d'expiration |
| certificate | Text | Contenu du certificat (PEM) |
| private_key | Text | Cle privee (encrypted) |

---

### Site Plan

Plan tarifaire pour les sites.

| Field | Type | Description |
|-------|------|-------------|
| name | String | Identifiant unique |
| title | String | Nom affichable (ex: "Free", "Pro") |
| price | Currency | Prix mensuel |
| max_storage | Int | Stockage max en GB |
| max_users | Int | Nombre max d'utilisateurs |
| features | Table | Liste des features incluses |

---

## Self-Hosted Extensions

### Storage Configuration

Configuration MinIO pour le stockage S3.

| Field | Type | Description |
|-------|------|-------------|
| name | String | Identifiant unique |
| endpoint_url | String | URL MinIO |
| access_key | Password | Access key (encrypted) |
| secret_key | Password | Secret key (encrypted) |
| default_bucket | String | Bucket par defaut |
| region | String | Region (default: us-east-1) |

---

### Local Registry

Configuration du registry Docker local.

| Field | Type | Description |
|-------|------|-------------|
| name | String | Identifiant unique |
| url | String | URL du registry |
| namespace | String | Namespace pour les images |
| username | String | Username (optionnel) |
| password | Password | Password (optionnel, encrypted) |

---

## Entity Relationships Diagram

```
                    ┌─────────────┐
                    │   Cluster   │
                    └──────┬──────┘
                           │ 1:N
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │  Proxy   │    │   App    │    │ Database │
    │  Server  │    │  Server  │    │  Server  │
    └──────────┘    └────┬─────┘    └──────────┘
                         │ 1:N
                         ▼
                  ┌──────────────┐
                  │    Bench     │◄────────┐
                  └──────┬───────┘         │
                         │ 1:N             │ N:1
                         ▼                 │
                  ┌──────────────┐   ┌─────────────┐
                  │     Site     │   │Release Group│
                  └──────┬───────┘   └─────────────┘
                         │ 1:N             │ 1:N
           ┌─────────────┼─────────────┐   │
           ▼             ▼             ▼   ▼
    ┌──────────┐  ┌──────────┐  ┌─────────────────┐
    │  Backup  │  │ SiteApp  │  │Deploy Candidate │
    └──────────┘  └──────────┘  └─────────────────┘
```

---

## State Transitions

### Site Lifecycle

```
pending → installing → active → suspended → archived
                  ↓         ↓
               broken    broken
```

### Backup Lifecycle

```
pending → running → success
              ↓
           failure
```

### Deploy Candidate Lifecycle

```
draft → pending → running → success
                     ↓
                  failure
```

---

## Validation Rules

### Site

- `name` doit etre un FQDN valide
- `name` doit etre unique dans le systeme
- `bench` doit etre actif
- `plan` doit etre defini

### Backup

- `site` doit exister et etre actif ou suspended
- `database_file` doit pointer vers un fichier valide dans MinIO

### Server

- `ip` doit etre une IP valide
- `private_ip` doit etre dans le reseau interne
- `container_prefix` doit correspondre au pattern Constitution

---

## Indexes Recommandes

| Entity | Field(s) | Type |
|--------|----------|------|
| Site | name | Unique |
| Site | status | Index |
| Backup | site, creation | Composite |
| Server | cluster, status | Composite |
| Bench | server, status | Composite |
