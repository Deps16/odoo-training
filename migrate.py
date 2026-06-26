# -*- coding: utf-8 -*-
import xmlrpc.client
import psycopg2
from psycopg2.extras import RealDictCursor
import sys

# ==========================================
# CONFIGURATION
# ==========================================
SOURCE_DB = {
    "dbname": "pm_dev",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": "5432"
}

ODOO_URL = "http://localhost:8070"
ODOO_DB = input("Masukkan nama database Odoo Anda (default: postgres): ") or "postgres"
ODOO_USER = input("Masukkan username/login Odoo admin (default: admin): ") or "admin"
ODOO_PASSWORD = input("Masukkan password Odoo admin (default: admin): ") or "admin"

try:
    # 1. Connect to Odoo via XML-RPC
    print("\n[Odoo] Connecting to Odoo via XML-RPC...")
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        print("[-] Gagal autentikasi ke Odoo. Periksa database, username, dan password Anda.")
        sys.exit(1)
    print(f"[+] Berhasil terhubung ke Odoo! UID Admin: {uid}")
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

    # 2. Connect to Laravel Postgres (pm_dev)
    print("\n[Postgres] Connecting to source database (pm_dev)...")
    conn = psycopg2.connect(**SOURCE_DB)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    print("[+] Berhasil terhubung ke database source pm_dev!")

    # ==========================================
    # STEP 1: MIGRATE USERS / PARTNERS
    # ==========================================
    print("\n[Step 1] Migrating Users & Subcontractors...")
    cur.execute("SELECT id, name, email, role, username FROM users")
    laravel_users = cur.fetchall()
    
    user_mapping = {} # maps laravel_uuid -> odoo_res_user_id
    partner_mapping = {} # maps laravel_uuid -> odoo_res_partner_id
    
    # Get internal user group ID (Internal User)
    group_user_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'ir.model.data', 'check_object_reference', ['base', 'group_user'])[1]

    for lu in laravel_users:
        email = lu['email']
        name = lu['name']
        uuid = lu['id']
        role = lu['role']
        
        # Check if user already exists in Odoo
        existing_user = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'res.users', 'search_read', [[('login', '=', email)]], {'fields': ['id', 'partner_id']})
        
        if existing_user:
            odoo_uid = existing_user[0]['id']
            odoo_partner_id = existing_user[0]['partner_id'][0]
            print(f" -> User {name} ({email}) sudah ada di Odoo (ID: {odoo_uid})")
        else:
            # Create user
            vals = {
                'name': name,
                'login': email,
                'email': email,
                'groups_id': [(6, 0, [group_user_id])], # Assign to Internal User group
            }
            try:
                odoo_uid = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'res.users', 'create', [vals])
                # Fetch partner_id created automatically by Odoo
                user_data = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'res.users', 'read', [odoo_uid], {'fields': ['partner_id']})
                odoo_partner_id = user_data[0]['partner_id'][0]
                print(f" -> Berhasil membuat user {name} (ID: {odoo_uid})")
            except Exception as e:
                print(f" -> [-] Gagal membuat user {name}: {e}")
                continue
                
        user_mapping[uuid] = odoo_uid
        partner_mapping[uuid] = odoo_partner_id

    # ==========================================
    # STEP 2: MIGRATE PROJECTS
    # ==========================================
    print("\n[Step 2] Migrating Projects...")
    cur.execute("""
        SELECT id, name, description, po_number, po_amount, type, 
               project_manager_id, project_director_id, subcontractor_id 
        FROM projects
    """)
    laravel_projects = cur.fetchall()
    project_mapping = {} # maps laravel_uuid -> odoo_project_id

    for lp in laravel_projects:
        uuid = lp['id']
        name = lp['name']
        
        # Check if project already exists
        existing_proj = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'project.project', 'search', [[('x_laravel_id', '=', uuid)]])
        if existing_proj:
            project_mapping[uuid] = existing_proj[0]
            print(f" -> Project '{name}' sudah diimpor sebelumnya (ID: {existing_proj[0]})")
            continue
            
        # Resolve manager and director
        manager_id = user_mapping.get(lp['project_manager_id'], False)
        director_id = user_mapping.get(lp['project_director_id'], False)
        subcontractor_id = partner_mapping.get(lp['subcontractor_id'], False)
        
        project_type = lp['type'] if lp['type'] in ['A/1', 'A/2', 'A/3', 'A/4'] else 'A/1'
        
        vals = {
            'name': name,
            'description': lp['description'],
            'x_po_number': lp['po_number'],
            'x_po_amount': float(lp['po_amount']) if lp['po_amount'] else 0.0,
            'x_project_type': project_type,
            'user_id': manager_id,
            'x_project_director_id': director_id,
            'x_subcontractor_id': subcontractor_id,
            'x_laravel_id': uuid
        }
        
        try:
            odoo_proj_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'project.project', 'create', [vals])
            project_mapping[uuid] = odoo_proj_id
            print(f" -> Berhasil membuat project '{name}' (ID: {odoo_proj_id})")
        except Exception as e:
            print(f" -> [-] Gagal membuat project '{name}': {e}")

    # ==========================================
    # STEP 3: MIGRATE SITES / TASKS
    # ==========================================
    print("\n[Step 3] Migrating Project Sites (Tasks)...")
    cur.execute("""
        SELECT id, project_id, name, description, supervisor_id, subcontractor_id, 
               done_date, service_date, bast_date 
        FROM project_sites
    """)
    laravel_sites = cur.fetchall()
    task_mapping = {} # maps laravel_uuid -> odoo_task_id

    for ls in laravel_sites:
        uuid = ls['id']
        name = ls['name']
        proj_uuid = ls['project_id']
        
        # Check if task already exists
        existing_task = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'project.task', 'search', [[('x_laravel_id', '=', uuid)]])
        if existing_task:
            task_mapping[uuid] = existing_task[0]
            print(f" -> Site '{name}' sudah diimpor sebelumnya (ID: {existing_task[0]})")
            continue
            
        odoo_proj_id = project_mapping.get(proj_uuid, False)
        if not odoo_proj_id:
            print(f" -> [-] Skip site '{name}' karena project parent-nya tidak ditemukan.")
            continue
            
        supervisor_id = user_mapping.get(ls['supervisor_id'], False)
        subcontractor_id = partner_mapping.get(ls['subcontractor_id'], False)
        
        vals = {
            'name': name,
            'description': ls['description'],
            'project_id': odoo_proj_id,
            'x_supervisor_id': supervisor_id,
            'x_subcontractor_id': subcontractor_id,
            'x_done_date': str(ls['done_date']) if ls['done_date'] else False,
            'x_service_date': str(ls['service_date']) if ls['service_date'] else False,
            'x_bast_date': str(ls['bast_date']) if ls['bast_date'] else False,
            'x_laravel_id': uuid
        }
        
        try:
            odoo_task_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'project.task', 'create', [vals])
            task_mapping[uuid] = odoo_task_id
            print(f" -> Berhasil membuat task/site '{name}' (ID: {odoo_task_id})")
        except Exception as e:
            print(f" -> [-] Gagal membuat task/site '{name}': {e}")

    # ==========================================
    # STEP 4: MIGRATE SITE CHRONOLOGIES
    # ==========================================
    print("\n[Step 4] Migrating Chronologies...")
    cur.execute("""
        SELECT id, project_site_id, user_id, title, event_date, description 
        FROM project_site_chronologies
    """)
    laravel_chronologies = cur.fetchall()

    for lc in laravel_chronologies:
        uuid = lc['id']
        site_uuid = lc['project_site_id']
        title = lc['title']
        
        # Check if chronology already exists
        existing_chron = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'project.site.chronology', 'search', [[('x_laravel_id', '=', uuid)]])
        if existing_chron:
            print(f" -> Chronology '{title}' sudah diimpor sebelumnya.")
            continue
            
        odoo_task_id = task_mapping.get(site_uuid, False)
        if not odoo_task_id:
            print(f" -> [-] Skip chronology '{title}' karena site parent-nya tidak ditemukan.")
            continue
            
        user_id = user_mapping.get(lc['user_id'], False)
        
        vals = {
            'project_site_id': odoo_task_id,
            'user_id': user_id,
            'title': title,
            'event_date': str(lc['event_date']) if lc['event_date'] else False,
            'description': lc['description'],
            'x_laravel_id': uuid
        }
        
        try:
            odoo_chron_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'project.site.chronology', 'create', [vals])
            print(f" -> Berhasil membuat chronology '{title}' (ID: {odoo_chron_id})")
        except Exception as e:
            print(f" -> [-] Gagal membuat chronology '{title}': {e}")

    # ==========================================
    # STEP 5: MIGRATE BUDGETS
    # ==========================================
    print("\n[Step 5] Migrating Budgets...")
    cur.execute("""
        SELECT id, project_id, type, amount, date, description 
        FROM project_budgets
    """)
    laravel_budgets = cur.fetchall()

    for lb in laravel_budgets:
        uuid = lb['id']
        proj_uuid = lb['project_id']
        b_type = lb['type']
        
        # Check if budget already exists
        existing_bud = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'project.budget', 'search', [[('x_laravel_id', '=', uuid)]])
        if existing_bud:
            print(f" -> Budget '{b_type}' sudah diimpor sebelumnya.")
            continue
            
        odoo_proj_id = project_mapping.get(proj_uuid, False)
        if not odoo_proj_id:
            print(f" -> [-] Skip budget '{b_type}' karena project parent-nya tidak ditemukan.")
            continue
            
        vals = {
            'project_id': odoo_proj_id,
            'type': b_type,
            'amount': float(lb['amount']) if lb['amount'] else 0.0,
            'date': str(lb['date']) if lb['date'] else False,
            'description': lb['description'],
            'x_laravel_id': uuid
        }
        
        try:
            odoo_bud_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'project.budget', 'create', [vals])
            print(f" -> Berhasil membuat budget '{b_type}' (ID: {odoo_bud_id})")
        except Exception as e:
            print(f" -> [-] Gagal membuat budget '{b_type}': {e}")

    # Cleanup
    cur.close()
    conn.close()
    print("\n[+] MIGRASI SELESAI DENGAN SUKSES!")

except Exception as e:
    print(f"\n[-] Terjadi kesalahan fatal: {e}")
