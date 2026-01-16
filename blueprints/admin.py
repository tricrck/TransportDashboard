"""
Main and Admin Blueprints
Main dashboard and administrative functions
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from functools import wraps
from models import (
    Organization, User, Role, Permission,
    Dashboard, Widget, DataSource, AuditLog, db
)
from forms import (
    OrganizationForm, UserForm, UserEditForm,
    RoleForm, PermissionForm
)
from services import AuthService, NotificationService


# ============================================================================
# DECORATORS
# ============================================================================

def permission_required(permission_code):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            if not AuthService.check_permission(current_user, permission_code):
                flash('You do not have permission to access this resource.', 'danger')
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================================
# MAIN BLUEPRINT
# ============================================================================

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page - redirect based on authentication"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page"""
    # Get user's default dashboard or organization default
    default_dashboard = Dashboard.query.filter_by(
        organization_id=current_user.organization_id,
        is_default=True,
        is_active=True
    ).first()
    
    # Get user statistics
    stats = {
        'dashboards': Dashboard.query.filter_by(
            organization_id=current_user.organization_id,
            is_active=True
        ).count(),
        'widgets': Widget.query.join(DataSource).filter(
            DataSource.organization_id == current_user.organization_id,
            Widget.is_active == True
        ).count(),
        'data_sources': DataSource.query.filter_by(
            organization_id=current_user.organization_id,
            is_active=True
        ).count()
    }
    
    # Get recent dashboards
    recent_dashboards = Dashboard.query.filter_by(
        organization_id=current_user.organization_id,
        is_active=True
    ).order_by(Dashboard.last_viewed.desc()).limit(5).all()
    
    return render_template(
        'main/dashboard.html',
        default_dashboard=default_dashboard,
        stats=stats,
        recent_dashboards=recent_dashboards
    )


@main_bp.route('/search')
@login_required
def search():
    """Search functionality"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return redirect(url_for('main.dashboard'))
    
    # Search dashboards
    dashboards = Dashboard.query.filter(
        Dashboard.organization_id == current_user.organization_id,
        Dashboard.is_active == True,
        Dashboard.name.ilike(f'%{query}%')
    ).limit(10).all()
    
    # Search widgets
    widgets = Widget.query.join(DataSource).filter(
        DataSource.organization_id == current_user.organization_id,
        Widget.is_active == True,
        Widget.name.ilike(f'%{query}%')
    ).limit(10).all()
    
    # Search data sources
    data_sources = DataSource.query.filter(
        DataSource.organization_id == current_user.organization_id,
        DataSource.is_active == True,
        DataSource.name.ilike(f'%{query}%')
    ).limit(10).all()
    
    return render_template(
        'main/search_results.html',
        query=query,
        dashboards=dashboards,
        widgets=widgets,
        data_sources=data_sources
    )


@main_bp.route('/notifications')
@login_required
def notifications():
    """User notifications page"""
    from services import NotificationService
    
    notifications = NotificationService.get_user_notifications(
        user=current_user,
        unread_only=False,
        limit=50
    )
    
    return render_template('main/notifications.html', notifications=notifications)


@main_bp.route('/notifications/<int:notification_id>/mark-read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    from models import Notification
    
    notification = Notification.query.get_or_404(notification_id)
    
    if notification.user_id != current_user.id:
        abort(403)
    
    notification.mark_as_read()
    
    return redirect(url_for('main.notifications'))


# ============================================================================
# ADMIN BLUEPRINT
# ============================================================================

admin_bp = Blueprint('admin', __name__)


# Organizations
# ----------------------------------------------------------------------------

@admin_bp.route('/organizations')
@login_required
@permission_required('view_organizations')
def organizations():
    """List all organizations"""
    orgs = Organization.query.order_by(Organization.name).all()
    return render_template('admin/organizations.html', organizations=orgs)


@admin_bp.route('/organizations/create', methods=['GET', 'POST'])
@login_required
@permission_required('create_organization')
def create_organization():
    """Create new organization"""
    form = OrganizationForm()
    
    if form.validate_on_submit():
        try:
            org = Organization(
                name=form.name.data,
                code=form.code.data.upper(),
                org_type=form.org_type.data,
                description=form.description.data,
                mission=form.mission.data,
                vision=form.vision.data,
                email=form.email.data,
                phone=form.phone.data,
                website=form.website.data,
                primary_color=form.primary_color.data,
                secondary_color=form.secondary_color.data,
                subscription_tier=form.subscription_tier.data,
                max_users=form.max_users.data,
                max_dashboards=form.max_dashboards.data,
                max_data_sources=form.max_data_sources.data,
                is_active=form.is_active.data
            )
            
            db.session.add(org)
            db.session.commit()
            
            # Log action
            AuditLog.log(
                action='create',
                user=current_user,
                resource_type='organization',
                resource_id=org.id,
                description=f'Created organization: {org.name}'
            )
            
            flash(f'Organization "{org.name}" created successfully!', 'success')
            return redirect(url_for('admin.organizations'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating organization: {str(e)}', 'danger')
    
    return render_template('admin/organization_form.html', form=form, action='Create')


@admin_bp.route('/organizations/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('edit_organization')
def edit_organization(id):
    """Edit organization"""
    org = Organization.query.get_or_404(id)
    form = OrganizationForm(obj=org, original_code=org.code)
    
    if form.validate_on_submit():
        try:
            org.name = form.name.data
            org.code = form.code.data.upper()
            org.org_type = form.org_type.data
            org.description = form.description.data
            org.mission = form.mission.data
            org.vision = form.vision.data
            org.email = form.email.data
            org.phone = form.phone.data
            org.website = form.website.data
            org.primary_color = form.primary_color.data
            org.secondary_color = form.secondary_color.data
            org.subscription_tier = form.subscription_tier.data
            org.max_users = form.max_users.data
            org.max_dashboards = form.max_dashboards.data
            org.max_data_sources = form.max_data_sources.data
            org.is_active = form.is_active.data
            
            db.session.commit()
            
            # Log action
            AuditLog.log(
                action='update',
                user=current_user,
                resource_type='organization',
                resource_id=org.id,
                description=f'Updated organization: {org.name}'
            )
            
            flash(f'Organization "{org.name}" updated successfully!', 'success')
            return redirect(url_for('admin.organizations'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating organization: {str(e)}', 'danger')
    
    return render_template('admin/organization_form.html', form=form, action='Edit', organization=org)


@admin_bp.route('/organizations/<int:id>/delete', methods=['POST'])
@login_required
@permission_required('delete_organization')
def delete_organization(id):
    """Delete organization"""
    org = Organization.query.get_or_404(id)
    
    # Prevent deleting system organization
    if org.code == 'SYSTEM':
        flash('Cannot delete system organization.', 'danger')
        return redirect(url_for('admin.organizations'))
    
    try:
        org_name = org.name
        db.session.delete(org)
        db.session.commit()
        
        flash(f'Organization "{org_name}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting organization: {str(e)}', 'danger')
    
    return redirect(url_for('admin.organizations'))


# Users
# ----------------------------------------------------------------------------

@admin_bp.route('/users')
@login_required
@permission_required('view_users')
def users():
    """List users"""
    # Filter by organization if not superuser
    if current_user.is_superuser:
        users_query = User.query
    else:
        users_query = User.query.filter_by(organization_id=current_user.organization_id)
    
    # Filter parameters
    status = request.args.get('status')
    role_id = request.args.get('role_id')
    search = request.args.get('search')
    
    if status == 'active':
        users_query = users_query.filter_by(is_active=True)
    elif status == 'inactive':
        users_query = users_query.filter_by(is_active=False)
    
    if role_id:
        users_query = users_query.filter_by(role_id=int(role_id))
    
    if search:
        users_query = users_query.filter(
            db.or_(
                User.email.ilike(f'%{search}%'),
                User.first_name.ilike(f'%{search}%'),
                User.last_name.ilike(f'%{search}%')
            )
        )
    
    users_list = users_query.order_by(User.created_at.desc()).all()
    roles = Role.query.filter_by(is_active=True).all()
    
    return render_template('admin/users.html', users=users_list, roles=roles)


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@permission_required('create_user')
def create_user():
    """Create new user"""
    form = UserForm()
    
    # Populate choices
    if current_user.is_superuser:
        form.organization.choices = [
            (o.id, o.name) for o in Organization.query.filter_by(is_active=True).all()
        ]
    else:
        form.organization.choices = [
            (current_user.organization_id, current_user.organization.name)
        ]
    
    form.role.choices = [
        (r.id, r.name) for r in Role.query.filter_by(is_active=True).all()
    ]
    
    if form.validate_on_submit():
        try:
            # Check organization user limit
            org = Organization.query.get(form.organization.data)
            if not org.can_add_user():
                flash(f'Organization has reached maximum user limit ({org.max_users}).', 'danger')
                return render_template('admin/user_form.html', form=form, action='Create')
            
            user = User(
                email=form.email.data.lower(),
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                phone=form.phone.data,
                job_title=form.job_title.data,
                department=form.department.data,
                employee_id=form.employee_id.data,
                organization_id=form.organization.data,
                role_id=form.role.data,
                is_active=form.is_active.data,
                email_notifications=form.email_notifications.data,
                created_by_id=current_user.id
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            # Log action
            AuditLog.log(
                action='create',
                user=current_user,
                resource_type='user',
                resource_id=user.id,
                description=f'Created user: {user.email}'
            )
            
            # Send welcome notification
            NotificationService.create_notification(
                user=user,
                title='Welcome to Kenya Transport Analytics',
                message='Your account has been created successfully.',
                notification_type='success'
            )
            
            flash(f'User "{user.email}" created successfully!', 'success')
            return redirect(url_for('admin.users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'danger')
    
    return render_template('admin/user_form.html', form=form, action='Create')


@admin_bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('edit_user')
def edit_user(id):
    """Edit user"""
    user = User.query.get_or_404(id)
    
    # Check permission (can only edit users in same organization unless superuser)
    if not current_user.is_superuser and user.organization_id != current_user.organization_id:
        abort(403)
    
    form = UserEditForm(obj=user, original_email=user.email)
    
    # Populate choices
    if current_user.is_superuser:
        form.organization.choices = [
            (o.id, o.name) for o in Organization.query.filter_by(is_active=True).all()
        ]
    else:
        form.organization.choices = [
            (current_user.organization_id, current_user.organization.name)
        ]
    
    form.role.choices = [
        (r.id, r.name) for r in Role.query.filter_by(is_active=True).all()
    ]
    
    if form.validate_on_submit():
        try:
            user.email = form.email.data.lower()
            user.first_name = form.first_name.data
            user.last_name = form.last_name.data
            user.phone = form.phone.data
            user.job_title = form.job_title.data
            user.department = form.department.data
            user.employee_id = form.employee_id.data
            user.organization_id = form.organization.data
            user.role_id = form.role.data
            user.is_active = form.is_active.data
            user.two_fa_enabled = form.two_fa_enabled.data
            user.email_notifications = form.email_notifications.data
            user.sms_notifications = form.sms_notifications.data
            
            db.session.commit()
            
            # Log action
            AuditLog.log(
                action='update',
                user=current_user,
                resource_type='user',
                resource_id=user.id,
                description=f'Updated user: {user.email}'
            )
            
            flash(f'User "{user.email}" updated successfully!', 'success')
            return redirect(url_for('admin.users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'danger')
    
    return render_template('admin/user_form.html', form=form, action='Edit', user=user)


@admin_bp.route('/users/<int:id>/delete', methods=['POST'])
@login_required
@permission_required('delete_user')
def delete_user(id):
    """Delete user"""
    user = User.query.get_or_404(id)
    
    # Check permission
    if not current_user.is_superuser and user.organization_id != current_user.organization_id:
        abort(403)
    
    # Prevent self-deletion
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users'))
    
    try:
        user_email = user.email
        db.session.delete(user)
        db.session.commit()
        
        flash(f'User "{user_email}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('admin.users'))


# Roles
# ----------------------------------------------------------------------------

@admin_bp.route('/roles')
@login_required
@permission_required('view_roles')
def roles():
    """List roles"""
    roles_list = Role.query.order_by(Role.level.desc()).all()
    return render_template('admin/roles.html', roles=roles_list)


@admin_bp.route('/roles/<int:id>')
@login_required
@permission_required('view_roles')
def view_role(id):
    """View role details"""
    role = Role.query.get_or_404(id)
    return render_template('admin/role_detail.html', role=role)

@admin_bp.route('/audit-logs')
@login_required
@permission_required('view_audit_logs')
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(500).all()
    return render_template('admin/audit_logs.html', logs=logs)