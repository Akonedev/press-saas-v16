# Tasks: Plateforme Cloud SaaS Self-Hosted

**Input**: Design documents from `/specs/001-press-saas-selfhosted/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/
**Generated**: 2025-12-20

**Tests**: Per Constitution Principle I (TDD-First), tests are MANDATORY and MUST be written BEFORE implementation. Coverage target: ≥80%.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Constitution Compliance

Per `.specify/memory/constitution.md`, all tasks MUST follow:

| Principle | Task Requirement |
| --------- | ---------------- |
| I. TDD-First | Tests BEFORE code (Red-Green-Refactor) |
| II. Documentation | Verify Frappe v16 official docs |
| III. Code Quality | Code review after implementation |
| IV. Testing | Unit + Integration + E2E |
| VI. Performance | No N+1 queries, pagination |
| VII. Security | OWASP compliance, no hardcoded secrets |
| VIII. Verification | Double-check before marking complete |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## User Stories Summary

| Story | Title | Priority | Status |
|-------|-------|----------|--------|
| US1 | Déploiement Initial de la Plateforme | P1 | MVP |
| US2 | Création d'un Site Tenant | P1 | MVP |
| US3 | Stockage sur MinIO | P1 | MVP |
| US4 | Routage et SSL avec Traefik | P1 | MVP |
| US5 | Monitoring et Observabilité | P2 | Post-MVP |
| US6 | Administration Centralisée UI | P2 | Post-MVP |
| US7 | Gestion DNS Locale | P3 | Future |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory structure per plan.md (docker/, apps/, config/)
- [x] T002 [P] Create config/.env.example with all environment variables
- [x] T003 [P] Create config/ports.yaml with port allocation registry (32300-32500)
- [x] T004 [P] Initialize apps/press_selfhosted/ as Frappe app skeleton
- [x] T005 [P] Create .gitignore with secrets, volumes, build artifacts exclusions
- [x] T006 [P] Create docker/.dockerignore for build optimization

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational Phase (MANDATORY - TDD First) 🔴

- [x] T007 [P] Create test for Docker Compose validation in apps/press_selfhosted/tests/unit/test_compose_validation.py
- [x] T008 [P] Create test for environment variable loading in apps/press_selfhosted/tests/unit/test_env_config.py
- [x] T009 [P] Create test for port range validation (32300-32500) in apps/press_selfhosted/tests/unit/test_port_allocation.py

### Implementation for Foundational Phase

- [x] T010 Create docker/compose/mariadb.yml with erp-saas-cloud-c16-mariadb container
- [x] T011 [P] Create docker/compose/redis.yml with erp-saas-cloud-c16-redis-cache and erp-saas-cloud-c16-redis-queue containers
- [x] T012 Create docker/images/press/Dockerfile based on frappe_docker patterns
- [x] T013 [P] Create docker/config/common_site_config.json template
- [x] T014 Create apps/press_selfhosted/press_selfhosted/__init__.py with app metadata
- [x] T015 [P] Create apps/press_selfhosted/press_selfhosted/hooks.py with app hooks
- [x] T016 Create apps/press_selfhosted/setup.py for app installation
- [x] T017 [P] Create validation script scripts/validate_container_names.sh for prefix check

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Déploiement Initial de la Plateforme (Priority: P1) 🎯 MVP

**Goal**: Déployer la plateforme Press complète sur infrastructure locale avec Docker/Podman

**Independent Test**: La plateforme peut être déployée avec `docker compose up` et affiche le dashboard Press accessible via navigateur

### Tests for User Story 1 (MANDATORY - TDD First) 🔴

> **CONSTITUTION PRINCIPLE I**: Write tests FIRST, ensure they FAIL (🔴 RED), then implement (🟢 GREEN)

- [x] T018 [P] [US1] Contract test for /health endpoint in apps/press_selfhosted/tests/contract/test_health_api.py
- [x] T019 [P] [US1] Integration test for container startup in apps/press_selfhosted/tests/integration/test_container_startup.py
- [x] T020 [P] [US1] E2E test for login page accessibility in apps/press_selfhosted/tests/e2e/test_login_page.py

### Implementation for User Story 1

- [x] T021 [US1] Create docker/compose/press.yml with erp-saas-cloud-c16-press main service
- [x] T022 [P] [US1] Create docker/compose/press-worker.yml with worker containers (short, long, scheduler)
- [x] T023 [US1] Create docker/compose/docker-compose.yml as main orchestrator including all services
- [x] T024 [P] [US1] Create docker/compose/docker-compose.override.yml for dev environment
- [x] T025 [US1] Create docker/config/press/sites/common_site_config.json with MariaDB/Redis connections
- [x] T026 [P] [US1] Create scripts/setup-press.sh for initial Press site creation
- [x] T027 [US1] Create quickstart validation script scripts/validate_quickstart.sh
- [x] T028 [US1] Implement health check endpoint in apps/press_selfhosted/press_selfhosted/api/health.py

**Checkpoint**: Platform deployment complete - Press dashboard accessible at https://press.platform.local:32443

---

## Phase 4: User Story 2 - Création d'un Site Tenant (Priority: P1) 🎯 MVP

**Goal**: Permettre la création de sites tenants isolés depuis l'interface Press

**Independent Test**: Créer un site "demo.local" depuis le dashboard et y accéder via navigateur

### Tests for User Story 2 (MANDATORY - TDD First) 🔴

- [x] T029 [P] [US2] Contract test for /method/press.api.site.new in apps/press_selfhosted/tests/contract/test_site_api.py
- [x] T030 [P] [US2] Contract test for /method/press.api.site.info in apps/press_selfhosted/tests/contract/test_site_info_api.py
- [x] T031 [P] [US2] Integration test for site creation workflow in apps/press_selfhosted/tests/integration/test_site_creation.py
- [x] T032 [P] [US2] E2E test for site access after creation in apps/press_selfhosted/tests/e2e/test_site_access.py

### Implementation for User Story 2

- [x] T033 [US2] Create apps/press_selfhosted/press_selfhosted/overrides/site.py for Site DocType extensions
- [x] T034 [P] [US2] Create apps/press_selfhosted/press_selfhosted/overrides/bench.py for Bench DocType extensions
- [x] T035 [US2] Implement local site provisioning in apps/press_selfhosted/press_selfhosted/services/site_provisioner.py
- [x] T036 [US2] Implement database creation for tenant in apps/press_selfhosted/press_selfhosted/services/database_manager.py
- [x] T037 [P] [US2] Create site isolation validation in apps/press_selfhosted/press_selfhosted/validators/site_isolation.py
- [x] T038 [US2] Implement site status tracking in apps/press_selfhosted/press_selfhosted/services/site_status.py

**Checkpoint**: Site creation works - new tenant sites can be created and accessed independently

---

## Phase 5: User Story 3 - Stockage sur MinIO (Priority: P1) 🎯 MVP

**Goal**: Configurer MinIO comme backend S3 pour tous les fichiers et backups

**Independent Test**: Uploader un fichier depuis un site tenant et vérifier qu'il est stocké dans MinIO

### Tests for User Story 3 (MANDATORY - TDD First) 🔴

- [x] T039 [P] [US3] Contract test for MinIO bucket operations in apps/press_selfhosted/tests/contract/test_minio_buckets.py
- [x] T040 [P] [US3] Contract test for MinIO object operations in apps/press_selfhosted/tests/contract/test_minio_objects.py
- [x] T041 [P] [US3] Integration test for file upload via Press in apps/press_selfhosted/tests/integration/test_file_upload.py
- [x] T042 [P] [US3] Integration test for backup storage in apps/press_selfhosted/tests/integration/test_backup_storage.py

### Implementation for User Story 3

- [x] T043 [US3] Create docker/compose/minio.yml with erp-saas-cloud-c16-minio container on port 32390
- [x] T044 [P] [US3] Create docker/config/minio/policies/default-policy.json for bucket access
- [x] T045 [US3] Create apps/press_selfhosted/press_selfhosted/integrations/minio.py for MinIO client wrapper
- [x] T046 [US3] Implement Storage Configuration DocType in apps/press_selfhosted/press_selfhosted/doctype/storage_configuration/
- [x] T047 [P] [US3] Create bucket initialization script scripts/init-minio-buckets.sh
- [x] T048 [US3] Configure storage_integration app settings in apps/press_selfhosted/press_selfhosted/setup/storage_setup.py
- [x] T049 [US3] Implement backup to MinIO in apps/press_selfhosted/press_selfhosted/overrides/backup.py
- [x] T050 [P] [US3] Create presigned URL generator in apps/press_selfhosted/press_selfhosted/services/presigned_urls.py

**Checkpoint**: MinIO integration complete - files and backups stored in local S3-compatible storage

---

## Phase 6: User Story 4 - Routage et SSL avec Traefik (Priority: P1) 🎯 MVP

**Goal**: Configurer Traefik pour le routage multi-tenant et la gestion SSL automatique

**Independent Test**: Accéder à plusieurs sites tenants via leurs domaines avec HTTPS valide

### Tests for User Story 4 (MANDATORY - TDD First) 🔴

- [x] T051 [P] [US4] Integration test for Traefik routing in apps/press_selfhosted/tests/integration/test_traefik_routing.py
- [x] T052 [P] [US4] Integration test for SSL certificate validation in apps/press_selfhosted/tests/integration/test_ssl_certificates.py
- [x] T053 [P] [US4] E2E test for multi-tenant access in apps/press_selfhosted/tests/e2e/test_multitenant_access.py

### Implementation for User Story 4

- [x] T054 [US4] Create docker/compose/traefik.yml with erp-saas-cloud-c16-traefik container on ports 32380/32443
- [x] T055 [P] [US4] Create docker/config/traefik/traefik.yml static configuration
- [x] T056 [US4] Create docker/config/traefik/dynamic/default.yml for default routing rules
- [x] T057 [P] [US4] Create docker/config/traefik/dynamic/press.yml for Press service routing
- [x] T058 [US4] Implement dynamic route generation in apps/press_selfhosted/press_selfhosted/services/route_manager.py
- [x] T059 [P] [US4] Create TLS Certificate DocType extension in apps/press_selfhosted/press_selfhosted/overrides/tls_certificate.py
- [x] T060 [US4] Create mkcert setup script for dev in scripts/setup-dev-certs.sh
- [x] T061 [P] [US4] Create Let's Encrypt configuration in docker/config/traefik/acme/

**Checkpoint**: Traefik routing complete - all sites accessible via HTTPS with valid certificates

---

## Phase 7: User Story 5 - Monitoring et Observabilité (Priority: P2)

**Goal**: Déployer stack de monitoring complet (Prometheus/Grafana/Wazuh)

**Independent Test**: Accéder au dashboard Grafana et voir les métriques de tous les conteneurs

### Tests for User Story 5 (MANDATORY - TDD First) 🔴

- [x] T062 [P] [US5] Integration test for Prometheus metrics collection in apps/press_selfhosted/tests/integration/test_prometheus_metrics.py
- [x] T063 [P] [US5] Integration test for Grafana dashboard access in apps/press_selfhosted/tests/integration/test_grafana_access.py
- [x] T064 [P] [US5] Integration test for log aggregation in apps/press_selfhosted/tests/integration/test_log_aggregation.py

### Implementation for User Story 5

- [x] T065 [US5] Create docker/compose/prometheus.yml with erp-saas-cloud-c16-prometheus on port 32392
- [x] T066 [P] [US5] Create docker/compose/grafana.yml with erp-saas-cloud-c16-grafana on port 32393
- [x] T067 [US5] Create docker/compose/wazuh.yml with erp-saas-cloud-c16-wazuh on port 32394
- [x] T068 [P] [US5] Create docker/config/monitoring/prometheus.yml with scrape configs
- [x] T069 [P] [US5] Create docker/config/monitoring/grafana/provisioning/datasources/
- [x] T070 [US5] Create docker/config/monitoring/grafana/provisioning/dashboards/ with Docker metrics dashboard
- [x] T071 [P] [US5] Create Frappe-specific dashboard in docker/config/monitoring/grafana/dashboards/frappe-metrics.json
- [x] T072 [US5] Create docker/compose/node-exporter.yml for host metrics
- [x] T073 [P] [US5] Create docker/compose/cadvisor.yml for container metrics
- [x] T074 [US5] Implement alert rules in docker/config/monitoring/alertmanager/

**Checkpoint**: Monitoring stack complete - all services visible in Grafana with alerting configured

---

## Phase 8: User Story 6 - Administration Centralisée UI (Priority: P2)

**Goal**: Permettre toutes les opérations d'administration via l'interface web Press

**Independent Test**: Effectuer toutes les opérations (créer site, backup, restart) depuis le dashboard sans SSH

### Tests for User Story 6 (MANDATORY - TDD First) 🔴

- [ ] T075 [P] [US6] Contract test for backup API in apps/press_selfhosted/tests/contract/test_backup_api.py
- [ ] T076 [P] [US6] Contract test for server status API in apps/press_selfhosted/tests/contract/test_server_api.py
- [ ] T077 [P] [US6] E2E test for backup workflow in apps/press_selfhosted/tests/e2e/test_backup_workflow.py
- [ ] T078 [P] [US6] E2E test for site restart workflow in apps/press_selfhosted/tests/e2e/test_site_restart.py

### Implementation for User Story 6

- [ ] T079 [US6] Extend Press dashboard for local operations in apps/press_selfhosted/press_selfhosted/overrides/server_dashboard.py
- [ ] T080 [P] [US6] Implement local backup trigger in apps/press_selfhosted/press_selfhosted/services/backup_service.py
- [ ] T081 [US6] Implement local site restart in apps/press_selfhosted/press_selfhosted/services/site_operations.py
- [ ] T082 [P] [US6] Create log viewer API in apps/press_selfhosted/press_selfhosted/api/logs.py
- [ ] T083 [US6] Implement Docker socket operations in apps/press_selfhosted/press_selfhosted/integrations/docker_client.py
- [ ] T084 [P] [US6] Create real-time status updates in apps/press_selfhosted/press_selfhosted/services/realtime_status.py

**Checkpoint**: Admin UI complete - all operations possible without SSH access

---

## Phase 9: User Story 7 - Gestion DNS Locale (Priority: P3)

**Goal**: Gérer les entrées DNS localement sans dépendance externe

**Independent Test**: Créer une entrée DNS via l'UI et vérifier la résolution depuis un client

### Tests for User Story 7 (MANDATORY - TDD First) 🔴

- [ ] T085 [P] [US7] Integration test for DNS record creation in apps/press_selfhosted/tests/integration/test_dns_records.py
- [ ] T086 [P] [US7] Integration test for DNS resolution in apps/press_selfhosted/tests/integration/test_dns_resolution.py

### Implementation for User Story 7

- [ ] T087 [US7] Create docker/compose/powerdns.yml with erp-saas-cloud-c16-powerdns container
- [ ] T088 [P] [US7] Create docker/config/powerdns/pdns.conf configuration
- [ ] T089 [US7] Implement DNS integration in apps/press_selfhosted/press_selfhosted/integrations/powerdns.py
- [ ] T090 [US7] Create Local Registry DocType in apps/press_selfhosted/press_selfhosted/doctype/local_dns_zone/
- [ ] T091 [P] [US7] Hook site creation to DNS in apps/press_selfhosted/press_selfhosted/hooks/dns_hooks.py

**Checkpoint**: DNS management complete - automatic DNS entries for new sites

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T092 [P] Documentation updates in specs/001-press-saas-selfhosted/docs/
- [ ] T093 [P] Create comprehensive README.md in docker/ directory
- [ ] T094 Code cleanup and refactoring across all modules
- [ ] T095 [P] Performance optimization for container startup time
- [ ] T096 Security hardening review per OWASP guidelines
- [ ] T097 Run quickstart.md validation with scripts/validate_quickstart.sh
- [ ] T098 [P] Create production deployment guide in docs/production-deployment.md
- [ ] T099 Final integration test suite execution
- [ ] T100 Coverage report generation (target ≥80%)

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) ← BLOCKS ALL USER STORIES
    ↓
┌───────────────────────────────────────────────────┐
│ P1 Stories (can run in parallel after Phase 2)   │
├───────────────────────────────────────────────────┤
│  Phase 3: US1 Deployment                         │
│  Phase 4: US2 Site Creation (depends on US1)     │
│  Phase 5: US3 MinIO Storage                      │
│  Phase 6: US4 Traefik SSL                        │
└───────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────┐
│ P2 Stories (after P1 complete)                   │
├───────────────────────────────────────────────────┤
│  Phase 7: US5 Monitoring                         │
│  Phase 8: US6 Admin UI                           │
└───────────────────────────────────────────────────┘
    ↓
Phase 9: US7 DNS (P3 - optional)
    ↓
Phase 10: Polish
```

### User Story Dependencies

| Story | Depends On | Can Start After |
|-------|------------|-----------------|
| US1 | Phase 2 (Foundational) | Phase 2 complete |
| US2 | US1 (Platform must be running) | Phase 3 complete |
| US3 | Phase 2 | Phase 2 complete (parallel with US1) |
| US4 | Phase 2 | Phase 2 complete (parallel with US1) |
| US5 | US1 (Platform to monitor) | Phase 3 complete |
| US6 | US1, US2, US3 (Features to manage) | Phases 3-5 complete |
| US7 | US2 (Sites to create DNS for) | Phase 4 complete |

### Within Each User Story (TDD Cycle)

1. 🔴 RED: Tests MUST be written FIRST and FAIL before implementation
2. 🟢 GREEN: Minimal code to pass tests
3. 🔵 REFACTOR: Improve without breaking tests
4. Coverage ≥80% required before marking story complete

### Parallel Opportunities

**Phase 1 Setup** (all parallel):
- T002, T003, T004, T005, T006

**Phase 2 Foundational** (partial parallel):
- T007, T008, T009 (tests - parallel)
- T010, T011 (DB services - T011 parallel after T010)
- T013, T015, T017 (config - parallel)

**P1 User Stories** (after Phase 2):
- US1 and US3, US4 can start in parallel
- US2 starts after US1 checkpoint

**P2 User Stories** (after P1 MVP):
- US5 and US6 can run in parallel

---

## Parallel Example: Phase 3 (User Story 1)

```bash
# Launch all tests for US1 together (TDD First):
Task: T018 "Contract test for /health endpoint"
Task: T019 "Integration test for container startup"
Task: T020 "E2E test for login page accessibility"

# After tests fail, implement in parallel where possible:
Task: T021 "Create press.yml"
Task: T022 "Create press-worker.yml" [P]
# T023 depends on T021, T022

# After compose files ready:
Task: T024 "Create docker-compose.override.yml" [P]
Task: T026 "Create setup-press.sh" [P]
```

---

## Implementation Strategy

### MVP First (P1 Stories Only)

1. Complete Phase 1: Setup (6 tasks)
2. Complete Phase 2: Foundational (11 tasks)
3. Complete Phase 3: US1 - Deployment (11 tasks)
4. **STOP and VALIDATE**: Test platform deployment independently
5. Complete Phase 4: US2 - Site Creation (10 tasks)
6. **STOP and VALIDATE**: Test site creation independently
7. Complete Phase 5: US3 - MinIO (12 tasks)
8. **STOP and VALIDATE**: Test file storage independently
9. Complete Phase 6: US4 - Traefik (11 tasks)
10. **MVP COMPLETE**: All P1 stories functional

**MVP Total**: ~61 tasks for core platform

### Incremental Delivery

| Increment | Stories | Value Delivered |
|-----------|---------|-----------------|
| MVP-1 | Setup + Foundational + US1 | Platform accessible |
| MVP-2 | + US2 | Multi-tenant ready |
| MVP-3 | + US3 | Files/backups to local storage |
| MVP-4 | + US4 | Production-ready SSL |
| Post-MVP | + US5, US6 | Full observability + admin |
| Future | + US7 | DNS automation |

### Parallel Team Strategy

With multiple developers:

1. **All**: Complete Setup + Foundational together
2. **After Phase 2**:
   - Developer A: US1 (Deployment)
   - Developer B: US3 (MinIO) + US4 (Traefik)
3. **After US1**:
   - Developer A: US2 (Sites)
   - Developer B: Continue US3/US4
4. **Post-MVP**:
   - Developer A: US5 (Monitoring)
   - Developer B: US6 (Admin UI)

---

## Task Summary

| Phase | Story | Task Count | Parallel Tasks |
|-------|-------|------------|----------------|
| 1 | Setup | 6 | 5 |
| 2 | Foundational | 11 | 6 |
| 3 | US1 - Deployment | 11 | 5 |
| 4 | US2 - Sites | 10 | 5 |
| 5 | US3 - MinIO | 12 | 6 |
| 6 | US4 - Traefik | 11 | 5 |
| 7 | US5 - Monitoring | 13 | 7 |
| 8 | US6 - Admin UI | 10 | 5 |
| 9 | US7 - DNS | 7 | 4 |
| 10 | Polish | 9 | 5 |
| **Total** | | **100** | **53** |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD Red phase)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Container prefix: `erp-saas-cloud-c16-*` (Constitution constraint)
- Port range: 32300-32500 only (Constitution constraint)
