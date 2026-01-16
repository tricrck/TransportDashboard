"""
Kenya Transport Sector - Unified Analytics Platform
Enterprise-grade Flask application with comprehensive security and analytics

Built by: Nerdware Technologies
Architecture: God-Level Production-Ready System
"""

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# ============================================================================
# APPLICATION FACTORY
# ============================================================================

def create_app(config_name='default'):
    """
    Application factory pattern for creating Flask app instances
    
    Args:
        config_name: Configuration environment (development, production, testing)
    
    Returns:
        Configured Flask application instance
    """
    # Initialize Flask app
    app = Flask(__name__)
    
    # Load configuration
    from config import config
    app.config.from_object(config[config_name])
    
    # Jinja filters
    from services.jinja_filters import format_number, timeago
    app.jinja_env.filters['format_number'] = format_number
    app.jinja_env.filters['timeago'] = timeago

    # Initialize extensions
    initialize_extensions(app)
    
    # Setup logging
    setup_logging(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register context processors
    register_context_processors(app)
    
    # Register CLI commands
    register_cli_commands(app)
    
    # Log startup
    app.logger.info('='*80)
    app.logger.info('Kenya Transport Analytics Platform - Starting')
    app.logger.info(f'Environment: {config_name}')
    app.logger.info(f'Debug Mode: {app.debug}')
    app.logger.info(f'Database: {app.config.get("SQLALCHEMY_DATABASE_URI", "Not configured")}')
    app.logger.info('='*80)
    
    return app


# ============================================================================
# EXTENSION INITIALIZATION
# ============================================================================

def initialize_extensions(app):
    """Initialize Flask extensions"""
    from models import db
    from flask_login import LoginManager
    from flask_bcrypt import Bcrypt
    from services.cache_service import CacheService
    
    
    # Database
    db.init_app(app)
    
    # Migrations
    migrate = Migrate(app, db)

    
    # Login Manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'
    
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # Bcrypt
    bcrypt = Bcrypt(app)

    cache_service_instance = CacheService()
    cache_service_instance.init_app(app)
    app.cache = cache_service_instance
    
    # CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config.get('CORS_ORIGINS', '*'),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Store extensions on app for easy access
    app.db = db
    app.login_manager = login_manager
    app.bcrypt = bcrypt
    
    app.logger.info('Extensions initialized successfully')


# ============================================================================
# BLUEPRINT REGISTRATION
# ============================================================================

def register_blueprints(app):
    """Register all application blueprints"""
    from blueprints import (
        auth_bp, main_bp, admin_bp, data_sources_bp,
        widgets_bp, dashboards_bp, api_bp, profile_bp
    )
    
    # Register blueprints with their URL prefixes
    blueprints = [
        (auth_bp, '/auth'),
        (main_bp, '/'),
        (admin_bp, '/admin'),
        (data_sources_bp, '/data-sources'),
        (widgets_bp, '/widgets'),
        (dashboards_bp, '/dashboards'),
        (api_bp, '/api'),
        (profile_bp, '/profile')
    ]
    
    for blueprint, url_prefix in blueprints:
        app.register_blueprint(blueprint, url_prefix=url_prefix)
        app.logger.info(f'Registered blueprint: {blueprint.name} at {url_prefix}')


# ============================================================================
# ERROR HANDLERS
# ============================================================================

def register_error_handlers(app):
    """Register error handlers for common HTTP errors"""
    from flask import render_template, jsonify, request
    
    @app.errorhandler(403)
    def forbidden(error):
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Forbidden',
                'message': 'You do not have permission to access this resource'
            }), 403
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Not Found',
                'message': 'The requested resource was not found'
            }), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        from models import db
        db.session.rollback()
        
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            }), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Too Many Requests',
                'message': 'Rate limit exceeded. Please try again later.'
            }), 429
        return render_template('errors/429.html'), 429
    
    app.logger.info('Error handlers registered')


# ============================================================================
# CONTEXT PROCESSORS
# ============================================================================

def register_context_processors(app):
    """Register context processors for templates"""
    from flask_login import current_user
    from models import Notification
    
    @app.context_processor
    def inject_globals():
        """Inject global variables into all templates"""
        unread_notifications = 0
        if current_user.is_authenticated:
            unread_notifications = Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).count()
        
        return {
            'app_name': 'Kenya Transport Analytics',
            'app_version': '1.0.0',
            'current_year': datetime.utcnow().year,
            'unread_notifications': unread_notifications,
            'debug_mode': app.debug
        }
    
    app.logger.info('Context processors registered')


# ============================================================================
# CLI COMMANDS
# ============================================================================

def register_cli_commands(app):
    """Register custom CLI commands"""
    import click
    from models import db

    @app.cli.command("fix-db")
    def fix_database():
        """Fix database schema issues"""
        print("Checking database schema...")
        
        # Check permissions table
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        
        if 'permissions' not in inspector.get_table_names():
            print("Permissions table doesn't exist. Creating all tables...")
            db.create_all()
            print("✓ Tables created")
        else:
            columns = {col['name'] for col in inspector.get_columns('permissions')}
            print(f"Current permissions columns: {columns}")
            
            # Check for missing columns
            missing = {'module', 'is_system', 'is_active', 'display_order', 'created_at', 'updated_at'} - columns
            
            if missing:
                print(f"Missing columns: {missing}")
                print("Dropping and recreating permissions table...")
                
                # Backup data if needed
                try:
                    # Read existing permissions
                    result = db.session.execute(text("SELECT * FROM permissions"))
                    existing_data = result.fetchall()
                    print(f"Found {len(existing_data)} existing permissions")
                except:
                    existing_data = []
                
                # Drop and recreate
                db.session.execute(text("DROP TABLE IF EXISTS permissions"))
                db.session.commit()
                
                # Recreate table
                from models.permission import Permission
                db.create_all()
                
                print("✓ Permissions table recreated with correct schema")
                
                # Note: You'll need to re-run flask init-db to populate default permissions
            else:
                print("✓ Permissions table schema is correct")
        
        print("Database fix completed!")

    # In app.py, modify the reset_db command:
    @app.cli.command("reset-db")
    def reset_db():
        """Drop and recreate all tables"""
        from sqlalchemy import text, inspect
        
        print("Dropping all tables with CASCADE...")
        
        try:
            # Get all table names
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            # Disable foreign key checks (PostgreSQL specific)
            db.session.execute(text('SET session_replication_role = replica;'))
            
            # Drop all tables
            for table in tables:
                print(f"Dropping table: {table}")
                db.session.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE;'))
            
            db.session.commit()
            
            # Re-enable foreign key checks
            db.session.execute(text('SET session_replication_role = DEFAULT;'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
            # Fallback to SQLAlchemy's drop_all with cascade
            with db.engine.connect() as conn:
                trans = conn.begin()
                try:
                    conn.execute(text('DROP SCHEMA public CASCADE;'))
                    conn.execute(text('CREATE SCHEMA public;'))
                    trans.commit()
                except:
                    trans.rollback()
                    raise
        
        print("Creating all tables...")
        db.create_all()
        print("✓ Database reset complete")
    
    @app.cli.command('init-db')
    def init_db():
        """Initialize the database with tables and default data"""
        click.echo('Creating database tables...')
        db.create_all()
        click.echo('✓ Database tables created')
        
        click.echo('Creating default permissions...')
        from models.permission import create_default_permissions
        create_default_permissions()
        click.echo('✓ Default permissions created')
        
        click.echo('Creating default roles...')
        from models.permission import create_default_roles
        create_default_roles()
        click.echo('✓ Default roles created')
        
        click.echo('Creating system organization...')
        from models import Organization
        system_org = Organization.query.filter_by(code='SYSTEM').first()
        if not system_org:
            system_org = Organization(
                name='System',
                code='SYSTEM',
                org_type='System',
                description='System organization',
                is_active=True
            )
            db.session.add(system_org)
            db.session.commit()
            click.echo('✓ System organization created')
        else:
            click.echo('✓ System organization already exists')
        
        click.echo('Creating admin user...')
        from models import User, Role
        admin_user = User.query.filter_by(email='admin@transport.go.ke').first()
        if not admin_user:
            admin_role = Role.query.filter_by(code='super_admin').first()
            admin_user = User(
                email='admin@transport.go.ke',
                first_name='System',
                last_name='Administrator',
                organization_id=system_org.id,
                role_id=admin_role.id,
                is_active=True,
                is_superuser=True
            )
            admin_user.set_password('ChangeMe123!')
            db.session.add(admin_user)
            db.session.commit()
            
            click.echo('')
            click.echo('='*60)
            click.echo('DEFAULT ADMIN CREATED')
            click.echo('Email: admin@transport.go.ke')
            click.echo('Password: ChangeMe123!')
            click.echo('⚠️  PLEASE CHANGE THIS PASSWORD IMMEDIATELY!')
            click.echo('='*60)
            click.echo('')
        else:
            click.echo('✓ Admin user already exists')
        
        click.echo('\n✅ Database initialization complete!')
    
    @app.cli.command('create-org')
    @click.argument('name')
    @click.argument('code')
    @click.option('--type', default='Transport Authority', help='Organization type')
    def create_org(name, code, type):
        """Create a new organization"""
        from models import Organization
        
        org = Organization.query.filter_by(code=code.upper()).first()
        if org:
            click.echo(f'❌ Organization with code {code} already exists')
            return
        
        org = Organization(
            name=name,
            code=code.upper(),
            org_type=type,
            is_active=True
        )
        db.session.add(org)
        db.session.commit()
        
        click.echo(f'✅ Organization "{name}" ({code}) created successfully!')
    
    @app.cli.command('create-user')
    @click.argument('email')
    @click.argument('password')
    @click.option('--first-name', prompt='First name')
    @click.option('--last-name', prompt='Last name')
    @click.option('--org-code', prompt='Organization code')
    @click.option('--role-code', default='analyst', help='Role code')
    def create_user(email, password, first_name, last_name, org_code, role_code):
        """Create a new user"""
        from models import User, Organization, Role
        
        user = User.query.filter_by(email=email.lower()).first()
        if user:
            click.echo(f'❌ User with email {email} already exists')
            return
        
        org = Organization.query.filter_by(code=org_code.upper()).first()
        if not org:
            click.echo(f'❌ Organization with code {org_code} not found')
            return
        
        role = Role.query.filter_by(code=role_code).first()
        if not role:
            click.echo(f'❌ Role with code {role_code} not found')
            return
        
        user = User(
            email=email.lower(),
            first_name=first_name,
            last_name=last_name,
            organization_id=org.id,
            role_id=role.id,
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        click.echo(f'✅ User "{email}" created successfully!')
    
    @app.cli.command('reset-password')
    @click.argument('email')
    @click.argument('new_password')
    def reset_password(email, new_password):
        """Reset user password"""
        from models import User
        
        user = User.query.filter_by(email=email.lower()).first()
        if not user:
            click.echo(f'❌ User with email {email} not found')
            return
        
        user.set_password(new_password)
        db.session.commit()
        
        click.echo(f'✅ Password reset successfully for {email}')
    
    @app.cli.command('list-users')
    @click.option('--org-code', help='Filter by organization code')
    def list_users(org_code):
        """List all users"""
        from models import User, Organization
        
        query = User.query
        if org_code:
            org = Organization.query.filter_by(code=org_code.upper()).first()
            if not org:
                click.echo(f'❌ Organization with code {org_code} not found')
                return
            query = query.filter_by(organization_id=org.id)
        
        users = query.all()
        
        if not users:
            click.echo('No users found')
            return
        
        click.echo(f'\nFound {len(users)} user(s):\n')
        click.echo(f'{"ID":<5} {"Email":<30} {"Name":<30} {"Organization":<20} {"Status":<10}')
        click.echo('-' * 100)
        
        for user in users:
            status = 'Active' if user.is_active else 'Inactive'
            org_name = user.organization.code if user.organization else 'N/A'
            click.echo(f'{user.id:<5} {user.email:<30} {user.full_name:<30} {org_name:<20} {status:<10}')
    
    @app.cli.command('cleanup')
    def cleanup():
        """Clean up expired notifications and sessions"""
        from services import NotificationService
        
        click.echo('Cleaning up expired notifications...')
        count = NotificationService.cleanup_expired()
        click.echo(f'✓ Removed {count} expired notifications')
        
        click.echo('\n✅ Cleanup complete!')
    
    app.logger.info('CLI commands registered')


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

def setup_logging(app):
    """Configure application logging"""
    if not app.debug:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # File handler for general logs
        file_handler = RotatingFileHandler(
            'logs/transport_analytics.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # File handler for errors
        error_handler = RotatingFileHandler(
            'logs/errors.log',
            maxBytes=10240000,
            backupCount=10
        )
        error_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s\n'
            'Path: %(pathname)s:%(lineno)d\n'
            '%(message)s\n'
        ))
        error_handler.setLevel(logging.ERROR)
        app.logger.addHandler(error_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Logging configured')


# ============================================================================
# APPLICATION INSTANCE
# ============================================================================

# Create application instance
app = create_app(os.getenv('FLASK_ENV', 'development'))


# ============================================================================
# SHELL CONTEXT
# ============================================================================

@app.shell_context_processor
def make_shell_context():
    """
    Make models available in Flask shell
    Usage: flask shell
    """
    from models import (
        db, Organization, User, Role, Permission,
        DataSource, Widget, Dashboard, DashboardWidget,
        AuditLog, Notification, APIKey, DataRefreshLog
    )
    from services import (
        AuthService, DataFetcher, WidgetProcessor,
        NotificationService, ReportService, cache_service
    )
    
    return {
        'db': db,
        'Organization': Organization,
        'User': User,
        'Role': Role,
        'Permission': Permission,
        'DataSource': DataSource,
        'Widget': Widget,
        'Dashboard': Dashboard,
        'DashboardWidget': DashboardWidget,
        'AuditLog': AuditLog,
        'Notification': Notification,
        'APIKey': APIKey,
        'DataRefreshLog': DataRefreshLog,
        'AuthService': AuthService,
        'DataFetcher': DataFetcher,
        'WidgetProcessor': WidgetProcessor,
        'NotificationService': NotificationService,
        'ReportService': ReportService,
        'cache': cache_service
    }

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    # Development server configuration
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    app.logger.info(f'Starting development server on {host}:{port}')
    app.logger.info(f'Debug mode: {debug}')
    app.logger.info('Press CTRL+C to quit')
    
    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=debug,
        threaded=True
    )