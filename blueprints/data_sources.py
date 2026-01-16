"""
Data Sources Routes - Enhanced
Complete CRUD with background refresh, schema inference, and validation
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import DataSource, DataSourceType, AuthType, DataFormat, db
from forms.data_source import (
    APIDataSourceForm, UploadDataSourceForm, LinkDataSourceForm,
    DatabaseDataSourceForm, ValidationRuleForm, SchemaInferenceForm,
    QueryDataSourceForm
)
from services import DataFetcher, NotificationService
from tasks.data_refresh import refresh_data_source_task  # Celery task
from functools import wraps
import os
import hashlib
import json

data_sources_bp = Blueprint('data_sources', __name__)


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


@data_sources_bp.route('/')
@login_required
@permission_required('view_data_sources')
def index():
    """List all data sources with filtering"""
    sources = DataSource.query.filter_by(
        organization_id=current_user.organization_id,
        deleted_at=None
    ).order_by(DataSource.created_at.desc()).all()
    
    # Apply filters
    status = request.args.get('status')
    source_type = request.args.get('type')
    health = request.args.get('health')
    format_filter = request.args.get('format')
    
    if status == 'active':
        sources = [s for s in sources if s.is_active]
    elif status == 'inactive':
        sources = [s for s in sources if not s.is_active]
    
    if source_type:
        sources = [s for s in sources if s.source_type.value == source_type]
    
    if health:
        sources = [s for s in sources if s.health_status == health]
    
    if format_filter:
        sources = [s for s in sources if s.data_format.value == format_filter]
    
    return render_template('data_sources/index.html', data_sources=sources)


@data_sources_bp.route('/create')
@login_required
@permission_required('create_data_source')
def create():
    """Select data source type"""
    return render_template('data_sources/create_select.html')


@data_sources_bp.route('/create/api', methods=['GET', 'POST'])
@login_required
@permission_required('create_data_source')
def create_api():
    """Create API data source"""
    if not current_user.organization.can_add_data_source():
        flash(
            f'Organization has reached maximum data source limit ({current_user.organization.max_data_sources}).',
            'danger'
        )
        return redirect(url_for('data_sources.index'))
    
    form = APIDataSourceForm()
    
    if form.validate_on_submit():
        try:
            # Parse JSON fields
            api_params = json.loads(form.api_params.data) if form.api_params.data else None
            api_headers = json.loads(form.api_headers.data) if form.api_headers.data else None
            api_body = form.api_body.data if form.api_body.data else None
            
            # Create data source
            ds = DataSource(
                name=form.name.data,
                reference=form.reference.data,
                description=form.description.data,
                source_type=DataSourceType.API,
                data_format=DataFormat[form.data_format.data.upper()],
                api_endpoint=form.api_endpoint.data,
                api_method=form.api_method.data,
                api_params=api_params,
                api_headers=api_headers,
                api_body=api_body,
                api_timeout=form.api_timeout.data,
                auth_type=AuthType[form.auth_type.data.upper()],
                data_path=form.data_path.data,
                auto_refresh=form.auto_refresh.data,
                refresh_frequency=form.refresh_frequency.data,
                cache_enabled=form.cache_enabled.data,
                cache_ttl=form.cache_ttl.data,
                validation_enabled=form.validation_enabled.data,
                alert_on_failure=form.alert_on_failure.data,
                alert_threshold=form.alert_threshold.data,
                is_active=form.is_active.data,
                organization_id=current_user.organization_id,
                created_by_id=current_user.id
            )
            
            # Set authentication credentials
            if form.auth_type.data == 'basic':
                ds.auth_username = form.auth_username.data
                ds.auth_password = form.auth_password.data
            elif form.auth_type.data in ['bearer', 'api_key', 'query_param']:
                ds.auth_token = form.auth_token.data
            
            db.session.add(ds)
            db.session.commit()
            
            # Test connection and infer schema
            test_result = DataFetcher.test_connection(ds)
            
            if test_result['success']:
                # Infer schema from test data
                if test_result.get('data'):
                    ds.infer_schema(test_result['data'])
                    db.session.commit()
                
                flash(
                    f'Data source "{ds.name}" created successfully! Response time: {test_result["response_time"]:.0f}ms',
                    'success'
                )
            else:
                flash(
                    f'Data source "{ds.name}" created but connection test failed: {test_result["message"]}',
                    'warning'
                )
            
            return redirect(url_for('data_sources.view', id=ds.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error creating API data source: {str(e)}')
            flash(f'Error creating data source: {str(e)}', 'danger')
    
    return render_template('data_sources/api_form.html', form=form)


@data_sources_bp.route('/create/upload', methods=['GET', 'POST'])
@login_required
@permission_required('create_data_source')
def create_upload():
    """Create upload data source with auto-format detection"""
    if not current_user.organization.can_add_data_source():
        flash(
            f'Organization has reached maximum data source limit ({current_user.organization.max_data_sources}).',
            'danger'
        )
        return redirect(url_for('data_sources.index'))
    
    form = UploadDataSourceForm()
    
    if form.validate_on_submit():
        try:
            file = form.file.data
            filename = secure_filename(file.filename)
            
            # Create upload directory
            upload_dir = os.path.join('uploads', str(current_user.organization_id))
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename with hash
            file_content = file.read()
            file_hash = hashlib.sha256(file_content).hexdigest()
            file_ext = os.path.splitext(filename)[1]
            unique_filename = f"{file_hash[:16]}_{filename}"
            filepath = os.path.join(upload_dir, unique_filename)
            
            # Save file
            with open(filepath, 'wb') as f:
                f.write(file_content)
            
            # Auto-detect format if requested
            if form.data_format.data == 'auto':
                detected_format, mime_type = DataSource.detect_format_from_file(filepath)
                data_format = detected_format if detected_format else DataFormat.JSON
            else:
                data_format = DataFormat[form.data_format.data.upper()]
                mime_type = None
            
            # Create data source
            ds = DataSource(
                name=form.name.data,
                reference=form.reference.data,
                description=form.description.data,
                source_type=DataSourceType.UPLOAD,
                data_format=data_format,
                detected_format=detected_format if form.data_format.data == 'auto' else None,
                mime_type=mime_type,
                file_path=filepath,
                file_size=len(file_content),
                file_hash=file_hash,
                auto_refresh=False,
                cache_enabled=form.cache_enabled.data,
                cache_ttl=form.cache_ttl.data,
                validation_enabled=form.validation_enabled.data,
                alert_on_failure=form.alert_on_failure.data,
                is_active=form.is_active.data,
                organization_id=current_user.organization_id,
                created_by_id=current_user.id
            )
            
            db.session.add(ds)
            db.session.commit()
            
            # Fetch data and infer schema
            fetch_result = DataFetcher.fetch_data(ds, force_refresh=True)
            
            if fetch_result['success']:
                # Infer schema
                ds.infer_schema(fetch_result['data'])
                db.session.commit()
                
                flash(
                    f'File uploaded successfully! Format: {data_format.value.upper()}, Records: {fetch_result.get("record_count", 0)}',
                    'success'
                )
            else:
                flash(
                    f'File uploaded but error processing: {fetch_result.get("error")}',
                    'warning'
                )
            
            return redirect(url_for('data_sources.view', id=ds.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error uploading file: {str(e)}')
            flash(f'Error uploading file: {str(e)}', 'danger')
    
    return render_template('data_sources/upload_form.html', form=form)


@data_sources_bp.route('/create/link', methods=['GET', 'POST'])
@login_required
@permission_required('create_data_source')
def create_link():
    """Create link-based data source"""
    if not current_user.organization.can_add_data_source():
        flash(
            f'Organization has reached maximum data source limit.',
            'danger'
        )
        return redirect(url_for('data_sources.index'))
    
    form = LinkDataSourceForm()
    
    if form.validate_on_submit():
        try:
            # Determine format
            if form.data_format.data == 'auto':
                # Try to detect from URL extension
                ext = os.path.splitext(form.file_url.data)[1].lower()
                ext_map = {
                    '.json': DataFormat.JSON,
                    '.csv': DataFormat.CSV,
                    '.xml': DataFormat.XML,
                    '.xlsx': DataFormat.EXCEL,
                    '.parquet': DataFormat.PARQUET,
                }
                data_format = ext_map.get(ext, DataFormat.JSON)
            else:
                data_format = DataFormat[form.data_format.data.upper()]
            
            # Create data source
            ds = DataSource(
                name=form.name.data,
                reference=form.reference.data,
                description=form.description.data,
                source_type=DataSourceType.LINK,
                data_format=data_format,
                file_url=form.file_url.data,
                auth_type=AuthType[form.auth_type.data.upper()] if form.requires_auth.data else AuthType.NONE,
                auto_refresh=form.auto_refresh.data,
                refresh_frequency=form.refresh_frequency.data,
                cache_enabled=form.cache_enabled.data,
                cache_ttl=form.cache_ttl.data,
                validation_enabled=form.validation_enabled.data,
                is_active=form.is_active.data,
                organization_id=current_user.organization_id,
                created_by_id=current_user.id
            )
            
            # Set credentials if required
            if form.requires_auth.data:
                if form.auth_type.data == 'basic':
                    ds.auth_username = form.auth_username.data
                    ds.auth_password = form.auth_password.data
                elif form.auth_type.data in ['bearer', 'api_key']:
                    ds.auth_token = form.auth_token.data
            
            db.session.add(ds)
            db.session.commit()
            
            # Test connection
            test_result = DataFetcher.test_connection(ds)
            
            if test_result['success']:
                ds.infer_schema(test_result.get('data'))
                db.session.commit()
                flash(f'Link data source created successfully!', 'success')
            else:
                flash(f'Data source created but connection failed: {test_result["message"]}', 'warning')
            
            return redirect(url_for('data_sources.view', id=ds.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error creating link data source: {str(e)}')
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('data_sources/link_form.html', form=form)


@data_sources_bp.route('/create/database', methods=['GET', 'POST'])
@login_required
@permission_required('create_data_source')
def create_database():
    """Create database connection data source"""
    if not current_user.organization.can_add_data_source():
        flash('Organization has reached maximum data source limit.', 'danger')
        return redirect(url_for('data_sources.index'))
    
    form = DatabaseDataSourceForm()
    
    if form.validate_on_submit():
        try:
            # Build connection string
            conn_str = f"{form.db_type.data}://{form.db_username.data}:{form.db_password.data}@{form.db_host.data}:{form.db_port.data}/{form.db_name.data}"
            
            ds = DataSource(
                name=form.name.data,
                reference=form.reference.data,
                description=form.description.data,
                source_type=DataSourceType.DATABASE,
                data_format=DataFormat.JSON,
                db_type=form.db_type.data,
                db_host=form.db_host.data,
                db_port=form.db_port.data,
                db_name=form.db_name.data,
                db_username=form.db_username.data,
                db_password=form.db_password.data,
                db_schema=form.db_schema.data,
                db_table=form.db_table.data,
                query_string=form.query_string.data,
                db_connection_string=conn_str,
                auto_refresh=form.auto_refresh.data,
                refresh_frequency=form.refresh_frequency.data,
                cache_enabled=form.cache_enabled.data,
                is_active=form.is_active.data,
                organization_id=current_user.organization_id,
                created_by_id=current_user.id
            )
            
            db.session.add(ds)
            db.session.commit()
            
            # Test connection
            test_result = DataFetcher.test_connection(ds)
            
            if test_result['success']:
                flash('Database connection created successfully!', 'success')
            else:
                flash(f'Connection created but test failed: {test_result["message"]}', 'warning')
            
            return redirect(url_for('data_sources.view', id=ds.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error creating database connection: {str(e)}')
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('data_sources/database_form.html', form=form)


@data_sources_bp.route('/<int:id>')
@login_required
@permission_required('view_data_sources')
def view(id):
    """View data source details with schema and health"""
    ds = DataSource.query.get_or_404(id)
    
    if ds.organization_id != current_user.organization_id:
        abort(403)
    
    # Get recent refresh logs
    from models import DataRefreshLog
    refresh_logs = DataRefreshLog.query.filter_by(
        data_source_id=ds.id
    ).order_by(DataRefreshLog.started_at.desc()).limit(20).all()
    
    # Get widgets using this data source
    widgets = ds.widgets.filter_by(is_active=True).all()
    
    return render_template(
        'data_sources/view.html',
        data_source=ds,
        refresh_logs=refresh_logs,
        widgets=widgets
    )


@data_sources_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('edit_data_source')
def edit(id):
    """Edit data source"""
    ds = DataSource.query.get_or_404(id)
    
    if ds.organization_id != current_user.organization_id:
        abort(403)
    
    # Select form based on source type
    form_map = {
        DataSourceType.API: APIDataSourceForm,
        DataSourceType.LINK: LinkDataSourceForm,
        DataSourceType.DATABASE: DatabaseDataSourceForm,
    }
    
    FormClass = form_map.get(ds.source_type, APIDataSourceForm)
    form = FormClass(obj=ds)
    
    if form.validate_on_submit():
        try:
            # Update common fields
            ds.name = form.name.data
            ds.reference = form.reference.data
            ds.description = form.description.data
            ds.auto_refresh = form.auto_refresh.data
            ds.refresh_frequency = form.refresh_frequency.data
            ds.cache_enabled = form.cache_enabled.data
            ds.cache_ttl = form.cache_ttl.data
            ds.validation_enabled = form.validation_enabled.data
            ds.alert_on_failure = form.alert_on_failure.data
            ds.alert_threshold = form.alert_threshold.data
            ds.is_active = form.is_active.data
            
            # Update type-specific fields
            if ds.source_type == DataSourceType.API:
                ds.api_endpoint = form.api_endpoint.data
                ds.api_method = form.api_method.data
                ds.api_timeout = form.api_timeout.data
                ds.data_path = form.data_path.data
                
                if form.api_params.data:
                    ds.api_params = json.loads(form.api_params.data)
                if form.api_headers.data:
                    ds.api_headers = json.loads(form.api_headers.data)
                
                # Update credentials if provided
                if form.auth_token.data:
                    ds.auth_token = form.auth_token.data
                if form.auth_username.data and form.auth_password.data:
                    ds.auth_username = form.auth_username.data
                    ds.auth_password = form.auth_password.data
            
            db.session.commit()
            flash(f'Data source "{ds.name}" updated successfully!', 'success')
            return redirect(url_for('data_sources.view', id=ds.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error updating data source: {str(e)}')
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('data_sources/edit_form.html', form=form, data_source=ds)


@data_sources_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@permission_required('delete_data_source')
def delete(id):
    """Soft delete data source"""
    ds = DataSource.query.get_or_404(id)
    
    if ds.organization_id != current_user.organization_id:
        abort(403)
    
    widget_count = ds.widgets.filter_by(is_active=True).count()
    if widget_count > 0:
        flash(f'Cannot delete. {widget_count} active widgets are using it.', 'danger')
        return redirect(url_for('data_sources.view', id=id))
    
    try:
        from datetime import datetime
        ds.deleted_at = datetime.utcnow()
        ds.is_active = False
        db.session.commit()
        
        flash(f'Data source "{ds.name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('data_sources.index'))


@data_sources_bp.route('/<int:id>/test', methods=['POST'])
@login_required
@permission_required('test_data_source')
def test_connection(id):
    """Test data source connection"""
    ds = DataSource.query.get_or_404(id)
    
    if ds.organization_id != current_user.organization_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        result = DataFetcher.test_connection(ds)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@data_sources_bp.route('/<int:id>/refresh', methods=['POST'])
@login_required
@permission_required('refresh_data_source')
def refresh(id):
    """Manually refresh data source (background job)"""
    ds = DataSource.query.get_or_404(id)
    
    if ds.organization_id != current_user.organization_id:
        abort(403)
    
    if ds.refresh_in_progress:
        flash('Refresh already in progress', 'info')
        return redirect(url_for('data_sources.view', id=id))
    
    try:
        # Mark as in progress
        ds.refresh_in_progress = True
        db.session.commit()
        
        # Queue background task
        task = refresh_data_source_task.delay(ds.id, force_refresh=True)
        ds.celery_task_id = task.id
        db.session.commit()
        
        flash('Data refresh started in background. This may take a moment.', 'info')
    except Exception as e:
        ds.refresh_in_progress = False
        db.session.commit()
        flash(f'Error starting refresh: {str(e)}', 'danger')
    
    return redirect(url_for('data_sources.view', id=id))


@data_sources_bp.route('/<int:id>/schema')
@login_required
@permission_required('view_data_sources')
def view_schema(id):
    """View data source schema"""
    ds = DataSource.query.get_or_404(id)
    
    if ds.organization_id != current_user.organization_id:
        abort(403)
    
    return render_template('data_sources/schema.html', data_source=ds)


@data_sources_bp.route('/<int:id>/infer-schema', methods=['POST'])
@login_required
@permission_required('edit_data_source')
def infer_schema(id):
    """Manually trigger schema inference"""
    ds = DataSource.query.get_or_404(id)
    
    if ds.organization_id != current_user.organization_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        result = DataFetcher.fetch_data(ds, force_refresh=True)
        
        if result['success'] and result['data']:
            ds.infer_schema(result['data'])
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Schema inferred successfully',
                'column_count': ds.column_count
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Unable to fetch data for schema inference'
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@data_sources_bp.route('/<int:id>/health')
@login_required
def health_status(id):
    """Get real-time health status"""
    ds = DataSource.query.get_or_404(id)
    
    if ds.organization_id != current_user.organization_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    return jsonify({
        'health_status': ds.health_status,
        'uptime_percentage': ds.uptime_percentage,
        'success_rate': ds.success_rate,
        'avg_response_time': ds.avg_response_time,
        'consecutive_failures': ds.consecutive_failures,
        'last_refresh': ds.last_refresh.isoformat() if ds.last_refresh else None,
        'refresh_in_progress': ds.refresh_in_progress,
        'is_healthy': ds.is_healthy
    })


@data_sources_bp.route('/<int:id>/preview')
@login_required
@permission_required('view_data_sources')
def preview_data(id):
    """Preview data with schema"""
    ds = DataSource.query.get_or_404(id)
    
    if ds.organization_id != current_user.organization_id:
        abort(403)
    
    try:
        result = DataFetcher.fetch_data(ds)
        
        if result['success']:
            data = result['data']
            
            if isinstance(data, list) and len(data) > 100:
                data = data[:100]
                preview_limited = True
            else:
                preview_limited = False
            
            return render_template(
                'data_sources/preview.html',
                data_source=ds,
                data=data,
                from_cache=result.get('from_cache', False),
                preview_limited=preview_limited
            )
        else:
            flash(f'Error fetching data: {result.get("error")}', 'danger')
            return redirect(url_for('data_sources.view', id=id))
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('data_sources.view', id=id))


@data_sources_bp.route('/api/list')
@login_required
def api_list():
    """API endpoint for data sources list"""
    sources = DataSource.query.filter_by(
        organization_id=current_user.organization_id,
        is_active=True,
        deleted_at=None
    ).all()
    
    return jsonify({
        'success': True,
        'data_sources': [ds.to_dict() for ds in sources],
        'count': len(sources)
    })