#!/usr/bin/env python
"""
Investigation Script for perfil_principal vs perfis_json Issue
Analyzes the specific concern: "when I created a user, the column 'perfil principal' is equal 'perfis_json'"

This should NOT happen as:
- perfil_principal should be a single string (e.g., 'financeiro_completo')
- perfis_json should be an array (e.g., ['basico', 'financeiro_completo'])
"""

def investigate_perfil_issue():
    """Investigate the perfil_principal vs perfis_json data integrity"""
    
    print("="*80)
    print("🔍 INVESTIGATING PERFIL_PRINCIPAL vs PERFIS_JSON ISSUE")
    print("="*80)
    
    print("\n📋 ISSUE DESCRIPTION:")
    print("User reported: 'when I created a user, the column perfil principal is equal perfis_json'")
    print("This indicates a potential data integrity issue where:")
    print("- perfil_principal (should be string) = perfis_json (should be array)")
    
    print("\n🎯 EXPECTED BEHAVIOR:")
    print("✅ perfil_principal: 'financeiro_completo' (single string)")
    print("✅ perfis_json: [\"basico\", \"financeiro_completo\"] (JSON array)")
    print("❌ perfil_principal: '[\"basico\", \"financeiro_completo\"]' (array as string - BUG)")
    
    print("\n" + "="*80)
    print("🔍 EXECUTE THESE DATABASE QUERIES TO INVESTIGATE:")
    print("="*80)
    
    queries = [
        {
            'title': '1. CHECK FOR EXACT MATCHES (THE REPORTED ISSUE)',
            'description': 'Find users where perfil_principal exactly equals perfis_json',
            'query': '''
-- This should return NO ROWS if working correctly
SELECT 
    id,
    email,
    name,
    perfil_principal,
    perfis_json,
    pg_typeof(perfil_principal) as principal_type,
    pg_typeof(perfis_json) as json_type,
    length(perfil_principal::text) as principal_length,
    length(perfis_json::text) as json_length
FROM users_dev 
WHERE perfil_principal::text = perfis_json::text  -- Cast both to text for comparison
ORDER BY email;
            '''
        },
        {
            'title': '2. CHECK DATA TYPES AND FORMATS',
            'description': 'Analyze data types and formats of both fields',
            'query': '''
SELECT 
    email,
    perfil_principal,
    perfis_json,
    pg_typeof(perfil_principal) as principal_type,
    pg_typeof(perfis_json) as json_type,
    CASE 
        WHEN perfil_principal IS NULL THEN 'NULL'
        WHEN perfil_principal LIKE '[%]' THEN 'LOOKS_LIKE_ARRAY'
        WHEN perfil_principal LIKE '"%"' THEN 'QUOTED_STRING'
        ELSE 'NORMAL_STRING'
    END as principal_format,
    CASE 
        WHEN perfis_json IS NULL THEN 'NULL'
        WHEN jsonb_typeof(perfis_json) = 'array' THEN 'PROPER_ARRAY'
        WHEN jsonb_typeof(perfis_json) = 'string' THEN 'STRING_NOT_ARRAY'
        ELSE 'OTHER_TYPE'
    END as json_format
FROM users_dev 
ORDER BY principal_format DESC, json_format DESC, email;
            '''
        },
        {
            'title': '3. CHECK FOR ARRAY-AS-STRING CONTAMINATION',
            'description': 'Find cases where perfil_principal contains array-like strings',
            'query': '''
-- Look for perfil_principal that looks like JSON arrays
SELECT 
    email,
    perfil_principal,
    perfis_json,
    'CONTAMINATED: perfil_principal looks like JSON array' as issue_type
FROM users_dev 
WHERE perfil_principal LIKE '[%]'
   OR perfil_principal LIKE '%,%'
   OR perfil_principal LIKE '"%"'
UNION ALL
-- Look for perfis_json that's not a proper array
SELECT 
    email,
    perfil_principal,
    perfis_json,
    'INVALID: perfis_json is not an array' as issue_type
FROM users_dev 
WHERE perfis_json IS NOT NULL 
  AND jsonb_typeof(perfis_json) != 'array'
ORDER BY issue_type, email;
            '''
        },
        {
            'title': '4. VALIDATE CORRECT RELATIONSHIPS',
            'description': 'Check if perfil_principal is properly contained in perfis_json array',
            'query': '''
SELECT 
    email,
    perfil_principal,
    perfis_json,
    CASE 
        WHEN perfil_principal IS NULL AND perfis_json IS NULL THEN '⚪ BOTH_NULL'
        WHEN perfil_principal IS NULL THEN '🔴 PRINCIPAL_NULL'
        WHEN perfis_json IS NULL THEN '🔴 JSON_NULL'
        WHEN perfil_principal = ANY(
            SELECT jsonb_array_elements_text(perfis_json)
        ) THEN '✅ PRINCIPAL_IN_ARRAY'
        ELSE '🔴 PRINCIPAL_NOT_IN_ARRAY'
    END as relationship_status,
    jsonb_array_length(perfis_json) as array_length
FROM users_dev 
ORDER BY relationship_status, email;
            '''
        },
        {
            'title': '5. CHECK RECENT USER CREATIONS',
            'description': 'Focus on recently created users to identify when issue started',
            'query': '''
SELECT 
    email,
    name,
    perfil_principal,
    perfis_json,
    created_at,
    updated_at,
    CASE 
        WHEN perfil_principal::text = perfis_json::text THEN '🔴 EXACT_MATCH_ISSUE'
        WHEN perfil_principal = ANY(SELECT jsonb_array_elements_text(perfis_json)) THEN '✅ CORRECT_RELATIONSHIP'
        ELSE '⚠️ OTHER_ISSUE'
    END as validation_result
FROM users_dev 
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
   OR updated_at >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY COALESCE(updated_at, created_at) DESC;
            '''
        },
        {
            'title': '6. SPECIFIC CHECK FOR KAUAN',
            'description': 'Check Kauan\'s profile assignment specifically',
            'query': '''
SELECT 
    email,
    name,
    perfil_principal,
    perfis_json,
    role,
    is_active,
    created_at,
    updated_at,
    pg_typeof(perfil_principal) as principal_type,
    pg_typeof(perfis_json) as json_type,
    CASE 
        WHEN perfil_principal::text = perfis_json::text THEN '🔴 EXACT_MATCH_BUG'
        WHEN perfil_principal = ANY(SELECT jsonb_array_elements_text(perfis_json)) THEN '✅ CORRECT'
        ELSE '⚠️ OTHER_ISSUE'
    END as kauan_status
FROM users_dev 
WHERE email LIKE '%kauan%' OR name LIKE '%Kauan%'
ORDER BY email;
            '''
        }
    ]
    
    for query_info in queries:
        print(f"\n{query_info['title']}")
        print(f"Purpose: {query_info['description']}")
        print("```sql")
        print(query_info['query'].strip())
        print("```")
    
    print("\n" + "="*80)
    print("🔧 POTENTIAL ROOT CAUSES TO INVESTIGATE:")
    print("="*80)
    
    causes = [
        "1. User creation logic incorrectly assigns array to perfil_principal",
        "2. Profile assignment logic doesn't differentiate between single value and array", 
        "3. Database migration issue where arrays got stringified",
        "4. Frontend sends wrong data format to backend",
        "5. Backend doesn't properly handle array vs string assignment",
        "6. PostgreSQL JSONB handling issue in Supabase"
    ]
    
    for cause in causes:
        print(f"• {cause}")
    
    print("\n" + "="*80) 
    print("🏥 PROPOSED FIXES (if issues found):")
    print("="*80)
    
    fixes = [
        "1. Clean up contaminated data in database",
        "2. Fix user creation logic to properly assign single string to perfil_principal",
        "3. Fix profile assignment logic to maintain proper data types",
        "4. Add validation to prevent future contamination",
        "5. Update frontend to send correct data formats",
        "6. Add database constraints to enforce data integrity"
    ]
    
    for fix in fixes:
        print(f"• {fix}")
    
    print(f"\n{'='*80}")
    print("📊 EXECUTE QUERIES AND REPORT FINDINGS")
    print("="*80)
    print("Run each query above and report:")
    print("🔴 Any rows returned by Query #1 (exact matches) - this is the reported bug")
    print("⚠️ Any 'CONTAMINATED' or 'INVALID' results from Query #3")
    print("🔴 Any 'PRINCIPAL_NOT_IN_ARRAY' results from Query #4") 
    print("🔍 Results from Query #6 for Kauan specifically")

if __name__ == "__main__":
    investigate_perfil_issue()