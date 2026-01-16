"""
Widgets, Dashboards, API, and Profile Blueprints
Complete route handlers for remaining functionality
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort, send_file
from flask_login import login_required, current_user
from functools import wraps
from models import Widget, Dashboard, DataSource, DashboardWidget, WidgetType, APIKey, db
from forms import WidgetForm, DashboardForm, DashboardWidgetAddForm, ProfileForm
from services import WidgetProcessor, ReportService, NotificationService
import json


def permission_required(permission_code):
    """Permission decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from services import AuthService
            if not AuthService.check_permission(current_user, permission_code):
                flash('You do not have permission to access this resource.', 'danger')
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================================
# WIDGETS BLUEPRINT
# ============================================================================

widgets_bp = Blueprint('widgets', __name__)


@widgets_bp.route('/')
@login_required
@permission_required('view_widgets')
def index():
    """List all widgets"""
    widgets_list = Widget.query.join(DataSource).filter(
        DataSource.organization_id == current_user.organization_id,
        Widget.is_active == True
    ).order_by(Widget.created_at.desc()).all()
    
    return render_template('widgets/index.html', widgets=widgets_list)


@widgets_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('create_widget')
def create():
    """Create new widget"""
    form = WidgetForm()
    
    # Populate data source choices
    form.data_source.choices = [
        (ds.id, ds.name) for ds in DataSource.query.filter_by(
            organization_id=current_user.organization_id,
            is_active=True
        ).all()
    ]
    
    if form.validate_on_submit():
        try:
            widget = Widget(
                name=form.name.data,
                reference=form.reference.data,
                description=form.description.data,
                widget_type=WidgetType[form.widget_type.data.upper()],
                title=form.title.data,
                subtitle=form.subtitle.data,
                icon=form.icon.data,
                color=form.color.data,
                data_source_id=form.data_source.data,
                query_type=form.query_type.data,
                show_kpi=form.show_kpi.data,
                auto_refresh=form.auto_refresh.data,
                refresh_interval=form.refresh_interval.data,
                is_active=form.is_active.data,
                is_template=form.is_template.data,
                created_by_id=current_user.id
            )
            
            # Parse JSON configurations
            if form.fields.data:
                widget.fields = json.loads(form.fields.data)
            if form.filters.data:
                widget.filters = json.loads(form.filters.data)
            if form.aggregations.data:
                widget.aggregations = json.loads(form.aggregations.data)
            if form.sorting.data:
                widget.sorting = json.loads(form.sorting.data)
            if form.display_config.data:
                widget.display_config = json.loads(form.display_config.data)
            if form.kpi_config.data:
                widget.kpi_config = json.loads(form.kpi_config.data)
            
            widget.limit = form.limit.data
            
            db.session.add(widget)
            db.session.commit()
            
            flash(f'Widget "{widget.name}" created successfully!', 'success')
            return redirect(url_for('widgets.view', id=widget.id))
            
        except json.JSONDecodeError as e:
            flash(f'Invalid JSON in configuration: {str(e)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating widget: {str(e)}', 'danger')
    
    return render_template('widgets/form.html', form=form, action='Create')


@widgets_bp.route('/<int:id>')
@login_required
@permission_required('view_widgets')
def view(id):
    """View widget details"""
    widget = Widget.query.get_or_404(id)
    
    # Check organization access
    if widget.data_source.organization_id != current_user.organization_id:
        abort(403)
    
    return render_template('widgets/view.html', widget=widget)


@widgets_bp.route('/<int:id>/preview')
@login_required
@permission_required('preview_widget')
def preview(id):
    """Preview widget with data"""
    widget = Widget.query.get_or_404(id)
    
    # Check organization access
    if widget.data_source.organization_id != current_user.organization_id:
        abort(403)
    
    try:
        result = WidgetProcessor.process_widget(widget)
        
        if result['success']:
            return render_template(
                'widgets/preview.html',
                widget=widget,
                data=result['data'],
                from_cache=result.get('from_cache', False)
            )
        else:
            flash(f'Error processing widget: {result.get("error")}', 'danger')
            return redirect(url_for('widgets.view', id=id))
            
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('widgets.view', id=id))


@widgets_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@permission_required('delete_widget')
def delete(id):
    """Delete widget"""
    widget = Widget.query.get_or_404(id)
    
    # Check organization access
    if widget.data_source.organization_id != current_user.organization_id:
        abort(403)
    
    try:
        widget_name = widget.name
        db.session.delete(widget)
        db.session.commit()
        
        flash(f'Widget "{widget_name}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting widget: {str(e)}', 'danger')
    
    return redirect(url_for('widgets.index'))



# ============================================================================
# DASHBOARDS BLUEPRINT
# ============================================================================

dashboards_bp = Blueprint('dashboards', __name__)


@dashboards_bp.route('/')
@login_required
@permission_required('view_dashboards')
def index():
    """List all dashboards"""
    dashboards_list = Dashboard.query.filter_by(
        organization_id=current_user.organization_id,
        is_active=True
    ).order_by(Dashboard.created_at.desc()).all()
    
    return render_template('dashboards/index.html', dashboards=dashboards_list)


@dashboards_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('create_dashboard')
def create():
    """Create new dashboard"""
    # Check organization limit
    if not current_user.organization.can_add_dashboard():
        flash(
            f'Organization has reached maximum dashboard limit ({current_user.organization.max_dashboards}).',
            'danger'
        )
        return redirect(url_for('dashboards.index'))
    
    form = DashboardForm()
    
    # Populate role choices
    from models import Role, Organization
    form.allowed_roles.choices = [
        (r.id, r.name) for r in Role.query.filter_by(is_active=True).all()
    ]
    
    # Get available widgets for initial selection
    available_widgets = Widget.query.join(DataSource).filter(
        DataSource.organization_id == current_user.organization_id,
        Widget.is_active == True
    ).all()
    
    # Get organizations for dropdown
    organizations = Organization.query.filter_by(is_active=True).all()
    
    if form.validate_on_submit():
        try:
            dashboard = Dashboard(
                name=form.name.data,
                slug=form.slug.data or form.name.data.lower().replace(' ', '-'),
                description=form.description.data,
                layout_type=form.layout_type.data,
                columns=form.columns.data,
                row_height=form.row_height.data,
                gap=form.gap.data,
                theme=form.theme.data,
                background_color=form.background_color.data,
                auto_refresh=form.auto_refresh.data,
                refresh_interval=form.refresh_interval.data,
                enable_filters=form.enable_filters.data,
                enable_export=form.enable_export.data,
                enable_fullscreen=form.enable_fullscreen.data,
                is_public=form.is_public.data,
                is_default=form.is_default.data,
                is_active=form.is_active.data,
                is_template=form.is_template.data,
                organization_id=current_user.organization_id,
                created_by_id=current_user.id
            )
            
            # Set allowed roles
            if form.allowed_roles.data:
                dashboard.allowed_roles = form.allowed_roles.data
            
            db.session.add(dashboard)
            db.session.flush()  # Get dashboard ID
            
            # Add selected widgets
            widget_ids = request.form.getlist('widget_ids')
            if widget_ids:
                for idx, widget_id in enumerate(widget_ids):
                    widget = Widget.query.get(int(widget_id))
                    if widget:
                        dashboard.add_widget(
                            widget=widget,
                            position_x=0,
                            position_y=idx,
                            width=4,
                            height=3
                        )
            
            db.session.commit()
            
            flash(f'Dashboard "{dashboard.name}" created successfully!', 'success')
            return redirect(url_for('dashboards.view', id=dashboard.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating dashboard: {str(e)}', 'danger')
    
    return render_template(
        'dashboards/form.html', 
        form=form, 
        action='Create',
        available_widgets=available_widgets,
        organizations=organizations
    )


@dashboards_bp.route('/<int:id>')
@login_required
@permission_required('view_dashboards')
def view(id):
    """View dashboard"""
    dashboard = Dashboard.query.get_or_404(id)
    
    # Check organization access
    if dashboard.organization_id != current_user.organization_id:
        abort(403)
    
    # Increment view count
    dashboard.increment_view_count()
    
    # Get all widgets with their data
    widgets_data = []
    for dw in dashboard.dashboard_widgets:
        try:
            result = WidgetProcessor.process_widget(dw.widget)
            if result['success']:
                widgets_data.append({
                    'dashboard_widget': dw,
                    'widget': dw.widget,
                    'data': result['data']
                })
        except Exception as e:
            # Log error but continue with other widgets
            print(f"Error processing widget {dw.widget.id}: {str(e)}")
    
    return render_template(
        'dashboards/view.html',
        dashboard=dashboard,
        widgets_data=widgets_data
    )


@dashboards_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('edit_dashboard')
def edit(id):
    """Edit dashboard"""
    dashboard = Dashboard.query.get_or_404(id)
    
    # Check organization access
    if dashboard.organization_id != current_user.organization_id:
        abort(403)
    
    # Handle archive action
    if request.method == 'POST' and request.form.get('status') == 'archived':
        try:
            dashboard.is_active = False
            db.session.commit()
            flash(f'Dashboard "{dashboard.name}" archived successfully!', 'success')
            return redirect(url_for('dashboards.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error archiving dashboard: {str(e)}', 'danger')
    
    # Widget add form
    add_widget_form = DashboardWidgetAddForm()
    add_widget_form.dashboard_id.data = dashboard.id
    
    # Populate widget choices
    add_widget_form.widget.choices = [
        (w.id, w.name) for w in Widget.query.join(DataSource).filter(
            DataSource.organization_id == current_user.organization_id,
            Widget.is_active == True
        ).all()
    ]
    
    if add_widget_form.validate_on_submit():
        try:
            widget = Widget.query.get(add_widget_form.widget.data)
            
            dashboard.add_widget(
                widget=widget,
                position_x=add_widget_form.position_x.data,
                position_y=add_widget_form.position_y.data,
                width=add_widget_form.width.data,
                height=add_widget_form.height.data
            )
            
            flash(f'Widget "{widget.name}" added to dashboard!', 'success')
            return redirect(url_for('dashboards.edit', id=id))
            
        except Exception as e:
            flash(f'Error adding widget: {str(e)}', 'danger')
    
    return render_template(
        'dashboards/edit.html',
        dashboard=dashboard,
        add_widget_form=add_widget_form
    )


@dashboards_bp.route('/<int:dashboard_id>/widget/<int:widget_id>/remove', methods=['POST'])
@login_required
@permission_required('edit_dashboard')
def remove_widget(dashboard_id, widget_id):
    """Remove widget from dashboard"""
    dashboard = Dashboard.query.get_or_404(dashboard_id)
    
    # Check organization access
    if dashboard.organization_id != current_user.organization_id:
        abort(403)
    
    try:
        dashboard_widget = DashboardWidget.query.filter_by(
            dashboard_id=dashboard_id,
            widget_id=widget_id
        ).first_or_404()
        
        widget_name = dashboard_widget.widget.name
        db.session.delete(dashboard_widget)
        db.session.commit()
        
        flash(f'Widget "{widget_name}" removed from dashboard!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing widget: {str(e)}', 'danger')
    
    return redirect(url_for('dashboards.edit', id=dashboard_id))


@dashboards_bp.route('/<int:id>/export')
@login_required
@permission_required('export_dashboard')
def export(id):
    """Export dashboard"""
    dashboard = Dashboard.query.get_or_404(id)
    
    # Check organization access
    if dashboard.organization_id != current_user.organization_id:
        abort(403)
    
    export_format = request.args.get('format', 'json')
    
    try:
        report = ReportService.generate_dashboard_report(
            dashboard=dashboard,
            format=export_format,
            include_data=True
        )
        
        mimetype_map = {
            'json': 'application/json',
            'csv': 'text/csv',
            'pdf': 'application/pdf'
        }
        
        return send_file(
            report,
            mimetype=mimetype_map.get(export_format, 'application/octet-stream'),
            as_attachment=True,
            download_name=f'{dashboard.slug}-export.{export_format}'
        )
        
    except Exception as e:
        flash(f'Error exporting dashboard: {str(e)}', 'danger')
        return redirect(url_for('dashboards.view', id=id))


@dashboards_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@permission_required('delete_dashboard')
def delete(id):
    """Delete dashboard"""
    dashboard = Dashboard.query.get_or_404(id)
    
    # Check organization access
    if dashboard.organization_id != current_user.organization_id:
        abort(403)
    
    try:
        dashboard_name = dashboard.name
        db.session.delete(dashboard)
        db.session.commit()
        
        flash(f'Dashboard "{dashboard_name}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting dashboard: {str(e)}', 'danger')
    
    return redirect(url_for('dashboards.index'))


# ============================================================================
# API BLUEPRINT
# ============================================================================

api_bp = Blueprint('api', __name__)


@api_bp.route('/widget/<int:id>/data')
@login_required
def widget_data(id):
    """Get widget data (API endpoint)"""
    widget = Widget.query.get_or_404(id)
    
    # Check organization access
    if widget.data_source.organization_id != current_user.organization_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        result = WidgetProcessor.process_widget(widget)
        
        if result['success']:
            return jsonify({
                'success': True,
                'widget': result['widget'],
                'data': result['data'],
                'from_cache': result.get('from_cache', False)
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error')
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/dashboard/<int:id>/data')
@login_required
def dashboard_data(id):
    """Get all dashboard widgets data (API endpoint)"""
    dashboard = Dashboard.query.get_or_404(id)
    
    # Check organization access
    if dashboard.organization_id != current_user.organization_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        widgets_data = {}
        
        for dw in dashboard.dashboard_widgets:
            result = WidgetProcessor.process_widget(dw.widget)
            if result['success']:
                widgets_data[dw.widget.id] = {
                    'widget': result['widget'],
                    'data': result['data'],
                    'position': {
                        'x': dw.position_x,
                        'y': dw.position_y,
                        'width': dw.width,
                        'height': dw.height
                    }
                }
        
        return jsonify({
            'success': True,
            'dashboard': dashboard.to_dict(),
            'widgets': widgets_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
    # ============================================================================
# PROFILE BLUEPRINT
# ============================================================================

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """User profile settings"""
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        try:
            current_user.first_name = form.first_name.data
            current_user.last_name = form.last_name.data
            current_user.phone = form.phone.data
            current_user.job_title = form.job_title.data
            current_user.department = form.department.data
            current_user.language = form.language.data
            current_user.timezone = form.timezone.data
            current_user.email_notifications = form.email_notifications.data
            current_user.sms_notifications = form.sms_notifications.data
            
            db.session.commit()
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile.settings'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
    
    return render_template('profile/settings.html', form=form)


@profile_bp.route('/activity')
@login_required
def activity():
    """User activity log"""
    from models import AuditLog
    
    logs = AuditLog.query.filter_by(
        user_id=current_user.id
    ).order_by(AuditLog.created_at.desc()).limit(50).all()
    
    return render_template('profile/activity.html', logs=logs)


@profile_bp.route('/api-keys')
@login_required
def api_keys():
    """User API keys"""
    keys = APIKey.query.filter_by(
        organization_id=current_user.organization_id
    ).order_by(APIKey.created_at.desc()).all()
    
    return render_template('profile/api_keys.html', api_keys=keys)


@profile_bp.route('/api-keys/create', methods=['POST'])
@login_required
def create_api_key():
    """Generate new API key"""
    name = request.form.get('name')
    
    if not name:
        flash('API key name is required.', 'danger')
        return redirect(url_for('profile.api_keys'))
    
    try:
        api_key, key_string = APIKey.generate(
            name=name,
            organization=current_user.organization,
            created_by=current_user,
            scopes=['read_dashboards', 'read_widgets'],
            expires_in_days=365
        )
        
        flash(
            f'API Key created! Save this key securely, it will not be shown again: {key_string}',
            'success'
        )
        
    except Exception as e:
        flash(f'Error creating API key: {str(e)}', 'danger')
    
    return redirect(url_for('profile.api_keys'))


@profile_bp.route('/api-keys/<int:id>/delete', methods=['POST'])
@login_required
def delete_api_key(id):
    """Delete API key"""
    api_key = APIKey.query.get_or_404(id)
    
    # Check organization access
    if api_key.organization_id != current_user.organization_id:
        abort(403)
    
    try:
        key_name = api_key.name
        db.session.delete(api_key)
        db.session.commit()
        
        flash(f'API key "{key_name}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting API key: {str(e)}', 'danger')
    
    return redirect(url_for('profile.api_keys'))