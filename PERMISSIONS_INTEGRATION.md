# Permissions System Integration Guide

## Current Status

**The permissions are currently "dummy data"** - they can be assigned to employees through the Users & Roles interface, but they are **NOT being enforced** in the actual routes. The system still uses role-based access control only.

## What's Implemented

✅ **Database Table**: `employee_permissions` table created
✅ **UI Interface**: Users & Roles page with permission assignment modal
✅ **API Routes**: 
   - `/users-roles/get-permissions/<employee_id>` - Get permissions
   - `/users-roles/update-permissions/<employee_id>` - Update permissions
✅ **Helper Functions**: `has_permission()` and `check_permission_or_role()` functions created

## What's Missing

❌ **Permission Enforcement**: Routes don't check permissions yet
❌ **Integration**: Permission checks not integrated into existing routes

## Permission Keys Available

The system has 29 permissions organized into 6 categories:

### Student Management
- `view_students` - View student information and records
- `add_students` - Add new students to the system
- `edit_students` - Edit existing student information
- `delete_students` - Remove students from the system
- `view_student_fees` - View student fee information

### Staff Management
- `view_staff` - View staff member information
- `add_staff` - Add new staff members
- `edit_staff` - Edit staff member information
- `delete_staff` - Remove staff members
- `manage_salaries` - View and manage staff salaries

### Financial Management
- `view_fees` - View fee structures and information
- `manage_fees` - Create and edit fee structures
- `view_financial_reports` - Access financial reports and analytics
- `generate_invoices` - Create and generate invoices
- `process_payments` - Record and process payments

### Academic Management
- `view_academic_levels` - View academic levels and grades
- `manage_academic_levels` - Create and edit academic levels
- `view_exams` - View exam information
- `manage_exams` - Create and edit exams
- `view_results` - View exam and academic results

### System Administration
- `view_database` - Access database management tools
- `manage_backups` - Create and restore database backups
- `system_settings` - Access and modify system settings
- `manage_users` - Manage user accounts and permissions
- `view_audit_logs` - View system audit trails and logs

### Reports & Analytics
- `view_reports` - View system reports
- `generate_reports` - Generate custom reports
- `export_data` - Export data to various formats
- `view_analytics` - Access analytics and insights

## How to Integrate Permissions

### Option 1: Hybrid Approach (Recommended)
Keep role-based access as fallback, but check permissions first:

```python
@app.route('/student-management')
@login_required
def student_management():
    user_role = session.get('role', '').lower()
    employee_id = session.get('employee_id') or session.get('user_id')
    
    # Check permission OR role
    has_access = check_permission_or_role('view_students', 
                                         allowed_roles=['principal', 'super admin', 'technician'])
    
    if not has_access:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('dashboard_employee'))
    
    # ... rest of route code
```

### Option 2: Permission-Only Approach
Replace role checks with permission checks:

```python
@app.route('/student-management')
@login_required
def student_management():
    employee_id = session.get('employee_id') or session.get('user_id')
    
    if not has_permission(employee_id, 'view_students'):
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('dashboard_employee'))
    
    # ... rest of route code
```

## Routes That Need Permission Integration

1. **Student Management** (`/student-management`)
   - `view_students` - to view
   - `add_students` - to add
   - `edit_students` - to edit
   - `delete_students` - to delete

2. **Staff Management** (`/staff-management`)
   - `view_staff` - to view
   - `add_staff` - to add
   - `edit_staff` - to edit
   - `delete_staff` - to delete

3. **Student Fees** (`/dashboard/employee/student-fees`)
   - `view_student_fees` - to view
   - `manage_fees` - to manage

4. **Staff & Salaries** (`/dashboard/employee/staff-and-salaries`)
   - `manage_salaries` - to access

5. **Database Management** (`/database`)
   - `view_database` - to view

6. **Backup & Restore** (`/database/backup-restore`)
   - `manage_backups` - to access

7. **System Settings** (`/system-settings`)
   - `system_settings` - to access

8. **Users & Roles** (`/users-roles`)
   - `manage_users` - to access

## Next Steps

To make permissions functional:

1. **Integrate permission checks** into all protected routes
2. **Update route decorators** to check permissions
3. **Test permission system** with different users
4. **Document permission requirements** for each route

## Helper Functions Available

- `has_permission(employee_id, permission_key)` - Check if employee has specific permission
- `check_permission_or_role(permission_key, allowed_roles)` - Check permission OR role (hybrid)

## Note

Currently, **technicians have all permissions by default** (hardcoded in the helper functions). This can be changed if needed.








