"""
Setup initial data for Press platform
Creates necessary doctypes for site creation
"""
import frappe


def setup_press_data():
    """Create all necessary data for Press to function"""

    print("\n" + "=" * 60)
    print("CONFIGURATION INITIALE DE PRESS")
    print("=" * 60)

    # 1. Root Domain
    print("\n1️⃣  Root Domain...")
    domain_name = "platform.local"
    if not frappe.db.exists("Root Domain", domain_name):
        domain = frappe.get_doc({
            "doctype": "Root Domain",
            "name": domain_name,
            "default_cluster": "Default"
        })
        domain.insert()
        print(f"   ✅ Créé: {domain_name}")
    else:
        print(f"   ℹ️  Existe: {domain_name}")

    # Configure Press Settings
    frappe.db.set_single_value("Press Settings", "domain", domain_name)

    # 2. Frappe App
    print("\n2️⃣  Frappe App...")
    if not frappe.db.exists("App", "frappe"):
        app = frappe.get_doc({
            "doctype": "App",
            "name": "frappe",
            "title": "Frappe Framework",
            "repo_owner": "frappe",
            "repo_name": "frappe",
            "branch": "develop"
        })
        app.insert()
        print("   ✅ Créé: frappe")
    else:
        app = frappe.get_doc("App", "frappe")
        print("   ℹ️  Existe: frappe")

    # 3. Frappe Version
    print("\n3️⃣  Frappe Version...")
    version_name = "Version 16"
    if not frappe.db.exists("Frappe Version", version_name):
        version = frappe.get_doc({
            "doctype": "Frappe Version",
            "name": version_name,
            "number": 16,
            "status": "Stable"
        })
        version.insert()
        print(f"   ✅ Créé: {version_name}")
    else:
        print(f"   ℹ️  Existe: {version_name}")

    # 3b. App Source for Frappe
    print("\n3️⃣ b. Frappe App Source...")
    team = frappe.get_value("Team", {"user": "Administrator"}, "name")
    repo_url = "https://github.com/frappe/frappe"
    source_exists = frappe.db.exists("App Source", {"app": "frappe", "version": version_name})

    if not source_exists:
        # Créer App Source manuellement
        source = frappe.get_doc({
            "doctype": "App Source",
            "app": "frappe",
            "version": version_name,
            "repository_url": repo_url,
            "branch": "develop",
            "team": team,
            "enabled": 1
        })
        source.insert(ignore_permissions=True, ignore_if_duplicate=True)
        source_name = source.name
        print(f"   ✅ Créé: {source_name}")
    else:
        source_name = frappe.get_value("App Source", {"app": "frappe", "version": version_name}, "name")
        print(f"   ℹ️  Existe: {source_name}")

    # 4. Release Group
    print("\n4️⃣  Release Group...")
    group_title = "Frappe v16 Platform"
    group_exists = frappe.db.exists("Release Group", {"title": group_title})

    if not group_exists:
        group = frappe.get_doc({
            "doctype": "Release Group",
            "title": group_title,
            "version": version_name,
            "enabled": 1,
            "public": 1,
            "cluster": "Default",
            "apps": [{"app": "frappe", "source": source_name}]
        })
        group.insert()
        group_name = group.name
        print(f"   ✅ Créé: {group_name}")
    else:
        group_name = frappe.get_value("Release Group", {"title": group_title}, "name")
        print(f"   ℹ️  Existe: {group_name}")

    # 5. Site Plan
    print("\n5️⃣  Site Plan...")
    plan_name = "Default Plan"
    if not frappe.db.exists("Site Plan", plan_name):
        plan = frappe.get_doc({
            "doctype": "Site Plan",
            "name": plan_name,
            "plan_title": plan_name,
            "price_inr": 0,
            "price_usd": 0,
            "enabled": 1,
            "cpu_time_per_day": 3600,
            "max_database_usage": 1024,
            "max_storage_usage": 1024
        })
        plan.insert()
        print(f"   ✅ Créé: {plan_name}")
    else:
        print(f"   ℹ️  Existe: {plan_name}")

    frappe.db.commit()

    # Résumé
    print("\n" + "=" * 60)
    print("RÉSUMÉ - DONNÉES CRÉÉES")
    print("=" * 60)

    teams = frappe.db.count("Team")
    domains = frappe.db.count("Root Domain")
    apps = frappe.db.count("App")
    groups = frappe.db.count("Release Group")
    plans = frappe.db.count("Site Plan")

    print(f"✅ Teams: {teams}")
    print(f"✅ Root Domains: {domains}")
    print(f"✅ Apps: {apps}")
    print(f"✅ Release Groups: {groups}")
    print(f"✅ Site Plans: {plans}")
    print(f"✅ Cluster: Default")

    print("\n🎯 Press est maintenant configuré pour créer des sites !")

    return {
        "success": True,
        "domain": domain_name,
        "release_group": group_name,
        "plan": plan_name
    }
