# Implementation Plan: Plateforme Cloud SaaS Self-Hosted

**Branch**: `001-press-saas-selfhosted` | **Date**: 2025-12-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-press-saas-selfhosted/spec.md`

## Summary

Déploiement d'une plateforme Cloud SaaS multi-tenant entièrement self-hosted basée sur
**Frappe Press v16**, remplaçant tous les providers cloud externes par des alternatives
open-source locales :

- **Stockage**: MinIO (remplace AWS S3)
- **Reverse Proxy**: Traefik (remplace Cloudflare)
- **Monitoring**: Wazuh + Prometheus/Grafana
- **Registry**: Harbor ou Docker Registry local
- **Infrastructure**: Docker/Podman (remplace Hetzner/DigitalOcean)

L'approche privilégie la réutilisation maximale des solutions officielles Frappe
(frappe/press, frappe/frappe_docker, frappe/storage_integration) avec adaptation
minimale pour l'environnement containerisé local.

## Technical Context

**Language/Version**: Python 3.11+ (Frappe Framework), Node.js 18+ (frontend)
**Primary Dependencies**: Frappe Framework v16 (develop), Frappe Press, Frappe UI (Vue.js)
**Storage**: MariaDB 10.6+ (database), Redis 7.0+ (cache/queues), MinIO (S3-compatible)
**Testing**: pytest (Python), Jest/Cypress (JavaScript), bench test framework
**Target Platform**: Linux server (Ubuntu 22.04+), Docker 24+ ou Podman 4+
**Project Type**: Infrastructure + Web application (multi-container orchestration)
**Performance Goals**: 50 sites tenants simultanés, <3s FCP, <500ms API p95
**Constraints**: Ports 32300-32500 uniquement, préfixe `erp-saas-cloud-c16-*`
**Scale/Scope**: 50 sites tenants minimum, 99.5% uptime mensuel

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
| --------- | ------ | ----- |
| I. TDD-First | ✅ | Tests écrits AVANT implémentation - pytest + bench test |
| II. Documentation Officielle | ✅ | Basé sur docs officielles Frappe Press, frappe_docker |
| III. Code Quality | ✅ | Code review obligatoire, PEP 8, ESLint Frappe |
| IV. Testing Complete | ✅ | Unit + Integration + E2E planifiés (pyramide tests) |
| V. UX Consistency | ✅ | Frappe UI natif, Press Dashboard existant |
| VI. Performance | ✅ | Métriques définies: <3s FCP, <500ms p95, pagination |
| VII. Security | ✅ | OWASP, secrets via .env, Frappe auth built-in |
| VIII. Verification | ✅ | Double-check, tests E2E, validation use cases |

**Infrastructure Constraints**:
- [x] Container prefix: `erp-saas-cloud-c16-*`
- [x] Port range: 32300-32500 (no default ports)
- [x] Frappe v16 compatibility verified (develop branch)

## Project Structure

### Documentation (this feature)

```text
specs/001-press-saas-selfhosted/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: Technical research
├── data-model.md        # Phase 1: Entity relationships
├── quickstart.md        # Phase 1: Getting started guide
├── contracts/           # Phase 1: API contracts
│   ├── press-api.yaml   # Press REST API (OpenAPI)
│   └── site-api.yaml    # Site management API
├── checklists/          # Quality validation
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2: Implementation tasks
```

### Source Code (repository root)

```text
# Infrastructure orchestration (Docker/Podman)
docker/
├── compose/
│   ├── docker-compose.yml           # Main orchestration
│   ├── docker-compose.override.yml  # Dev overrides
│   ├── docker-compose.prod.yml      # Production config
│   └── services/
│       ├── press.yml                # Press service
│       ├── traefik.yml              # Reverse proxy
│       ├── minio.yml                # Object storage
│       ├── mariadb.yml              # Database
│       ├── redis.yml                # Cache/queues
│       └── monitoring.yml           # Wazuh/Prometheus/Grafana
├── images/
│   ├── press/
│   │   └── Dockerfile               # Press custom image
│   └── agent/
│       └── Dockerfile               # Agent custom image
└── config/
    ├── traefik/
    │   ├── traefik.yml              # Static config
    │   └── dynamic/                 # Dynamic routing
    ├── minio/
    │   └── policies/                # Bucket policies
    └── monitoring/
        ├── prometheus.yml
        └── grafana/

# Press customizations (minimal - prefer upstream)
apps/
└── press_selfhosted/                # Custom Press adaptations
    ├── press_selfhosted/
    │   ├── __init__.py
    │   ├── hooks.py
    │   ├── overrides/               # Override Press behaviors
    │   └── integrations/
    │       ├── minio.py             # MinIO integration
    │       └── local_registry.py    # Local Docker registry
    └── tests/
        ├── unit/
        ├── integration/
        └── e2e/

# Configuration
config/
├── .env.example                     # Environment template
├── ports.yaml                       # Port allocation registry
└── secrets/                         # Secrets (gitignored)
```

**Structure Decision**: Infrastructure-first approach avec orchestration Docker/Podman.
Le code custom est minimisé - on utilise frappe/press upstream avec une app
d'adaptation légère (`press_selfhosted`) pour les intégrations locales.

## Complexity Tracking

> **No violations detected - Constitution Check passed**

| Aspect | Justification |
|--------|---------------|
| Multi-container architecture | Requis par Press (multiple services) |
| Custom app (press_selfhosted) | Minimisé - uniquement pour adaptations MinIO/local registry |
| Multiple compose files | Standard pour dev/prod separation |

---

## Phase 0: Research Summary

Voir [research.md](./research.md) pour les détails complets.

### Décisions Clés

| Sujet | Décision | Justification |
|-------|----------|---------------|
| Base Platform | frappe/press (develop branch) | Solution officielle complète |
| Docker Images | frappe/frappe_docker patterns | Patterns officiels testés |
| S3 Integration | frappe/storage_integration | App officielle Frappe |
| Reverse Proxy | Traefik v3 | Recommandé par frappe_docker |
| SSL Certificates | Let's Encrypt (prod) / mkcert (dev) | Standard industry |
| Monitoring | Prometheus + Grafana + Wazuh | Stack complète open-source |
| Container Runtime | Docker avec fallback Podman | Compatibilité maximale |

---

## Phase 1: Design Artifacts

### Data Model

Voir [data-model.md](./data-model.md) - Entités Press existantes + extensions locales.

### API Contracts

Voir [contracts/](./contracts/) - OpenAPI specs pour APIs Press et intégrations.

### Quickstart Guide

Voir [quickstart.md](./quickstart.md) - Guide de démarrage rapide (<30 min).

---

## Constitution Check - Final Validation (Post-Design)

*Re-evaluation après Phase 1 design - 2025-12-20*

| Principle | Status | Validation |
| --------- | ------ | ---------- |
| I. TDD-First | ✅ PASS | Structure tests/ définie dans project structure |
| II. Documentation Officielle | ✅ PASS | research.md référence uniquement sources officielles |
| III. Code Quality | ✅ PASS | PEP 8, ESLint, code review mandatoires |
| IV. Testing Complete | ✅ PASS | Pyramide tests: unit/, integration/, e2e/ planifiée |
| V. UX Consistency | ✅ PASS | Frappe UI natif, Press Dashboard existant |
| VI. Performance | ✅ PASS | Métriques <3s FCP, <500ms p95 dans Technical Context |
| VII. Security | ✅ PASS | OWASP, secrets via .env, no hardcoded credentials |
| VIII. Verification | ✅ PASS | Double-check process documenté |

**Infrastructure Constraints - Final Check**:
- [x] Container prefix: `erp-saas-cloud-c16-*` (verified in research.md)
- [x] Port range: 32300-32500 (port allocation plan in research.md)
- [x] Frappe v16 (develop) compatibility (verified)

---

## Next Steps

1. **Phase 0 Complete** ✅ research.md généré avec résolutions techniques
2. **Phase 1 Complete** ✅ data-model.md, contracts/, quickstart.md générés
3. **Agent Context Updated** ✅ CLAUDE.md mis à jour avec contexte projet
4. **Constitution Validated** ✅ All 8 principles verified post-design
5. **Phase 2**: Exécuter `/speckit.tasks` pour générer les tâches d'implémentation
