# 🔐 Access Control System Documentation
## Unique Aduaneira Portal - Hierarchical Admin Structure

**Version**: 2.0  
**Last Updated**: August 26, 2025  
**Author**: Development Team  

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [User Hierarchy](#user-hierarchy)
4. [Database Schema](#database-schema)
5. [Profile Types](#profile-types)
6. [Module Structure](#module-structure)
7. [Access Control Rules](#access-control-rules)
8. [Implementation Details](#implementation-details)
9. [Testing & Validation](#testing--validation)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

The Unique Aduaneira Portal implements a **3-tier hierarchical access control system** designed to provide granular permissions based on operational and financial responsibilities. This system replaced the previous binary admin structure with a more flexible, scalable approach that aligns with the company's organizational needs.

### Key Features
- **Hierarchical Admin Levels**: Master, Module, and Basic users
- **Module-Based Isolation**: Operational vs Financial admin separation
- **Profile Assignment Validation**: Admins can only assign profiles within their scope
- **Future-Ready Architecture**: Prepared for Consultoria and Exportação modules
- **Strict Security Boundaries**: No cross-module access for module admins

---

## 🏗️ System Architecture

### Design Patterns
- **Role-Based Access Control (RBAC)**: Users have roles that determine base permissions
- **Profile-Based Enhancement**: Profiles refine access within roles
- **Hierarchical Validation**: Higher-level admins can manage lower-level users
- **Module Isolation**: Strict boundaries between operational and financial domains

### Core Components
- **Authentication**: Supabase Auth with session management
- **Authorization**: Flask decorators with profile validation
- **Access Service**: Centralized permission logic (`perfil_access_service.py`)
- **Route Protection**: Module-specific access validation
- **UI Rendering**: Dynamic interface based on user permissions

---

## 👥 User Hierarchy

### Level 0: Master Admin
**Profile**: `master_admin`  
**Role**: `admin`  
**Scope**: Full system access

**Capabilities**:
- ✅ Manage all users (create, edit, delete)
- ✅ Manage all profiles (create, edit, delete)
- ✅ Access all modules (Importação, Financeiro, future modules)
- ✅ System configuration and admin functions
- ✅ Assign any profile to any user

**Examples**: 
- `system@uniqueaduaneira.com.br`
- `edgar@uniqueaduaneira.com.br`

### Level 1: Module Admin

#### Admin Operacional
**Profile**: `admin_operacao`  
**Role**: `interno_unique`  
**Scope**: Operational modules only

**Capabilities**:
- ✅ Manage basic users (interno_unique + basico, cliente_unique + basico)
- ✅ Access operational modules: Importação, Consultoria*, Exportação*
- ✅ Assign operational profiles only
- ❌ Cannot access financial modules
- ❌ Cannot manage other admins
- ❌ Cannot manage profiles (no perfis page access)

**Module Coverage**:
- **Importação** (imp): All importation-related functions
- **Consultoria** (con): Future consultancy services*
- **Exportação** (exp): Future export services*

#### Admin Financeiro
**Profile**: `admin_financeiro`  
**Role**: `interno_unique`  
**Scope**: Financial modules only

**Capabilities**:
- ✅ Manage basic users (interno_unique + basico, cliente_unique + basico)
- ✅ Access financial modules: Financeiro
- ✅ Assign financial profiles only
- ❌ Cannot access operational modules
- ❌ Cannot manage other admins
- ❌ Cannot manage profiles (no perfis page access)

**Module Coverage**:
- **Financeiro** (fin): All financial functions

### Level 2: Basic Users

#### Internal Basic Users
**Profile**: `basico`  
**Role**: `interno_unique`  
**Scope**: Limited access based on assigned profiles

#### Client Basic Users
**Profile**: `basico`  
**Role**: `cliente_unique`  
**Scope**: Client-specific access only

#### Specialized Profile Users
**Examples**:
- `financeiro_completo`: Full financial access
- `financeiro_fluxo_de_caixa`: Cash flow access only
- `importacoes_completo`: Full importation access

---

## 🗄️ Database Schema

### users_dev Table
```sql
CREATE TABLE users_dev (
    id UUID PRIMARY KEY,
    name VARCHAR,
    email VARCHAR UNIQUE,
    role VARCHAR, -- 'admin', 'interno_unique', 'cliente_unique'
    perfil_principal TEXT DEFAULT 'basico',
    perfis_json JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### users_perfis Table (Enhanced)
```sql
CREATE TABLE users_perfis (
    id INTEGER PRIMARY KEY,
    perfil_nome VARCHAR NOT NULL,
    modulo_codigo VARCHAR NOT NULL,
    modulo_nome VARCHAR NOT NULL,
    paginas_modulo JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    is_admin_profile BOOLEAN DEFAULT false, -- NEW COLUMN
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(perfil_nome, modulo_codigo)
);
```

### Key Data Examples
```sql
-- Admin Profiles
INSERT INTO users_perfis VALUES
(36, 'admin_operacao', 'imp', 'Importações', '["dashboard_executivo", "dashboard_resumido", "documentos", "relatorio", "agente"]', true, true),
(37, 'admin_operacao', 'con', 'Consultoria', '["consultoria_dashboard", "consultoria_processos"]', true, true),
(38, 'admin_operacao', 'exp', 'Exportação', '["exportacao_dashboard", "exportacao_processos"]', true, true),
(39, 'admin_financeiro', 'fin', 'Financeiro', '["fin_dashboard_executivo", "fluxo_caixa", "despesas", "faturamento"]', true, true);
```

---

## 📊 Profile Types

### Administrative Profiles

| Profile Name | Type | Modules | Description |
|--------------|------|---------|-------------|
| `master_admin` | System Admin | All | Complete system access |
| `admin_operacao` | Module Admin | imp, con*, exp* | Operational modules administrator |
| `admin_financeiro` | Module Admin | fin | Financial modules administrator |

### Operational Profiles

| Profile Name | Module | Access Level | Description |
|--------------|--------|--------------|-------------|
| `importacoes_completo` | imp | Full | Complete importation access |
| `operacoes_importacao_todas_paginas` | imp | Full | Complete operational importation access |
| `importacao_basico` | imp | Limited | Basic importation functions |
| `importacao_avancado` | imp | Advanced | Advanced importation functions |

### Financial Profiles

| Profile Name | Module | Access Level | Description |
|--------------|--------|--------------|-------------|
| `financeiro_completo` | fin | Full | Complete financial access |
| `financeiro_fluxo_de_caixa` | fin | Specific | Cash flow access only |
| `financeiro_basico` | fin | Limited | Basic financial functions |

### Future Profiles (Prepared)

| Profile Name | Module | Status | Description |
|--------------|--------|--------|-------------|
| `consultoria_completo` | con | Planned | Complete consultancy access |
| `exportacao_completo` | exp | Planned | Complete export access |

---

## 🏢 Module Structure

### Active Modules

#### Importação (imp)
**Pages**:
- `dashboard_executivo`: Executive Dashboard
- `dashboard_resumido`: Summary Dashboard  
- `documentos`: Document Conference
- `relatorio`: Report Export
- `agente`: Unique Agent

**Access Controlled By**: Admin Operacional

#### Financeiro (fin)
**Pages**:
- `fin_dashboard_executivo`: Financial Executive Dashboard
- `fluxo_caixa`: Cash Flow
- `despesas`: Expenses
- `faturamento`: Billing

**Access Controlled By**: Admin Financeiro

### Future Modules

#### Consultoria (con) - Prepared
**Status**: Infrastructure ready, UI hidden  
**Planned Pages**:
- `consultoria_dashboard`: Consultancy Dashboard
- `consultoria_processos`: Consultancy Processes

#### Exportação (exp) - Prepared  
**Status**: Infrastructure ready, UI hidden  
**Planned Pages**:
- `exportacao_dashboard`: Export Dashboard
- `exportacao_processos`: Export Processes

### System Modules
- **usuarios**: User Management (accessible by all admins)
- **perfis**: Profile Management (Master Admin only)

---

## 🔒 Access Control Rules

### 1. Role-Profile Hierarchy Rules
```
admin + master_admin          → Full System Access
interno_unique + admin_operacao → Operational Modules + User Management
interno_unique + admin_financeiro → Financial Modules + User Management  
interno_unique + basico        → Profile-based access
cliente_unique + basico        → Client access only
```

### 2. Module Access Rules
- **Master Admins**: Access to ALL modules
- **Admin Operacional**: Access to imp, con, exp, usuarios (NO fin)
- **Admin Financeiro**: Access to fin, usuarios (NO imp, con, exp)
- **Basic Users**: Access based on assigned profiles

### 3. Profile Assignment Rules
- **Master Admins**: Can assign ANY profile to ANY user
- **Admin Operacional**: Can assign operational profiles only (imp, con, exp related)
- **Admin Financeiro**: Can assign financial profiles only (fin related)
- **Basic Users**: Cannot assign profiles

### 4. User Management Rules
- **Master Admins**: Can edit ALL users
- **Module Admins**: Can edit basic users only (cannot edit other admins)
- **Basic Users**: Cannot edit other users

### 5. UI Visibility Rules
- **Profile Management**: Master Admins only
- **Admin Sections**: Hidden from Module Admins
- **Module Sections**: Visible based on user's module access
- **Navigation**: Dynamically filtered based on permissions

---

## ⚙️ Implementation Details

### Core Files Modified

#### Backend Services
```
services/perfil_access_service.py  - Access control logic
modules/auth/routes.py            - Authentication decorators
modules/usuarios/routes.py        - User management with validation
```

#### Frontend Components
```
templates/base.html                        - Sidebar visibility logic
modules/usuarios/templates/usuarios.html   - User management interface
modules/usuarios/static/js/script.js       - Profile handling logic
```

### Key Functions

#### Access Validation
```python
# perfil_access_service.py
@staticmethod
def get_user_accessible_modules():
    """Returns modules user can access based on profile"""
    
@staticmethod
def get_user_accessible_pages(modulo_codigo):
    """Returns pages user can access in specific module"""

@staticmethod
def get_user_admin_capabilities():
    """Returns admin capabilities based on profile"""
```

#### Profile Assignment Validation
```python
# usuarios/routes.py
def can_assign_perfil(editor_user, perfil_id):
    """Validates if user can assign specific profile"""
```

### Database Queries

#### User Profile Validation
```sql
-- Check user configuration
SELECT 
    email, role, perfil_principal,
    CASE 
        WHEN role = 'admin' AND perfil_principal = 'master_admin' THEN 'Master Admin'
        WHEN role = 'interno_unique' AND perfil_principal = 'admin_operacao' THEN 'Admin Operacional'
        WHEN role = 'interno_unique' AND perfil_principal = 'admin_financeiro' THEN 'Admin Financeiro'
        WHEN perfil_principal = 'basico' THEN 'Basic User'
        ELSE 'Check Configuration'
    END as admin_type
FROM users_dev WHERE is_active = true;
```

#### Admin Profile Lookup
```sql
-- Get admin profiles
SELECT * FROM users_perfis 
WHERE is_admin_profile = true 
ORDER BY modulo_codigo, perfil_nome;
```

---

## 🧪 Testing & Validation

### Test Cases

#### 1. Master Admin Testing
```
Login: system@uniqueaduaneira.com.br
Expected: Full access to all modules, user management, profile management
Test: Create users, assign any profiles, access all pages
```

#### 2. Admin Operacional Testing  
```
Login: lucas.vexani@uniqueaduaneira.com.br (after profile update)
Expected: Access to imp modules, user management (no profile management)
Test: Assign operational profiles, blocked from financial modules
```

#### 3. Admin Financeiro Testing
```
Login: financeiro@uniqueaduaneira.com.br (after profile update)  
Expected: Access to fin modules, user management (no profile management)
Test: Assign financial profiles, blocked from operational modules
```

#### 4. Profile Assignment Validation
```
Test: Admin Operacional tries to assign financial profile
Expected: Blocked with error message
Test: Admin Financeiro tries to assign operational profile  
Expected: Blocked with error message
```

### Validation Queries

#### System Health Check
```sql
-- Users needing profile updates
SELECT email, role, perfil_principal 
FROM users_dev 
WHERE (role = 'interno_unique' AND perfil_principal NOT IN ('basico', 'admin_operacao', 'admin_financeiro'))
   OR (role = 'admin' AND perfil_principal != 'master_admin')
   OR (role = 'cliente_unique' AND perfil_principal != 'basico');
```

#### Profile Consistency Check  
```sql
-- Check admin profile coverage
SELECT 
    modulo_codigo,
    COUNT(*) as profile_count,
    ARRAY_AGG(perfil_nome) as profiles
FROM users_perfis 
WHERE is_admin_profile = true 
GROUP BY modulo_codigo;
```

---

## 🚨 Troubleshooting

### Common Issues

#### Issue: Module not showing in navigation but accessible via direct URL
**Symptoms**: Module accessible via direct URL (e.g., `/export_relatorios/`) but not visible in sidebar/navigation  
**Causes**: 
- Module mapping mismatch between access service and template
- Template checking for different module name than service provides
- Missing module in accessible_modules list

**Solution**: 
Ensure both module names are added to accessible_modules for compatibility:
```python
# Add both names for compatibility
accessible_modules.add('relatorios')  # For sidebar compatibility  
accessible_modules.add('export_relatorios')  # For direct access
```

#### Issue: User shows "Check Configuration"
**Symptoms**: User appears in query with ⚠️ status  
**Causes**: 
- Old profile structure (admin_geral, admin_importacoes)
- Invalid role-profile combination
- Missing admin profiles

**Solution**:
```sql
-- Update to new structure
UPDATE users_dev SET perfil_principal = 'master_admin' 
WHERE role = 'admin' AND perfil_principal = 'admin_geral';

UPDATE users_dev SET perfil_principal = 'admin_operacao'
WHERE role = 'interno_unique' AND perfil_principal = 'admin_importacoes';
```

#### Issue: Module Admin can't assign profiles
**Symptoms**: Error when trying to assign profiles  
**Causes**: Profile not within admin's module scope
**Solution**: Verify profile belongs to admin's modules (imp/con/exp for operational, fin for financial)

#### Issue: User can't access expected modules  
**Symptoms**: Modules not visible in navigation
**Causes**: 
- Incorrect perfil_principal assignment
- Profile not linked to correct modules
- Access service misconfiguration

**Solution**: 
1. Verify user's perfil_principal matches intended role
2. Check profile exists in users_perfis table
3. Verify module mapping in perfil_access_service.py

#### Issue: Admin sees wrong interface sections
**Symptoms**: Module admin sees master admin elements
**Causes**: Template conditions checking wrong profile names
**Solution**: Update templates to use new profile names (master_admin, admin_operacao, admin_financeiro)

### Debug Commands

#### Check User Access
```python
# In Flask shell
from services.perfil_access_service import PerfilAccessService
from flask import session

# Simulate user session
session['user'] = {'role': 'interno_unique', 'perfil_principal': 'admin_operacao'}

# Check accessible modules
modules = PerfilAccessService.get_user_accessible_modules()
print(f"Accessible modules: {modules}")

# Check admin capabilities  
capabilities = PerfilAccessService.get_user_admin_capabilities()
print(f"Admin capabilities: {capabilities}")
```

#### Validate Profile Assignment
```python
from modules.usuarios.routes import can_assign_perfil

editor_user = {'role': 'interno_unique', 'perfil_principal': 'admin_operacao'}
can_assign = can_assign_perfil(editor_user, 'financeiro_completo')
print(f"Can assign financial profile: {can_assign}")  # Should be False
```

### Monitoring

#### Access Control Logs
Monitor browser console for access control messages:
```
[ACCESS_SERVICE] Master Admin (master_admin) - módulos disponíveis: [...]
[ACCESS_SERVICE] Module Admin (admin_operacao) - módulos disponíveis: [...]
[PERFIL_ASSIGNMENT_CHECK] Admin Operacional pode atribuir profile_name: true/false
```

#### Database Monitoring
```sql
-- Monitor profile assignments
SELECT 
    DATE(updated_at) as date,
    COUNT(*) as updates,
    COUNT(DISTINCT id) as users_updated
FROM users_dev 
WHERE updated_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(updated_at)
ORDER BY date DESC;
```

---

## 📝 Migration Notes

### From Previous System
The system was migrated from a binary admin structure to the new hierarchical system:

**Old Structure** → **New Structure**:
- `admin_geral` → `master_admin`
- `admin_importacoes` → `admin_operacao`  
- `admin_financeiro` → `admin_financeiro` (unchanged)

### Migration Steps Performed
1. Updated all code references to use new profile names
2. Enhanced database schema with `is_admin_profile` flag
3. Created new admin profiles for operational scope
4. Updated access control logic for module isolation
5. Modified UI templates for new admin structure
6. Added future module preparation (consultoria, exportacao)

### Post-Migration Validation
- ✅ All existing users maintain access levels
- ✅ New admin structure provides proper isolation
- ✅ Profile assignment validation works correctly
- ✅ UI renders appropriately for each user type
- ✅ Future modules ready for implementation

---

## 📋 Future Enhancements

### Planned Features
1. **Consultoria Module**: Complete implementation with dedicated profiles
2. **Exportação Module**: Complete implementation with dedicated profiles  
3. **Audit Logging**: Track all profile assignments and access attempts
4. **Time-based Access**: Temporary profile assignments with expiration
5. **API Access Control**: Extend profile validation to API endpoints

### Scalability Considerations
- **Role Inheritance**: Future parent-child role relationships
- **Dynamic Permissions**: Runtime permission modifications
- **Multi-tenant Support**: Client-specific admin hierarchies
- **External Integration**: LDAP/AD integration for enterprise environments

---

## 📞 Support & Maintenance

### Development Team Contacts
- **System Architecture**: Development Team
- **Database Administration**: Database Team  
- **User Support**: Support Team

### Documentation Updates
This document should be updated when:
- New modules are added
- Profile structure changes
- Access control rules are modified
- New admin levels are introduced

### Version History
- **v1.0**: Initial binary admin system
- **v2.0**: Hierarchical admin system with module isolation (Current)

---

**End of Documentation**

## 🚀 Database-Driven Profile System (NEW)

### **🆕 Automatic Profile Access**

The system now **automatically derives access from database profiles** instead of requiring hardcoded mappings for every new profile. This means:

✅ **No manual coding required** when creating new profiles  
✅ **Database-driven**: Profiles work immediately when created in `users_perfis` table  
✅ **Consistent mapping**: Same logic applied to all profiles automatically  
✅ **Maintainable**: Changes in database immediately reflect in access control  

### **How It Works**

1. **User logs in** with `perfil_principal = 'any_profile_name'`
2. **System looks up** profile in `users_perfis` table automatically
3. **Pages are mapped** to modules using `PAGE_TO_ENDPOINT_MAPPING`
4. **Sidebar compatibility** is added automatically for navigation
5. **Access granted** without any code changes

### **Example: Adding New Profile**

```sql
-- 1. Just create the profile in database
INSERT INTO users_perfis VALUES 
(41, 'new_custom_profile', 'imp', 'Importação', 
 '["dashboard_executivo", "relatorio", "agente"]', true, false);

-- 2. Assign to user
UPDATE users_dev SET perfil_principal = 'new_custom_profile' 
WHERE email = 'user@company.com';

-- 3. User automatically gets access to:
-- - dashboard_executivo module
-- - relatorios + export_relatorios modules (from "relatorio" page)
-- - agente module
-- No code changes needed!
```

### **Page-to-Module Mapping**

The system uses `PAGE_TO_ENDPOINT_MAPPING` to automatically convert database page codes to accessible modules:

```python
PAGE_TO_ENDPOINT_MAPPING = {
    'dashboard_executivo': 'dashboard_executivo',
    'dashboard_resumido': 'dash_importacoes_resumido', 
    'documentos': 'conferencia',
    'relatorio': 'export_relatorios',  # Also adds 'relatorios' for sidebar
    'agente': 'agente',
    'fin_dashboard_executivo': 'fin_dashboard_executivo',
    'fluxo_caixa': 'fluxo_de_caixa',
    'despesas': 'despesas_anual',
    'faturamento': 'faturamento_anual'
}
```

### **Legacy Support**

For profiles not found in database, the system falls back to legacy hardcoded mappings (currently only `financeiro_fluxo_de_caixa` and `financeiro_completo`), but **new profiles should always be database-driven**.

---

*This document serves as the authoritative reference for the Unique Aduaneira Portal access control system. Keep it updated as the system evolves.*