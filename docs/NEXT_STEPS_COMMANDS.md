# 🚀 Commandes pour Continuer la Validation

**Date**: 2025-12-23
**Contexte**: Infrastructure validée, tests end-to-end à exécuter

---

## 📋 Tests Manuels à Exécuter

### 1. Vérification Services (Rapide)

```bash
# Status tous les services
docker-compose ps

# Logs temps réel Press
docker-compose logs -f press

# Health check complet
curl http://localhost:32300/api/method/ping
curl http://localhost:32392/api/v1/query?query=up
curl http://localhost:32381/api/overview
```

### 2. Test Création Site via UI

```bash
# 1. Ouvrir navigateur
xdg-open http://localhost:32300

# 2. Login: Administrator / changeme
# 3. Aller dans: Desk > Sites > New Site
# 4. Remplir formulaire:
#    - Name: test-site-001
#    - Apps: frappe
#    - Cluster: Default
# 5. Créer et observer status

# 6. Vérifier en CLI
docker exec erp-saas-cloud-c16-press bench --site press.platform.local execute \
  "print(frappe.get_all('Site', fields=['name', 'status']))"
```

### 3. Test Backup/Restore

```bash
# 1. Créer backup d'un site
docker exec erp-saas-cloud-c16-press bench --site press.platform.local backup \
  --with-files

# 2. Lister backups dans volume
docker exec erp-saas-cloud-c16-press ls -lh \
  /home/frappe/frappe-bench/sites/press.platform.local/private/backups/

# 3. Vérifier backup dans MinIO (si intégration active)
# Ouvrir: http://localhost:32391
# Login: minioadmin / minioadmin
# Vérifier bucket: erp-saas-cloud-c16-backups

# 4. Test restore (créer nouveau site d'abord)
docker exec erp-saas-cloud-c16-press bench new-site test-restore.local \
  --db-root-password changeme --admin-password changeme

docker exec erp-saas-cloud-c16-press bench --site test-restore.local restore \
  /home/frappe/frappe-bench/sites/press.platform.local/private/backups/[BACKUP_FILE]
```

### 4. Test Performance Basique

```bash
# Installer Apache Bench si nécessaire
sudo dnf install httpd-tools  # Fedora
# sudo apt install apache2-utils  # Ubuntu

# Test 100 requêtes, 10 concurrentes
ab -n 100 -c 10 http://localhost:32300/api/method/ping

# Test avec session (après login manuel)
# 1. Login dans navigateur
# 2. Copier cookie sid depuis DevTools
# 3. Exécuter:
ab -n 100 -c 10 -H "Cookie: sid=YOUR_SESSION_COOKIE" \
  http://localhost:32300/desk
```

### 5. Test Isolation Multi-Tenancy (Sécurité)

```bash
# 1. Créer 2 sites différents
docker exec erp-saas-cloud-c16-press bash -c "
  bench new-site site-a.local --db-root-password changeme --admin-password admin-a
  bench new-site site-b.local --db-root-password changeme --admin-password admin-b
"

# 2. Créer user dans site-a
docker exec erp-saas-cloud-c16-press bench --site site-a.local console << 'PYTHON'
user = frappe.get_doc({
    'doctype': 'User',
    'email': 'user-a@example.com',
    'first_name': 'User A',
    'send_welcome_email': 0
})
user.insert()
frappe.db.commit()
PYTHON

# 3. Vérifier que site-b ne peut pas voir user de site-a
docker exec erp-saas-cloud-c16-press bench --site site-b.local execute \
  "print(frappe.db.get_all('User', filters={'email': 'user-a@example.com'}))"

# Résultat attendu: [] (liste vide)
```

### 6. Test Redémarrage (Persistence)

```bash
# 1. Capturer état avant
docker-compose ps > /tmp/before-restart.txt
docker exec erp-saas-cloud-c16-press bench --site press.platform.local \
  execute "print(frappe.db.count('User'))" > /tmp/user-count-before.txt

# 2. Arrêter tous les services
docker-compose down

# 3. Redémarrer
docker-compose up -d

# 4. Attendre démarrage (30s)
sleep 30

# 5. Vérifier état après
docker-compose ps > /tmp/after-restart.txt
docker exec erp-saas-cloud-c16-press bench --site press.platform.local \
  execute "print(frappe.db.count('User'))" > /tmp/user-count-after.txt

# 6. Comparer
diff /tmp/before-restart.txt /tmp/after-restart.txt
diff /tmp/user-count-before.txt /tmp/user-count-after.txt

# Résultat attendu: Aucune différence (sauf uptime)
```

---

## 🔧 Commandes de Diagnostic

### Logs

```bash
# Logs Press application
docker-compose logs -f press | grep -i error

# Logs MariaDB
docker-compose logs -f mariadb | tail -50

# Logs Redis
docker-compose logs -f redis-cache
docker-compose logs -f redis-queue

# Logs dans le container Press
docker exec erp-saas-cloud-c16-press tail -f \
  /home/frappe/frappe-bench/logs/frappe.log
```

### Métriques

```bash
# Prometheus - Query manual
curl -G http://localhost:32392/api/v1/query \
  --data-urlencode 'query=up'

# Prometheus - Memory usage
curl -G http://localhost:32392/api/v1/query \
  --data-urlencode 'query=container_memory_usage_bytes{name=~"erp-saas.*"}'

# CPU usage
docker stats --no-stream --format \
  "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### Database

```bash
# Connexion MariaDB
docker exec -it erp-saas-cloud-c16-mariadb mysql \
  -u root -pchangeme

# Requêtes utiles (dans MySQL shell)
SHOW DATABASES;
USE _dec19b7b6895eb43;
SHOW TABLES;
SELECT COUNT(*) FROM tabSite;
SELECT name, status FROM tabSite;
```

### Redis

```bash
# Connexion Redis Cache
docker exec -it erp-saas-cloud-c16-redis-cache redis-cli \
  -a changeme

# Commandes utiles (dans redis-cli)
INFO
DBSIZE
KEYS *
MEMORY STATS
```

### MinIO

```bash
# Lister buckets
docker exec erp-saas-cloud-c16-minio mc ls local/

# Lister fichiers dans bucket
docker exec erp-saas-cloud-c16-minio mc ls \
  local/erp-saas-cloud-c16-files/

# Stats bucket
docker exec erp-saas-cloud-c16-minio mc du \
  local/erp-saas-cloud-c16-backups/
```

---

## 🐛 Fixer l'Incompatibilité Press/Frappe v16

### Option A: Patch Local Rapide

```bash
# 1. Backup du fichier original
docker exec erp-saas-cloud-c16-press cp \
  /home/frappe/frappe-bench/apps/press/press/press/doctype/team/team.py \
  /home/frappe/frappe-bench/apps/press/press/press/doctype/team/team.py.backup

# 2. Appliquer le patch
docker exec erp-saas-cloud-c16-press bash -c 'cat > /tmp/fix-team.patch << '\''EOF'\''
--- team.py.old
+++ team.py
@@ -793,7 +793,10 @@
        return frappe.db.get_all(
            "Balance Transaction",
-           fields=["sum(amount) as ending_balance"],
+           fields=[{
+               "sum": "amount",
+               "alias": "ending_balance"
+           }],
            filters={"team": self.name, "docstatus": 1, "type": ("!=", "Partnership Fee")},
            group_by="team",
        )[0].ending_balance
EOF'

# 3. Appliquer le patch
docker exec erp-saas-cloud-c16-press patch \
  /home/frappe/frappe-bench/apps/press/press/press/doctype/team/team.py \
  /tmp/fix-team.patch

# 4. Redémarrer Press
docker-compose restart press

# 5. Re-tester
docker exec erp-saas-cloud-c16-press bench --site press.platform.local \
  run-tests --app press --module press.api.tests.test_site \
  --test test_new_fn_creates_site_and_subscription
```

### Option B: Fork Press et Maintenir Patch

```bash
# 1. Fork Press sur GitHub
# 2. Cloner le fork
cd /tmp
git clone https://github.com/YOUR_USERNAME/press.git press-fork
cd press-fork

# 3. Créer branche fix
git checkout -b fix/frappe-v16-compat

# 4. Appliquer fix dans team.py (éditer manuellement)
# Ligne 796: Remplacer
#   fields=["sum(amount) as ending_balance"],
# Par:
#   fields=[{"sum": "amount", "alias": "ending_balance"}],

# 5. Commit et push
git add press/press/doctype/team/team.py
git commit -m "Fix: Update SQL syntax for Frappe v16 compatibility

- Replace string SQL function with dict syntax
- Fixes: sum(amount) as ending_balance -> {'sum': 'amount'}
- Required for Frappe v16 query builder
"
git push origin fix/frappe-v16-compat

# 6. Créer PR vers frappe/press
# 7. En attendant merge, utiliser le fork dans Dockerfile
```

### Option C: Attendre Mise à Jour Officielle

```bash
# Vérifier si une issue existe déjà
xdg-open https://github.com/frappe/press/issues

# Sinon, créer une issue
# Titre: "SQL syntax incompatible with Frappe v16 in Team.get_balance_all()"
# Body: Décrire le problème et le fix proposé
```

---

## 📊 Collecter Métriques pour Rapport

### Performance Metrics

```bash
# 1. Response times
curl -w "\nTime: %{time_total}s\n" http://localhost:32300/api/method/ping

# 2. Database connections
docker exec erp-saas-cloud-c16-mariadb mysql -u root -pchangeme \
  -e "SHOW STATUS LIKE 'Threads_connected';"

# 3. Redis memory
docker exec erp-saas-cloud-c16-redis-cache redis-cli -a changeme \
  INFO memory | grep used_memory_human

# 4. Disk usage
docker exec erp-saas-cloud-c16-press df -h | grep -E "(Filesystem|frappe-bench)"

# 5. Container resource usage
docker stats --no-stream --format \
  "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
```

### Availability Metrics

```bash
# Uptime des containers
docker ps --format "table {{.Names}}\t{{.Status}}"

# Health status
docker inspect erp-saas-cloud-c16-press | jq '.[0].State.Health.Status'
docker inspect erp-saas-cloud-c16-mariadb | jq '.[0].State.Health.Status'

# Prometheus targets
curl -s http://localhost:32392/api/v1/targets | \
  jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

---

## ✅ Checklist Validation Finale

Cocher au fur et à mesure:

```bash
# Infrastructure
[ ] Tous les services UP (docker-compose ps)
[ ] Tous les services Healthy
[ ] Uptime > 24h sans interruption
[ ] Logs sans erreurs critiques

# Application
[ ] Login Press fonctionnel
[ ] Desk accessible
[ ] API répond en < 500ms
[ ] Assets chargent correctement

# Fonctionnalités
[ ] Création site via UI fonctionne
[ ] Installation app sur site OK
[ ] Backup manuel créé avec succès
[ ] Backup visible dans MinIO
[ ] Restore backup fonctionne

# Performance
[ ] 100 requêtes simultanées OK (ab test)
[ ] CPU < 80% sous charge
[ ] Memory stable (pas de leak)
[ ] Response time moyen < 500ms

# Sécurité
[ ] SSL/TLS configuré
[ ] Isolation tenants validée
[ ] Pas de secrets dans logs
[ ] Firewall configuré (si applicable)

# Monitoring
[ ] Prometheus collecte métriques
[ ] Grafana dashboards visibles
[ ] Alertes configurées (optionnel P2)

# Persistence
[ ] Données survivent redémarrage
[ ] Volumes persistent
[ ] Configuration preserved
```

---

## 📝 Documenter Résultats

### Après chaque test

```bash
# Créer fichier résultats
cat > /tmp/test-results-$(date +%Y%m%d-%H%M%S).md << 'EOF'
# Test Results - [TEST_NAME]

## Date
$(date)

## Test Executed
[Description du test]

## Command Used
```bash
[Commande exacte]
```

## Expected Result
[Résultat attendu]

## Actual Result
[Résultat obtenu]

## Status
[ ] PASS / [ ] FAIL

## Screenshots/Logs
[Si applicable]

## Notes
[Observations supplémentaires]
EOF
```

### Rapport Final

```bash
# Compiler tous les résultats
cat /tmp/test-results-*.md > docs/FINAL_TEST_REPORT.md

# Ajouter métriques
echo "## Performance Metrics" >> docs/FINAL_TEST_REPORT.md
docker stats --no-stream >> docs/FINAL_TEST_REPORT.md

# Ajouter status services
echo "## Services Status" >> docs/FINAL_TEST_REPORT.md
docker-compose ps >> docs/FINAL_TEST_REPORT.md
```

---

**Bon courage pour la suite de la validation ! 🚀**

**Prochaine étape**: Exécuter les tests manuels end-to-end
**Documentation**: Voir `docs/END_TO_END_TEST_PLAN.md`
**Support**: Vérifier logs si problèmes
