# Research: Plateforme Cloud SaaS Self-Hosted

**Feature**: `001-press-saas-selfhosted`
**Date**: 2025-12-20
**Status**: Complete

## Executive Summary

Cette recherche consolide les decisions techniques pour deployer Frappe Press v16
en mode self-hosted complet, sans dependances cloud externes.

---

## 1. Platform Base: Frappe Press

### Decision: Utiliser frappe/press (branche develop)

**Rationale**:
- Solution officielle Frappe pour le cloud hosting multi-tenant
- Architecture complete : gestion sites, benches, backups, billing
- Licence AGPL-3.0 permettant les modifications
- Actif : 17,173 commits, 142 contributeurs

**Alternatives Considered**:

| Alternative | Rejete car |
|-------------|-----------|
| frappe_docker seul | Pas de gestion multi-tenant avancee |
| Custom from scratch | Violation Constitution (reutilisation) |
| ERPNext Cloud | Non open-source |

**Source**: https://github.com/frappe/press

---

## 2. Container Orchestration

### Decision: Docker Compose avec support Podman

**Rationale**:
- Docker Compose est le standard documente par frappe_docker
- Podman compose disponible en fallback (podman-compose wrapper)
- Support rootless pour securite accrue avec Podman

**Contraintes Constitution**:
- Prefixe conteneurs: erp-saas-cloud-c16-*
- Ports: 32300-32500 uniquement

**Port Allocation Plan**:

| Service | Port | Usage |
|---------|------|-------|
| Traefik HTTP | 32380 | Redirect to HTTPS |
| Traefik HTTPS | 32443 | Main entry point |
| Traefik Dashboard | 32381 | Admin UI |
| Press Backend | 32300 | Internal only |
| MariaDB | 32306 | Database |
| Redis Cache | 32379 | Cache |
| Redis Queue | 32378 | Background jobs |
| MinIO API | 32390 | S3 API |
| MinIO Console | 32391 | Web UI |
| Prometheus | 32392 | Metrics |
| Grafana | 32393 | Dashboards |
| Wazuh Dashboard | 32394 | Security |

**Source**: https://github.com/frappe/frappe_docker/blob/main/docs/custom-apps-podman.md

---

## 3. Storage: MinIO Integration

### Decision: MinIO avec frappe/storage_integration

**Rationale**:
- MinIO est 100% compatible S3 API
- frappe/storage_integration est app officielle Frappe
- Supporte presigned URLs pour streaming
- Configuration via site_config ou common_site_config

**Configuration MinIO** (exemple):

```
common_site_config.json:
  s3_bucket: erp-saas-cloud-c16-files
  s3_endpoint_url: http://erp-saas-cloud-c16-minio:9000
  s3_access_key_id: from environment
  s3_secret_access_key: from environment
  s3_region: us-east-1
  s3_force_path_style: true
```

**Buckets Structure**:

| Bucket | Purpose |
|--------|---------|
| erp-saas-cloud-c16-files | Attachments, uploads |
| erp-saas-cloud-c16-backups | Site backups |
| erp-saas-cloud-c16-private | Private files |
| erp-saas-cloud-c16-logs | Archived logs |

**Source**: https://github.com/frappe/storage_integration

---

## 4. Reverse Proxy: Traefik v3

### Decision: Traefik v3 avec Let's Encrypt

**Rationale**:
- Recommande par frappe_docker single-server guide
- Auto-discovery des conteneurs Docker
- Gestion automatique SSL via Let's Encrypt
- Pas de base de donnees additionnelle (vs Nginx Proxy Manager)

**Configuration Pattern** (traefik.yml static):

```
api:
  dashboard: true
entryPoints:
  web:
    address: :32380
    http:
      redirections:
        entryPoint:
          to: websecure
  websecure:
    address: :32443
certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@example.com
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web
providers:
  docker:
    exposedByDefault: false
  file:
    directory: /etc/traefik/dynamic
```

**Dev Mode**: Utiliser mkcert pour certificats locaux.

**Source**: https://github.com/frappe/frappe_docker/blob/main/docs/single-server-example.md

---

## 5. Monitoring Stack

### Decision: Prometheus + Grafana + Wazuh

**Rationale**:
- Prometheus: metriques standard, integration Docker native
- Grafana: dashboards visuels, alerting
- Wazuh: SIEM complet, security monitoring, compliance

**Stack Components**:

| Component | Role | Port |
|-----------|------|------|
| Prometheus | Metrics collection | 32392 |
| Grafana | Visualization | 32393 |
| Wazuh Manager | SIEM engine | Internal |
| Wazuh Dashboard | Security UI | 32394 |
| Node Exporter | Host metrics | Internal |
| cAdvisor | Container metrics | Internal |

**Wazuh Requirement**: vm.max_map_count >= 262144

**Grafana Dashboards**:
- Docker Container Metrics (ID: 893)
- Frappe Application Metrics (custom)
- MariaDB Overview (ID: 7362)
- Redis Dashboard (ID: 763)

**Source**: https://github.com/wazuh/wazuh-docker

---

## 6. Press Agent Adaptation

### Decision: Agent containerise avec Docker socket

**Rationale**:
- Agent Press communique avec les benches via CLI
- En mode containerise, acces au Docker socket requis
- Configuration via variables environnement

**Challenge Identifie**:
Press Agent est concu pour SSH vers des VMs. En mode full-container,
agent doit communiquer avec les conteneurs via Docker API.

**Adaptation Proposee**:
Creer override dans press_selfhosted/overrides/agent.py
Remplacer SSH commands par docker commands

**Risque**: Modification significative du comportement Press.
**Mitigation**: Tests E2E exhaustifs, monitoring des commandes.

---

## 7. Docker Registry Local

### Decision: Docker Registry v2 (simple) ou Harbor (enterprise)

**Rationale**:
- Press construit des images custom pour chaque Release Group
- Registry local evite dependance DigitalOcean/DockerHub
- Harbor offre UI et scanning de vulnerabilites

**Press Configuration**:
- docker_registry_url: localhost:32395
- docker_registry_namespace: erp-saas-cloud-c16

---

## 8. Email Service

### Decision: Mailhog (dev) / Postal (prod)

**Rationale**:
- Mailhog capture tous les emails en dev (pas envoi reel)
- Postal est un serveur mail open-source complet pour prod

**Ports**:
- SMTP: 32325
- Web UI: 32326

---

## 9. DNS Management

### Decision: Configuration manuelle initiale, PowerDNS optionnel (P3)

**Rationale**:
- DNS local pas critique pour MVP
- /etc/hosts ou DNS externe suffisent initialement
- PowerDNS peut etre ajoute en P3 pour automation

---

## 10. Frappe v16 Compatibility

### Decision: Utiliser branche develop

**Rationale**:
- v16 beta sortie prevue 1er juin 2025
- Branche develop contient les features v16
- Press supporte Frappe v16 (meme repo)

**Source**: https://discuss.frappe.io/t/version-16-release-plan/142686

---

## Summary of Decisions

| Component | Decision | Risk Level |
|-----------|----------|------------|
| Platform | frappe/press develop | Low |
| Containers | Docker + Podman fallback | Low |
| Storage | MinIO + storage_integration | Low |
| Reverse Proxy | Traefik v3 | Low |
| Monitoring | Prometheus + Grafana + Wazuh | Low |
| Agent | Custom Docker adapter | Medium |
| Registry | Docker Registry v2 | Low |
| Email | Mailhog (dev) / Postal (prod) | Low |
| DNS | Manual (P3: PowerDNS) | Low |
| Frappe | v16 develop branch | Medium |

---

## Open Questions Resolved

1. **Q: Comment Agent Press communique-t-il sans SSH?**
   A: Via Docker socket et docker, necessite une adaptation custom.

2. **Q: MinIO est-il compatible avec storage_integration?**
   A: Oui, via s3_force_path_style=true et s3_endpoint_url custom.

3. **Q: Traefik peut-il gerer wildcard SSL?**
   A: Oui, avec DNS challenge (requiert DNS API) ou certificat wildcard manuel.

4. **Q: Podman est-il vraiment compatible?**
   A: Oui avec podman-compose, mais attention au .env file issue.
