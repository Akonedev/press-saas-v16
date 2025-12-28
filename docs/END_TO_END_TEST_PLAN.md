# 📋 Plan de Tests End-to-End - ERP SaaS Cloud PRESSE v16

**Date**: 2025-12-23
**Plateforme**: Press Self-Hosted v0.7.0
**Constitution**: erp-saas-cloud-c16

---

## 🎯 Objectif

Valider de bout en bout toutes les fonctionnalités critiques de la plateforme Press self-hosted, sans régression.

---

## 📊 Résultats des Tests Unitaires Automatisés

### Tests Press API

| Module | Tests | Passés | Échoués | Statut | Notes |
|--------|-------|--------|---------|--------|-------|
| **test_account** | 2 | 2 | 0 | ✅ OK | Signup et validation postale |
| **test_site** | - | - | - | ⚠️ Incompatible | Code Press incompatible avec Frappe v16 (SQL syntax) |
| **test_bench** | - | - | - | ⚠️ Incompatible | Dépendance de test_site |
| **test_server** | - | - | - | ⚠️ Incompatible | Dépendance de test_site |

**Dépendances de test installées**:
- ✅ moto 5.1.18 (AWS mocking)
- ✅ faker 39.0.0 (données fake)
- ✅ responses 0.23.1 (HTTP mocking)
- ✅ hypothesis 6.148.8 (property-based testing)

**Problèmes identifiés**:
1. **Code Press obsolète** :
   - Utilise syntaxe SQL ancienne : `sum(amount) as ending_balance` (string)
   - Frappe v16 exige : `{'sum': 'amount'}` (dict)
   - Affecte `Team.get_balance_all()` dans team.py:796

---

## 🧪 Tests End-to-End Manuels

### US1 - ✅ Déploiement Initial Press (VALIDÉ)

**Objectif**: Vérifier que Press démarre et est accessible

| # | Test | Commande | Résultat Attendu | Statut |
|---|------|----------|------------------|--------|
| 1.1 | Service Press actif | `docker ps \| grep press` | Container UP | ✅ Passé |
| 1.2 | API Health endpoint | `curl localhost:32300/api/method/ping` | `{"message": "pong"}` | ✅ Passé |
| 1.3 | Page login accessible | `curl localhost:32300/login` | HTML 200 OK | ✅ Passé |
| 1.4 | Assets chargent correctement | Navigateur DevTools | CSS/JS 200 OK | ✅ Passé |
| 1.5 | Login administrateur | admin@example.com / changeme | Desk accessible | ✅ Passé |
| 1.6 | Apps installées | `bench list-apps` | frappe, press, storage_integration | ✅ Passé |

**Résultat**: ✅ **PASS** (6/6)

---

### US2 - 📝 Création de Site (À TESTER)

**Objectif**: Créer un nouveau site Frappe via Press

| # | Test | Étapes | Résultat Attendu | Statut |
|---|------|--------|------------------|--------|
| 2.1 | Accès menu Sites | Desk > Sites > New Site | Formulaire création visible | ⏳ À tester |
| 2.2 | Validation formulaire | Saisir nom site invalide | Message erreur | ⏳ À tester |
| 2.3 | Créer site test | Nom: test-site-001, Apps: frappe | Site créé status=Pending | ⏳ À tester |
| 2.4 | Provisioning automatique | Attendre 2 min | Site status=Active | ⏳ À tester |
| 2.5 | Site accessible | Naviguer vers test-site-001 | Page login s'affiche | ⏳ À tester |
| 2.6 | Base de données créée | `docker exec mariadb mysql -e "SHOW DATABASES"` | DB pour test-site-001 visible | ⏳ À tester |

**Résultat**: ⏳ **À EXÉCUTER**

---

### US3 - 🗄️ Stockage MinIO (À TESTER)

**Objectif**: Vérifier stockage fichiers et backups dans MinIO

| # | Test | Étapes | Résultat Attendu | Statut |
|---|------|--------|------------------|--------|
| 3.1 | Console MinIO accessible | http://localhost:32391 | Login minioadmin/minioadmin OK | ✅ Validé précédemment |
| 3.2 | Bucket files existe | MinIO Console > Buckets | Bucket `erp-saas-cloud-c16-files` visible | ⏳ À tester |
| 3.3 | Upload fichier via site | Site > Upload File | Fichier apparaît dans MinIO | ⏳ À tester |
| 3.4 | Bucket backups existe | MinIO Console > Buckets | Bucket `erp-saas-cloud-c16-backups` visible | ⏳ À tester |
| 3.5 | Créer backup manuel | Site > Backup > Create | Backup .sql.gz apparaît dans MinIO | ⏳ À tester |
| 3.6 | Download backup | MinIO > Download backup file | Fichier téléchargé valide | ⏳ À tester |

**Résultat**: ⏳ **À EXÉCUTER**

---

### US4 - 🔒 Traefik SSL/TLS (VALIDÉ PARTIELLEMENT)

**Objectif**: Vérifier routage et SSL

| # | Test | Étapes | Résultat Attendu | Statut |
|---|------|--------|------------------|--------|
| 4.1 | Dashboard Traefik | http://localhost:32381 | Dashboard visible | ✅ Passé |
| 4.2 | Routers configurés | Dashboard > HTTP > Routers | Au moins 5 routers actifs | ✅ Passé (12 routers) |
| 4.3 | Services configurés | Dashboard > HTTP > Services | Services press, grafana visibles | ✅ Passé (5 services) |
| 4.4 | Middlewares sécurité | Dashboard > HTTP > Middlewares | Headers, compression actifs | ✅ Passé (9 middlewares) |
| 4.5 | Certificats SSL dev | `ls config/traefik/certs/` | Certificats mkcert présents | ⏳ À tester |
| 4.6 | HTTPS redirection | Curl http://press.local | Redirect 301 vers https | ⏳ À tester |

**Résultat**: ⚠️ **PARTIEL** (4/6 validés)

---

### US5 - 📊 Monitoring (VALIDÉ PARTIELLEMENT)

**Objectif**: Vérifier collecte métriques et dashboards

| # | Test | Étapes | Résultat Attendu | Statut |
|---|------|--------|------------------|--------|
| 5.1 | Prometheus accessible | http://localhost:32392 | UI Prometheus visible | ✅ Passé |
| 5.2 | Targets UP | Prometheus > Status > Targets | 4 targets UP | ✅ Passé |
| 5.3 | Métriques collectées | Prometheus > Graph > `up` | Données temps réel | ✅ Passé |
| 5.4 | Grafana accessible | http://localhost:32393 | Login admin/admin OK | ✅ Passé |
| 5.5 | Datasource Prometheus | Grafana > Config > Data Sources | Prometheus configuré | ⏳ À tester |
| 5.6 | Dashboard Press | Grafana > Dashboards | Dashboard Press visible | ⏳ À tester |
| 5.7 | Panels affichent data | Dashboard > Panels | Graphiques avec données | ⏳ À tester |

**Résultat**: ⚠️ **PARTIEL** (4/7 validés)

---

## 🔄 Tests d'Intégration

### Test INT-01: Workflow Complet Création Site

**Scénario**: Créer un site, installer une app, créer backup, le restaurer

```bash
# 1. Créer site
bench --site press.platform.local execute "press.api.site.new({...})"

# 2. Attendre provisioning
watch 'bench --site press.platform.local execute "frappe.get_doc(\"Site\", \"test-001\").status"'

# 3. Installer app (si pas déjà installée)
bench --site press.platform.local execute "press.api.site.install_app(\"test-001\", \"erpnext\")"

# 4. Créer backup
bench --site test-001 backup --with-files

# 5. Vérifier backup dans MinIO
mc ls local/erp-saas-cloud-c16-backups/

# 6. Restaurer backup
bench --site new-site restore /path/to/backup.sql.gz
```

**Résultat attendu**: Tous les steps passent sans erreur
**Statut**: ⏳ À EXÉCUTER

---

### Test INT-02: Performance Sous Charge

**Scénario**: 10 utilisateurs simultanés accèdent au desk

```bash
# Utiliser Apache Bench
ab -n 100 -c 10 -H "Cookie: sid=..." http://localhost:32300/desk
```

**Critères de succès**:
- Temps réponse moyen < 500ms
- Aucune erreur 500
- CPU Press < 80%

**Statut**: ⏳ À EXÉCUTER

---

### Test INT-03: Isolation Multi-Tenancy

**Scénario**: 2 sites ne peuvent pas accéder aux données de l'autre

```bash
# 1. Créer site-a avec user-a
# 2. Créer site-b avec user-b
# 3. Depuis site-a, tenter SELECT * FROM site-b.tabUser
# 4. Vérifier erreur permissions
```

**Résultat attendu**: Permission denied
**Statut**: ⏳ À EXÉCUTER

---

## 🚨 Tests de Régression

### REG-01: Services Ne Cassent Pas Après Mise à Jour

```bash
# 1. Capturer état avant
docker-compose ps > before.txt

# 2. Simuler update (rebuild image)
docker-compose build press

# 3. Redémarrer
docker-compose up -d

# 4. Vérifier état après
docker-compose ps > after.txt
diff before.txt after.txt

# 5. Tester tous les endpoints
```

**Statut**: ⏳ À EXÉCUTER

---

### REG-02: Données Persistent Après Redémarrage

```bash
# 1. Créer données test
# 2. Arrêter tous les services
docker-compose down

# 3. Redémarrer
docker-compose up -d

# 4. Vérifier données toujours présentes
```

**Statut**: ⏳ À EXÉCUTER

---

## 📝 Checklist Validation Finale

Avant de marquer la plateforme comme "Production Ready":

- [ ] **Infrastructure** (9/9 services UP et Healthy)
- [ ] **Press Application** (API, Login, Desk fonctionnels)
- [ ] **Création Site** (Workflow complet end-to-end)
- [ ] **Stockage MinIO** (Upload/download fichiers + backups)
- [ ] **Routage Traefik** (SSL/TLS + routing multi-sites)
- [ ] **Monitoring** (Prometheus + Grafana dashboards opérationnels)
- [ ] **Performance** (Temps réponse < 500ms sous charge)
- [ ] **Sécurité** (Isolation tenants + SSL enforced)
- [ ] **Persistence** (Données survivent redémarrage)
- [ ] **Documentation** (Procédures opérationnelles complètes)

---

## 🎯 Prochaines Actions

### Priorité P0 (Bloquant Production)

1. **Exécuter tests manuels US2-US5** non complétés
2. **Exécuter tests d'intégration INT-01 à INT-03**
3. **Exécuter tests de régression REG-01 et REG-02**
4. **Fixer ou documenter incompatibilité code Press/Frappe v16**

### Priorité P1 (Important)

5. **Load testing** avec 50+ utilisateurs simultanés
6. **Backup/Restore** test complet avec données volumineuses
7. **Fail-over testing** (simuler crash MariaDB, Redis, Press)
8. **Security audit** (OWASP Top 10 check)

### Priorité P2 (Nice to Have)

9. **Performance profiling** (identifier bottlenecks)
10. **Monitoring alerting** (configurer alertes critiques)
11. **Admin UI** (Phase 8 du plan initial)
12. **DNS Local** (Phase 9 du plan initial)

---

## 📊 Métriques de Succès

- **Infrastructure**: 100% services Healthy ✅ **ATTEINT** (9/9)
- **Tests Unitaires**: >80% pass rate ⚠️ **PARTIEL** (2/2 account OK, site incompatible)
- **Tests E2E**: 100% pass rate ⏳ **EN COURS** (6/6 US1, reste à tester)
- **Performance**: <500ms response time ⏳ **À MESURER**
- **Uptime**: >99% sur 7 jours ⏳ **À MESURER**

---

**Dernière mise à jour**: 2025-12-23 03:50
**Exécuté par**: Claude Code
**Statut Global**: ⚠️ **EN COURS** - Infrastructure validée, tests applicatifs à compléter
