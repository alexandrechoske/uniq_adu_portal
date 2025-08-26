#!/usr/bin/env python
"""
Database State Checker for Perfis + Usuários
Queries the database to identify current issues and validate data consistency
"""

def generate_database_queries():
    """Generate SQL queries to check database state"""
    
    print("="*80)
    print("DATABASE STATE CHECK - PERFIS + USUÁRIOS")
    print("="*80)
    
    print("\n🔍 EXECUTE THESE QUERIES IN YOUR DATABASE TO CHECK CURRENT STATE:\n")
    
    queries = [
        {
            'title': '1. CHECK PERFIL_PRINCIPAL vs PERFIS_JSON CONSISTENCY',
            'purpose': 'Identify users where perfil_principal equals perfis_json (potential issue)',
            'query': '''
SELECT 
    id,
    email,
    name,
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
            'title': '2. CHECK BASICO PRIORITY LOGIC',
            'purpose': 'Find users with basico as perfil_principal when other profiles exist',
            'query': '''
SELECT 
    email,
    perfil_principal,
    perfis_json,
    cardinality(string_to_array(replace(replace(replace(perfis_json, '[', ''), ']', ''), '"', ''), ',')) as profile_count,
    CASE 
        WHEN perfil_principal = 'basico' 
             AND cardinality(string_to_array(replace(replace(replace(perfis_json, '[', ''), ']', ''), '"', ''), ',')) > 1 
        THEN '⚠️ SHOULD_USE_NON_BASICO'
        WHEN perfil_principal = 'basico' 
             AND cardinality(string_to_array(replace(replace(replace(perfis_json, '[', ''), ']', ''), '"', ''), ',')) = 1 
        THEN '✅ BASICO_ONLY_OK'
        ELSE '✅ NON_BASICO_PRINCIPAL'
    END as basico_priority_status
FROM users_dev 
WHERE perfis_json IS NOT NULL
ORDER BY basico_priority_status, email;
            '''
        },
        {
            'title': '3. CHECK ORPHANED PROFILE REFERENCES',
            'purpose': 'Find profile names referenced in users but not existing in perfis_acesso',
            'query': '''
WITH user_profiles AS (
    SELECT DISTINCT 
        unnest(string_to_array(replace(replace(replace(perfis_json, '[', ''), ']', ''), '"', ''), ',')) as referenced_profile
    FROM users_dev 
    WHERE perfis_json IS NOT NULL
)
SELECT 
    up.referenced_profile,
    CASE 
        WHEN pa.perfil_nome IS NOT NULL THEN '✅ EXISTS'
        ELSE '🔴 ORPHANED'
    END as profile_status
FROM user_profiles up
LEFT JOIN perfis_acesso pa ON up.referenced_profile = pa.perfil_nome
ORDER BY profile_status, referenced_profile;
            '''
        },
        {
            'title': '4. CHECK EMAIL UNIQUENESS',
            'purpose': 'Ensure email addresses are unique (authentication integrity)',
            'query': '''
SELECT 
    email, 
    COUNT(*) as count,
    CASE 
        WHEN COUNT(*) = 1 THEN '✅ UNIQUE'
        ELSE '🔴 DUPLICATE'
    END as uniqueness_status
FROM users_dev 
GROUP BY email 
ORDER BY count DESC, email;
            '''
        },
        {
            'title': '5. CHECK KAUAN SPECIFIC ISSUE',
            'purpose': 'Check Kauan\'s current profile configuration',
            'query': '''
SELECT 
    email,
    name,
    perfil_principal,
    perfis_json,
    role,
    is_active,
    CASE 
        WHEN email LIKE '%kauan%' THEN '👤 KAUAN_USER'
        ELSE '👤 OTHER_USER'
    END as user_type
FROM users_dev 
WHERE email LIKE '%kauan%' OR email LIKE '%cesar%'
ORDER BY email;
            '''
        },
        {
            'title': '6. CHECK AVAILABLE PROFILES',
            'purpose': 'List all available profiles in perfis_acesso',
            'query': '''
SELECT 
    perfil_nome,
    descricao,
    ativo,
    paginas,
    modulos,
    created_at,
    updated_at
FROM perfis_acesso 
ORDER BY ativo DESC, perfil_nome;
            '''
        },
        {
            'title': '7. CHECK RECENTLY CREATED/UPDATED USERS',
            'purpose': 'Check recent user operations for potential issues',
            'query': '''
SELECT 
    email,
    name,
    perfil_principal,
    perfis_json,
    created_at,
    updated_at,
    CASE 
        WHEN updated_at > created_at THEN '📝 UPDATED'
        ELSE '🆕 CREATED_ONLY'
    END as modification_status
FROM users_dev 
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
   OR updated_at >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY COALESCE(updated_at, created_at) DESC;
            '''
        },
        {
            'title': '8. ANALYZE PERFIL_PRINCIPAL PATTERNS',
            'purpose': 'Analyze patterns in perfil_principal assignment',
            'query': '''
SELECT 
    perfil_principal,
    COUNT(*) as user_count,
    ARRAY_AGG(DISTINCT role) as roles_using_it,
    CASE 
        WHEN perfil_principal = 'basico' THEN '🔵 BASIC_PROFILE'
        WHEN perfil_principal LIKE '%admin%' THEN '🔴 ADMIN_PROFILE'
        WHEN perfil_principal LIKE '%financeiro%' THEN '💰 FINANCIAL_PROFILE'
        WHEN perfil_principal LIKE '%importacao%' THEN '🚢 IMPORT_PROFILE'
        ELSE '⚪ OTHER_PROFILE'
    END as profile_category
FROM users_dev 
WHERE perfil_principal IS NOT NULL
GROUP BY perfil_principal
ORDER BY user_count DESC, perfil_principal;
            '''
        }
    ]
    
    for i, query_info in enumerate(queries, 1):
        print(f"{query_info['title']}")
        print(f"Purpose: {query_info['purpose']}")
        print("```sql")
        print(query_info['query'].strip())
        print("```")
        print()
    
    print("="*80)
    print("EXECUTE THESE QUERIES AND ANALYZE THE RESULTS")
    print("="*80)
    print("Look for:")
    print("🔴 Red indicators - Issues that need fixing")
    print("⚠️ Yellow indicators - Potential issues to review") 
    print("✅ Green indicators - Good state")
    print("📝 Blue indicators - Informational")

if __name__ == "__main__":
    generate_database_queries()