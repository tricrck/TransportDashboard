"""
Supporting Models: Audit Logs, Notifications, API Keys, Data Refresh Logs
"""

from datetime import datetime, timedelta
import enum
import secrets
from sqlalchemy import event
from . import db


# ============================================================================
# AUDIT LOG MODEL
# ============================================================================

class AuditAction(enum.Enum):
    """Audit log action types"""
    # Authentication
    LOGIN = 'login'
    LOGOUT = 'logout'
    LOGIN_FAILED = 'login_failed'
    PASSWORD_CHANGE = 'password_change'
    PASSWORD_RESET = 'password_reset'
    TWO_FA_ENABLED = '2fa_enabled'
    TWO_FA_DISABLED = '2fa_disabled'
    
    # CRUD Operations
    CREATE = 'create'
    READ = 'read'
    UPDATE = 'update'
    DELETE = 'delete'
    
    # Permissions
    PERMISSION_GRANTED = 'permission_granted'
    PERMISSION_REVOKED = 'permission_revoked'
    
    # Data Operations
    DATA_EXPORT = 'data_export'
    DATA_IMPORT = 'data_import'
    
    # System
    SETTINGS_CHANGE = 'settings_change'
    API_ACCESS = 'api_access'


class AuditLog(db.Model):
    """
    Audit log for tracking all system activities
    Comprehensive logging for security and compliance
    """
    __tablename__ = 'audit_logs'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Action Details
    action = db.Column(db.Enum(AuditAction), nullable=False, index=True)
    resource_type = db.Column(db.String(50), index=True)  # user, dashboard, widget, etc.
    resource_id = db.Column(db.Integer)
    description = db.Column(db.Text)
    
    # Before/After State
    old_values = db.Column(db.JSON)
    new_values = db.Column(db.JSON)
    
    # Request Information
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    request_method = db.Column(db.String(10))
    request_path = db.Column(db.String(500))
    request_params = db.Column(db.JSON)
    
    # Result
    status = db.Column(db.String(20))  # success, failure, error
    error_message = db.Column(db.Text)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), index=True)
    
    def __repr__(self):
        return f'<AuditLog {self.action.value}: {self.resource_type}#{self.resource_id}>'
    
    @classmethod
    def log(cls, action, user=None, organization=None, resource_type=None, 
            resource_id=None, description=None, old_values=None, new_values=None,
            ip_address=None, user_agent=None, status='success', error_message=None):
        """Create audit log entry"""
        log = cls(
            action=action,
            user_id=user.id if user else None,
            organization_id=organization.id if organization else (user.organization_id if user else None),
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message
        )
        db.session.add(log)
        db.session.commit()
        return log
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'action': self.action.value if self.action else None,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'description': self.description,
            'status': self.status,
            'user': {
                'id': self.user.id,
                'email': self.user.email,
                'full_name': self.user.full_name
            } if self.user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================================================
# NOTIFICATION MODEL
# ============================================================================

class NotificationType(enum.Enum):
    """Notification types"""
    INFO = 'info'
    SUCCESS = 'success'
    WARNING = 'warning'
    ERROR = 'error'
    SYSTEM = 'system'


class Notification(db.Model):
    """
    User notifications
    In-app notification system
    """
    __tablename__ = 'notifications'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Content
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.Enum(NotificationType), default=NotificationType.INFO)
    
    # Action
    action_url = db.Column(db.String(500))
    action_label = db.Column(db.String(50))
    
    # Status
    is_read = db.Column(db.Boolean, default=False, index=True)
    read_at = db.Column(db.DateTime)
    
    # Priority
    priority = db.Column(db.Integer, default=0)  # Higher = more important
    
    # Expiry
    expires_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    def __repr__(self):
        return f'<Notification {self.title}>'
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = datetime.utcnow()
        db.session.commit()
    
    @property
    def is_expired(self):
        """Check if notification has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @classmethod
    def create(cls, user, title, message, notification_type=NotificationType.INFO,
               action_url=None, action_label=None, priority=0, expires_in_days=30):
        """Create notification"""
        notification = cls(
            user_id=user.id,
            title=title,
            message=message,
            notification_type=notification_type,
            action_url=action_url,
            action_label=action_label,
            priority=priority,
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days)
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'notification_type': self.notification_type.value if self.notification_type else None,
            'action_url': self.action_url,
            'action_label': self.action_label,
            'is_read': self.is_read,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None
        }


# ============================================================================
# API KEY MODEL
# ============================================================================

class APIKey(db.Model):
    """
    API keys for programmatic access
    Secure API authentication tokens
    """
    __tablename__ = 'api_keys'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Key Details
    name = db.Column(db.String(200), nullable=False)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    prefix = db.Column(db.String(10))  # First 8 chars for identification
    description = db.Column(db.Text)
    
    # Permissions
    scopes = db.Column(db.JSON)  # Array of allowed operations
    allowed_ips = db.Column(db.JSON)  # Whitelist of IP addresses
    rate_limit = db.Column(db.Integer, default=1000)  # Requests per hour
    
    # Usage
    last_used = db.Column(db.DateTime)
    usage_count = db.Column(db.Integer, default=0)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)
    expires_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Foreign Keys
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    def __repr__(self):
        return f'<APIKey {self.prefix}...>'
    
    @classmethod
    def generate(cls, name, organization, created_by, scopes=None, 
                 expires_in_days=365, description=None):
        """Generate new API key"""
        key = secrets.token_urlsafe(48)
        prefix = key[:8]
        
        api_key = cls(
            name=name,
            key=key,
            prefix=prefix,
            description=description,
            scopes=scopes or [],
            organization_id=organization.id,
            created_by_id=created_by.id,
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days)
        )
        db.session.add(api_key)
        db.session.commit()
        return api_key, key  # Return key only once
    
    def record_usage(self, ip_address=None):
        """Record API key usage"""
        self.last_used = datetime.utcnow()
        self.usage_count += 1
        db.session.commit()
    
    @property
    def is_expired(self):
        """Check if API key has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if API key is valid"""
        return self.is_active and not self.is_expired
    
    def has_scope(self, scope):
        """Check if API key has specific scope"""
        if not self.scopes:
            return False
        return scope in self.scopes
    
    def to_dict(self, include_key=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'prefix': self.prefix,
            'description': self.description,
            'scopes': self.scopes,
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_key:
            data['key'] = self.key
        
        return data


# ============================================================================
# DATA REFRESH LOG MODEL
# ============================================================================

class DataRefreshLog(db.Model):
    """
    Log of data source refresh operations
    Tracks refresh history and performance
    """
    __tablename__ = 'data_refresh_logs'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Refresh Details
    status = db.Column(db.String(20), nullable=False, index=True)  # success, error, timeout
    records_fetched = db.Column(db.Integer)
    records_processed = db.Column(db.Integer)
    
    # Performance
    duration_ms = db.Column(db.Integer)  # Milliseconds
    data_size_bytes = db.Column(db.Integer)
    
    # Error Details
    error_message = db.Column(db.Text)
    error_trace = db.Column(db.Text)
    
    # Metadata
    triggered_by = db.Column(db.String(50))  # manual, scheduled, api
    
    # Timestamp
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = db.Column(db.DateTime)
    
    # Foreign Keys
    data_source_id = db.Column(db.Integer, db.ForeignKey('data_sources.id'), nullable=False, index=True)
    triggered_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    triggered_by_user = db.relationship('User', foreign_keys=[triggered_by_user_id])
    
    def __repr__(self):
        return f'<DataRefreshLog DS:{self.data_source_id} {self.status}>'
    
    @classmethod
    def start_refresh(cls, data_source, triggered_by='scheduled', user=None):
        """Create log entry for starting refresh"""
        log = cls(
            data_source_id=data_source.id,
            status='running',
            triggered_by=triggered_by,
            triggered_by_user_id=user.id if user else None
        )
        db.session.add(log)
        db.session.commit()
        return log
    
    def complete_success(self, records_fetched, records_processed, data_size_bytes):
        """Mark refresh as successful"""
        self.status = 'success'
        self.records_fetched = records_fetched
        self.records_processed = records_processed
        self.data_size_bytes = data_size_bytes
        self.completed_at = datetime.utcnow()
        
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)
        
        db.session.commit()
    
    def complete_error(self, error_message, error_trace=None):
        """Mark refresh as failed"""
        self.status = 'error'
        self.error_message = error_message
        self.error_trace = error_trace
        self.completed_at = datetime.utcnow()
        
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)
        
        db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'status': self.status,
            'records_fetched': self.records_fetched,
            'records_processed': self.records_processed,
            'duration_ms': self.duration_ms,
            'data_size_bytes': self.data_size_bytes,
            'triggered_by': self.triggered_by,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'data_source': {
                'id': self.data_source.id,
                'name': self.data_source.name
            } if self.data_source else None
        }


# ============================================================================
# EVENT LISTENERS
# ============================================================================

@event.listens_for(Notification, 'after_insert')
def send_notification_email(mapper, connection, target):
    """Send email notification if user has enabled email notifications"""
    # This will be implemented in the service layer
    pass