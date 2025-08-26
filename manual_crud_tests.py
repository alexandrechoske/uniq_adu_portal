#!/usr/bin/env python
"""
Manual CRUD Testing Script for Perfis + Usuários
Step-by-step testing with immediate database validation
"""

def test_profile_creation_manual():
    """Manual test instructions for profile creation"""
    print("=" * 80)
    print("🧪 MANUAL TEST 1: PROFILE CREATION")
    print("=" * 80)
    
    print("\n📋 STEPS TO EXECUTE:")
    print("1. Navigate to: http://localhost:5000/usuarios/perfis")
    print("2. Click 'Novo Perfil'")
    print("3. Create profile with these details:")
    print("   - Nome: test_crud_profile_financeiro")
    print("   - Descrição: Perfil de teste para CRUD operations - financeiro")
    print("   - Módulos: fin (Financeiro)")
    print("   - Páginas: fluxo_caixa, despesas")
    print("4. Click 'Salvar'")
    
    print("\n🔍 DATABASE VALIDATION QUERY:")
    print("Execute this in your database to validate:")
    print("""
    SELECT 
        perfil_nome,
        descricao,
        ativo,
        paginas,
        modulos,
        created_at
    FROM perfis_acesso 
    WHERE perfil_nome = 'test_crud_profile_financeiro';
    """)
    
    print("\n✅ EXPECTED RESULTS:")
    print("- perfil_nome: 'test_crud_profile_financeiro'")
    print("- descricao: 'Perfil de teste para CRUD operations - financeiro'")
    print("- ativo: true")
    print("- modulos should contain 'fin'")
    print("- paginas should contain 'fluxo_caixa', 'despesas'")
    print("- created_at should be recent timestamp")

def test_profile_update_manual():
    """Manual test instructions for profile update"""
    print("\n" + "=" * 80)
    print("🧪 MANUAL TEST 2: PROFILE UPDATE (NAME PRESERVATION)")
    print("=" * 80)
    
    print("\n📋 STEPS TO EXECUTE:")
    print("1. Navigate to: http://localhost:5000/usuarios/perfis")
    print("2. Find the 'test_crud_profile_financeiro' profile")
    print("3. Click 'Edit' button")
    print("4. Notice that the 'Nome' field is DISABLED with warning")
    print("5. Try to change:")
    print("   - Descrição: 'UPDATED: Perfil editado para testar preservação de nome'")
    print("   - Keep same modules and pages")
    print("6. Click 'Salvar'")
    
    print("\n🔍 DATABASE VALIDATION QUERY:")
    print("Execute this in your database to validate name preservation:")
    print("""
    SELECT 
        perfil_nome,
        descricao,
        updated_at,
        created_at
    FROM perfis_acesso 
    WHERE perfil_nome = 'test_crud_profile_financeiro';
    """)
    
    print("\n✅ EXPECTED RESULTS:")
    print("- perfil_nome: UNCHANGED 'test_crud_profile_financeiro'")
    print("- descricao: 'UPDATED: Perfil editado para testar preservação de nome'")
    print("- updated_at: Recent timestamp (after created_at)")

def test_user_creation_manual():
    """Manual test instructions for user creation with profile assignment"""
    print("\n" + "=" * 80)
    print("🧪 MANUAL TEST 3: USER CREATION WITH PROFILE ASSIGNMENT")
    print("=" * 80)
    
    print("\n📋 STEPS TO EXECUTE:")
    print("1. Navigate to: http://localhost:5000/usuarios/")
    print("2. Click 'Novo Usuário'")
    print("3. Create user with these details:")
    print("   - Nome: Test CRUD User")
    print("   - Email: test.crud.user@test.com")
    print("   - Perfil de Acesso: Equipe Interna (interno_unique)")
    print("   - Senha: test123")
    print("   - Confirmar Senha: test123")
    print("   - Status: Ativo")
    print("4. In 'Perfis de Acesso' section:")
    print("   - Select: basico, financeiro_completo")
    print("   - (This tests the perfil_principal vs perfis_json logic)")
    print("5. Click 'Salvar'")
    
    print("\n🔍 DATABASE VALIDATION QUERIES:")
    print("Execute these in your database to validate perfil_principal logic:")
    print("""
    -- Check user creation and profile assignment
    SELECT 
        id,
        email,
        name,
        perfil_principal,
        perfis_json,
        role,
        is_active,
        created_at
    FROM users_dev 
    WHERE email = 'test.crud.user@test.com';
    """)
    
    print("""
    -- Validate perfil_principal vs perfis_json relationship
    SELECT 
        email,
        perfil_principal,
        perfis_json,
        CASE 
            WHEN perfil_principal = ANY(string_to_array(replace(replace(replace(perfis_json, '[', ''), ']', ''), '"', ''), ',')) 
            THEN '✅ PRINCIPAL_IN_JSON'
            ELSE '🔴 MISMATCH'
        END as consistency_check,
        CASE 
            WHEN perfil_principal = 'basico' AND 'financeiro_completo' = ANY(string_to_array(replace(replace(replace(perfis_json, '[', ''), ']', ''), '"', ''), ','))
            THEN '⚠️ SHOULD_USE_FINANCEIRO_COMPLETO'
            WHEN perfil_principal != 'basico' AND perfil_principal = ANY(string_to_array(replace(replace(replace(perfis_json, '[', ''), ']', ''), '"', ''), ','))
            THEN '✅ CORRECT_NON_BASICO_PRIORITY'
            ELSE '✅ OK'
        END as priority_check
    FROM users_dev 
    WHERE email = 'test.crud.user@test.com';
    """)
    
    print("\n✅ EXPECTED RESULTS:")
    print("- perfil_principal: 'financeiro_completo' (NOT 'basico')")
    print("- perfis_json: [\"basico\", \"financeiro_completo\"] or similar array")
    print("- consistency_check: '✅ PRINCIPAL_IN_JSON'")
    print("- priority_check: '✅ CORRECT_NON_BASICO_PRIORITY'")
    print("- This validates that perfil_principal correctly prioritizes non-basico profiles")

def test_user_update_manual():
    """Manual test instructions for user update with email preservation"""
    print("\n" + "=" * 80)
    print("🧪 MANUAL TEST 4: USER UPDATE (EMAIL PRESERVATION)")
    print("=" * 80)
    
    print("\n📋 STEPS TO EXECUTE:")
    print("1. Navigate to: http://localhost:5000/usuarios/")
    print("2. Find the 'Test CRUD User' user")
    print("3. Click 'Edit' button")
    print("4. Notice that the 'Email' field is DISABLED with warning")
    print("5. Try to change:")
    print("   - Nome: 'UPDATED Test CRUD User Name'")
    print("   - Role: Keep as 'Equipe Interna'")
    print("   - Add another profile: importacao_basico (if available)")
    print("6. Click 'Salvar'")
    
    print("\n🔍 DATABASE VALIDATION QUERY:")
    print("Execute this in your database to validate email preservation:")
    print("""
    SELECT 
        email,
        name,
        perfil_principal,
        perfis_json,
        updated_at,
        created_at
    FROM users_dev 
    WHERE email = 'test.crud.user@test.com';
    """)
    
    print("\n✅ EXPECTED RESULTS:")
    print("- email: UNCHANGED 'test.crud.user@test.com'")
    print("- name: 'UPDATED Test CRUD User Name'")
    print("- perfil_principal: Should still prioritize non-basico profiles")
    print("- perfis_json: Should contain updated profile list")
    print("- updated_at: Recent timestamp (after created_at)")

def test_access_control_manual():
    """Manual test instructions for access control validation"""
    print("\n" + "=" * 80)
    print("🧪 MANUAL TEST 5: ACCESS CONTROL VALIDATION")
    print("=" * 80)
    
    print("\n📋 STEPS TO EXECUTE:")
    print("1. Login as Kauan (kauan.cesar@uniqueaduaneira.com.br)")
    print("   - If Kauan has 'financeiro_completo' profile")
    print("2. Try to access:")
    print("   - ✅ Should work: /financeiro/dashboard-executivo/")
    print("   - ✅ Should work: Financial pages in menu")
    print("   - ❌ Should fail: /dashboard-executivo/ (importacao)")
    print("   - ❌ Should fail: Importacao pages in menu")
    print("3. Check browser console for access control messages")
    
    print("\n🔍 DATABASE VALIDATION - Check Kauan's current profile:")
    print("""
    SELECT 
        email,
        name,
        perfil_principal,
        perfis_json,
        role,
        is_active
    FROM users_dev 
    WHERE email LIKE '%kauan%';
    """)
    
    print("\n✅ EXPECTED RESULTS:")
    print("- Kauan should only see financial modules in menu")
    print("- Direct URL access to /dashboard-executivo/ should redirect or show 403")
    print("- Financial URLs should work correctly")
    print("- Browser console should show access control messages")

def test_security_boundaries_manual():
    """Manual test instructions for security boundary testing"""
    print("\n" + "=" * 80)
    print("🧪 MANUAL TEST 6: SECURITY BOUNDARIES")
    print("=" * 80)
    
    print("\n📋 STEPS TO EXECUTE:")
    print("1. Open incognito/private browser window")
    print("2. Try to access without authentication:")
    print("   - ❌ Should fail: http://localhost:5000/usuarios/perfis")
    print("   - ❌ Should fail: http://localhost:5000/usuarios/")
    print("   - ❌ Should redirect to login: http://localhost:5000/usuarios/api/users")
    print("3. Login as Lucas (admin_importacoes)")
    print("4. Try to:")
    print("   - ❌ Should fail: Create financial profiles")
    print("   - ❌ Should fail: Assign financial profiles to users")
    print("   - ✅ Should work: Create importacao profiles")
    print("   - ✅ Should work: Assign importacao profiles")
    
    print("\n✅ EXPECTED RESULTS:")
    print("- Unauthenticated access blocked with 401/403 or redirect to login")
    print("- Module Admins restricted to their module's profiles")
    print("- Proper error messages for unauthorized operations")

def test_cleanup_manual():
    """Manual test instructions for cleanup"""
    print("\n" + "=" * 80)
    print("🧪 MANUAL TEST 7: CLEANUP TEST DATA")
    print("=" * 80)
    
    print("\n📋 STEPS TO EXECUTE:")
    print("1. Delete test user:")
    print("   - Navigate to: http://localhost:5000/usuarios/")
    print("   - Find 'Test CRUD User'")
    print("   - Click delete button")
    print("   - Confirm deletion")
    print("2. Delete test profile:")
    print("   - Navigate to: http://localhost:5000/usuarios/perfis")
    print("   - Find 'test_crud_profile_financeiro'")
    print("   - Delete if deletion is available")
    
    print("\n🔍 DATABASE VALIDATION - Confirm cleanup:")
    print("""
    -- Check user deletion
    SELECT COUNT(*) as remaining_test_users
    FROM users_dev 
    WHERE email = 'test.crud.user@test.com';
    
    -- Check profile deletion (if delete feature exists)
    SELECT COUNT(*) as remaining_test_profiles
    FROM perfis_acesso 
    WHERE perfil_nome = 'test_crud_profile_financeiro';
    """)
    
    print("\n✅ EXPECTED RESULTS:")
    print("- remaining_test_users: 0")
    print("- remaining_test_profiles: 0 (if deletion implemented)")

def generate_final_validation_queries():
    """Generate comprehensive validation queries"""
    print("\n" + "=" * 80)
    print("🔍 FINAL DATABASE VALIDATION QUERIES")
    print("=" * 80)
    
    print("\n📊 Execute these queries to validate overall system integrity:")
    
    queries = [
        {
            'title': 'Check all users for perfil_principal vs perfis_json consistency',
            'query': '''
SELECT 
    email,
    perfil_principal,
    perfis_json,
    CASE 
        WHEN perfil_principal IS NULL THEN '🔴 NULL_PRINCIPAL'
        WHEN perfis_json IS NULL THEN '🔴 NULL_JSON'
        WHEN perfil_principal = perfis_json THEN '⚠️ EXACT_MATCH_ISSUE'
        WHEN perfil_principal = ANY(string_to_array(replace(replace(replace(perfis_json, '[', ''), ']', ''), '"', ''), ',')) THEN '✅ PRINCIPAL_IN_JSON'
        ELSE '🔴 MISMATCH'
    END as consistency_status
FROM users_dev 
ORDER BY consistency_status, email;
            '''
        },
        {
            'title': 'Check for basico priority issues',
            'query': '''
SELECT 
    email,
    perfil_principal,
    perfis_json,
    CASE 
        WHEN perfil_principal = 'basico' 
             AND cardinality(string_to_array(replace(replace(replace(perfis_json, '[', ''), ']', ''), '"', ''), ',')) > 1 
        THEN '⚠️ SHOULD_USE_NON_BASICO'
        ELSE '✅ OK'
    END as basico_priority_check
FROM users_dev 
WHERE perfis_json LIKE '%basico%'
ORDER BY basico_priority_check DESC, email;
            '''
        },
        {
            'title': 'Summary of profile assignments',
            'query': '''
SELECT 
    perfil_principal,
    COUNT(*) as user_count,
    ARRAY_AGG(DISTINCT role) as roles_using_it
FROM users_dev 
WHERE perfil_principal IS NOT NULL
GROUP BY perfil_principal
ORDER BY user_count DESC;
            '''
        }
    ]
    
    for query_info in queries:
        print(f"\n-- {query_info['title']}")
        print(query_info['query'])

def main():
    """Main execution"""
    print("🧪 COMPREHENSIVE MANUAL CRUD TESTING FOR PERFIS + USUÁRIOS")
    print("Follow these tests step by step and validate with database queries")
    print("=" * 80)
    
    test_profile_creation_manual()
    test_profile_update_manual()
    test_user_creation_manual()
    test_user_update_manual()
    test_access_control_manual()
    test_security_boundaries_manual()
    test_cleanup_manual()
    generate_final_validation_queries()
    
    print("\n" + "=" * 80)
    print("🏁 MANUAL TESTING COMPLETE")
    print("=" * 80)
    print("Execute all database queries to validate 100% security and data integrity")
    print("Report any issues found during testing")

if __name__ == "__main__":
    main()