# 🎯 Plan de Déploiement Production - Press v16

**Version**: 1.0.0
**Date Préparation**: 2025-12-27
**Status**: Prêt pour Exécution
**Criticité**: HAUTE (Correctifs de compatibilité majeurs)

---

## 📊 Résumé Exécutif

### Objectif
Déployer les correctifs Frappe v16 validés en staging vers l'environnement de production.

### Justification
- **Impact**: +70 tests débloqués (2.7% → 98.6%)
- **Risque**: FAIBLE (zéro régression, validé en staging)
- **Urgence**: MOYENNE (compatibilité v16 requise pour maintenance future)

### Fenêtre de Maintenance
**Durée estimée**: 30 minutes
**Horaire recommandé**: En dehors des heures de pointe

---

## ✅ Pré-requis (Checklist Obligatoire)

### Infrastructure
- [ ] Accès serveur production validé
- [ ] Backup automatique configuré
- [ ] Espace disque suffisant (>20% libre)
- [ ] Plan de rollback documenté
- [ ] Contact équipe infrastructure disponible

### Code
- [x] Code validé en staging (72/73 tests)
- [x] Code poussé sur GitHub (commit f00a724)
- [x] Documentation complète
- [ ] Revue de code effectuée (optionnel si solo)

### Communication
- [ ] Utilisateurs notifiés (maintenance planifiée)
- [ ] Fenêtre de maintenance réservée
- [ ] Canal de communication d'urgence actif

---

## 🚀 Procédure de Déploiement

### Phase 1 : Préparation (T-30 minutes)

#### 1.1 Backup Complet
```bash
# Se connecter au serveur production
ssh production-server

# Aller dans le répertoire bench
cd /path/to/frappe-bench

# Backup base de données + fichiers
bench --site <production-site> backup --with-files

# Vérifier le backup
ls -lh sites/<production-site>/private/backups/
# Copier le backup vers un endroit sûr
cp sites/<production-site>/private/backups/*.sql.gz /backup/safe/location/
```

#### 1.2 Snapshot Serveur (si Cloud)
```bash
# AWS
aws ec2 create-snapshot --volume-id vol-xxx

# GCP
gcloud compute disks snapshot <disk-name>

# DigitalOcean
doctl compute volume snapshot <volume-id>
```

#### 1.3 Vérification État Actuel
```bash
# Services actifs
sudo supervisorctl status

# Logs récents
tail -100 logs/web.log | grep -i error
tail -100 logs/worker.log | grep -i error

# Santé de la base
bench --site <production-site> mariadb -e "SHOW STATUS LIKE 'Threads_connected';"
```

---

### Phase 2 : Déploiement (T=0)

#### 2.1 Activer Mode Maintenance
```bash
# Mettre le site en maintenance
bench --site <production-site> set-maintenance-mode on

# Vérifier
curl http://<production-url>
# Devrait afficher page maintenance
```

#### 2.2 Déployer le Code

**Option A : Via Git (Recommandé)**
```bash
cd apps/press
git fetch origin
git checkout main
git pull origin main

# Vérifier le commit
git log -1 --oneline
# Devrait afficher: f00a724 fix: Complete Frappe v16 compatibility
```

**Option B : Copie Manuelle (Si Git non disponible)**
```bash
# Copier les fichiers modifiés depuis GitHub ou staging
scp user@staging:/path/to/balance_transaction.py ./apps/press/press/press/doctype/balance_transaction/
scp user@staging:/path/to/site.py ./apps/press/press/api/
```

#### 2.3 Configuration
```bash
# Activer server_script_enabled
bench --site <production-site> set-config server_script_enabled true
bench set-config -g server_script_enabled true

# Vérifier
cat sites/common_site_config.json | grep server_script_enabled
cat sites/<production-site>/site_config.json | grep server_script_enabled
```

#### 2.4 Redémarrage Services
```bash
# Redémarrer tous les services
sudo supervisorctl restart all

# Attendre stabilisation (30 secondes)
sleep 30

# Vérifier status
sudo supervisorctl status
```

---

### Phase 3 : Validation (T+5 minutes)

#### 3.1 Tests Automatisés Critiques
```bash
# Test Balance Transaction (le plus critique)
bench --site <production-site> run-tests \
  --module press.press.doctype.balance_transaction.test_balance_transaction

# Résultat attendu: Ran 7 tests ... OK

# Test Site API (ORDER BY fix)
bench --site <production-site> run-tests \
  --module press.api.tests.test_site --failfast

# Test Server API (server_script_enabled)
bench --site <production-site> run-tests \
  --module press.api.tests.test_server --failfast
```

#### 3.2 Smoke Tests Fonctionnels

**Test 1 : API Health**
```bash
curl http://<production-url>/api/method/ping
# Attendu: {"message":"pong"}
```

**Test 2 : Interface Press**
```bash
curl -I http://<production-url>/
# Attendu: HTTP/1.1 200 OK
```

**Test 3 : Balance Transaction (via bench console)**
```bash
bench --site <production-site> console <<EOF
from press.press.doctype.team.test_team import create_test_team
team = create_test_team()
team.allocate_credit_amount(10, source="Production Validation")
bt = frappe.get_last_doc("Balance Transaction", {"team": team.name})
assert bt.ending_balance == 10
print("✅ Balance Transaction works!")
frappe.db.rollback()
EOF
```

#### 3.3 Vérification Logs
```bash
# Logs web (dernières 100 lignes)
tail -100 logs/web.log | grep -i error
# Attendu: aucune erreur

# Logs worker
tail -100 logs/worker.log | grep -i error
# Attendu: aucune erreur
```

---

### Phase 4 : Mise en Production (T+15 minutes)

#### 4.1 Désactiver Maintenance
```bash
# Retirer le mode maintenance
bench --site <production-site> set-maintenance-mode off

# Vérifier accessibilité
curl http://<production-url>/
```

#### 4.2 Monitoring Post-Déploiement
```bash
# Surveiller les métriques (30 minutes minimum)
# - Temps de réponse API
# - Taux d'erreur
# - Utilisation mémoire/CPU
# - Connexions base de données

# Exemple avec curl
while true; do
  curl -o /dev/null -s -w "%{time_total}\n" http://<production-url>/api/method/ping
  sleep 10
done
```

---

## 🔴 Plan de Rollback (Si Problème)

### Déclencheurs de Rollback
- Taux d'erreur > 5%
- Tests critiques échouent
- Performance dégradée > 50%
- Erreurs non résolues dans logs

### Procédure Rollback

#### Rollback Code (Rapide - 5 minutes)
```bash
# Mode maintenance ON
bench --site <production-site> set-maintenance-mode on

# Revenir au commit précédent
cd apps/press
git reset --hard HEAD~1

# OU restaurer fichiers depuis backup
cp /backup/balance_transaction.py.bak ./apps/press/press/press/doctype/balance_transaction/balance_transaction.py
cp /backup/site.py.bak ./apps/press/press/api/site.py

# Redémarrer
sudo supervisorctl restart all

# Mode maintenance OFF
bench --site <production-site> set-maintenance-mode off
```

#### Rollback Configuration
```bash
# Retirer server_script_enabled si problème
bench --site <production-site> set-config server_script_enabled false
bench set-config -g server_script_enabled false
```

#### Rollback Base de Données (Dernier Recours - 15 minutes)
```bash
# ATTENTION : Perte de données depuis le backup !

# Restaurer depuis backup Phase 1
bench --site <production-site> restore /backup/safe/location/backup.sql.gz

# Redémarrer services
sudo supervisorctl restart all
```

---

## 📊 Métriques de Succès

### Critères GO/NO-GO

**GO (Déploiement Réussi)** si :
- ✅ Tous les tests critiques passent (Balance, Site, Server)
- ✅ API répond en < 500ms
- ✅ Aucune erreur dans logs (15 min post-deploy)
- ✅ Interface accessible
- ✅ Pas de spike CPU/Mémoire

**NO-GO (Rollback Requis)** si :
- ❌ Un test critique échoue
- ❌ Taux d'erreur > 5%
- ❌ Performance dégradée > 50%
- ❌ Erreurs bloquantes dans logs

---

## 📋 Timeline Détaillée

| Temps | Phase | Action | Durée |
|-------|-------|--------|-------|
| T-30 | Préparation | Backup + Snapshot | 10 min |
| T-20 | Préparation | Vérification état | 5 min |
| T-15 | Préparation | Communication équipe | 5 min |
| T-10 | Préparation | Dernière revue | 5 min |
| **T-5** | **Déploiement** | **Mode Maintenance ON** | **1 min** |
| T-4 | Déploiement | Git pull / Copie code | 2 min |
| T-2 | Déploiement | Configuration | 1 min |
| T-1 | Déploiement | Redémarrage services | 1 min |
| **T+0** | **Validation** | **Tests automatisés** | **5 min** |
| T+5 | Validation | Smoke tests | 5 min |
| T+10 | Validation | Vérification logs | 2 min |
| T+12 | Production | Mode Maintenance OFF | 1 min |
| **T+13** | **Post-Deploy** | **Monitoring** | **30 min** |
| T+43 | Clôture | Rapport final | 5 min |

**Durée Totale Fenêtre** : 73 minutes (1h13)
**Downtime Utilisateur** : ~15 minutes (T-5 à T+12)

---

## 👥 Rôles & Responsabilités

### Responsable Déploiement
- Exécute la procédure
- Décide GO/NO-GO
- Active rollback si nécessaire

### Support Technique (Backup)
- Surveille logs en temps réel
- Valide métriques
- Assiste en cas de problème

### Communication
- Notifie utilisateurs (avant/après)
- Met à jour status page
- Documente incidents

---

## 📞 Contacts d'Urgence

### Technique
- **DevOps Lead** : [Contact]
- **DBA** : [Contact]
- **Équipe Frappe** : https://discuss.frappe.io

### Business
- **Product Owner** : [Contact]
- **Support Client** : [Contact]

---

## 📝 Post-Déploiement

### Rapport à Générer
- [ ] Métriques de succès
- [ ] Incidents rencontrés
- [ ] Actions correctives
- [ ] Lessons learned

### Suivi Long Terme (7 jours)
- [ ] Monitoring quotidien
- [ ] Analyse logs
- [ ] Feedback utilisateurs
- [ ] Performance tracking

---

## 🎯 Checklist Finale

### Avant Déploiement
- [ ] Backup validé
- [ ] Snapshot créé
- [ ] Équipe disponible
- [ ] Utilisateurs notifiés
- [ ] Rollback plan testé

### Pendant Déploiement
- [ ] Mode maintenance activé
- [ ] Code déployé
- [ ] Configuration mise à jour
- [ ] Services redémarrés
- [ ] Tests passés

### Après Déploiement
- [ ] Mode maintenance désactivé
- [ ] Logs vérifiés
- [ ] Monitoring actif
- [ ] Rapport créé
- [ ] Documentation mise à jour

---

**État**: ⏸️ PRÊT POUR EXÉCUTION
**Prochain Jalon**: Planification fenêtre de maintenance
**Contact**: DevOps Team

**Préparé par**: Claude Code (Sonnet 4.5)
**Validé par**: Tests Staging (72/73 PASS)
