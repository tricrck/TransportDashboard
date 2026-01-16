"""
User Model
Handles user authentication, 2FA, and profile management
"""

from datetime import datetime, timedelta
from flask_login import UserMixin
from flask_bcrypt import generate_password_hash, check_password_hash
import pyotp
import secrets
from sqlalchemy import event
from models.support import Notification
from . import db


class User(UserMixin, db.Model):
    """
    User model with comprehensive authentication and profile features
    Supports 2FA, password policies, and activity tracking
    """
    __tablename__ = 'users'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Authentication
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    avatar_url = db.Column(db.String(500))
    
    # Job Information
    job_title = db.Column(db.String(100))
    department = db.Column(db.String(100))
    employee_id = db.Column(db.String(50))
    
    # Two-Factor Authentication
    two_fa_enabled = db.Column(db.Boolean, default=False)
    two_fa_secret = db.Column(db.String(32))
    backup_codes = db.Column(db.JSON)  # Encrypted backup codes
    
    # Password Management
    password_changed_at = db.Column(db.DateTime)
    password_reset_token = db.Column(db.String(100))
    password_reset_expires = db.Column(db.DateTime)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    
    # Session Management
    session_token = db.Column(db.String(100))
    last_login = db.Column(db.DateTime)
    last_activity = db.Column(db.DateTime)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    
    # Preferences
    language = db.Column(db.String(10), default='en')
    timezone = db.Column(db.String(50), default='Africa/Nairobi')
    theme = db.Column(db.String(20), default='light')  # light, dark, auto
    email_notifications = db.Column(db.Boolean, default=True)
    sms_notifications = db.Column(db.Boolean, default=False)
    
    # Status & Metadata
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_superuser = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100))
    verification_sent_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)  # Soft delete
    
    # Foreign Keys
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    role = db.relationship('Role', backref='users', foreign_keys=[role_id])
    created_by = db.relationship('User', remote_side=[id], foreign_keys=[created_by_id])
    data_sources_created = db.relationship('DataSource', backref='creator', foreign_keys='DataSource.created_by_id')
    widgets_created = db.relationship('Widget', backref='creator', foreign_keys='Widget.created_by_id')
    dashboards_created = db.relationship('Dashboard', backref='creator', foreign_keys='Dashboard.created_by_id')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    # Password Management
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password).decode('utf-8')
        self.password_changed_at = datetime.utcnow()
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def check_password(self, password):
        """Verify password"""
        if self.is_locked():
            return False
        
        is_valid = check_password_hash(self.password_hash, password)
        
        if not is_valid:
            self.failed_login_attempts += 1
            if self.failed_login_attempts >= 5:
                self.locked_until = datetime.utcnow() + timedelta(minutes=30)
            db.session.commit()
        else:
            self.failed_login_attempts = 0
            self.locked_until = None
        
        return is_valid
    
    def is_locked(self):
        """Check if account is locked"""
        if not self.locked_until:
            return False
        if datetime.utcnow() > self.locked_until:
            self.locked_until = None
            self.failed_login_attempts = 0
            db.session.commit()
            return False
        return True
    
    def generate_password_reset_token(self):
        """Generate password reset token"""
        self.password_reset_token = secrets.token_urlsafe(32)
        self.password_reset_expires = datetime.utcnow() + timedelta(hours=24)
        db.session.commit()
        return self.password_reset_token
    
    def verify_password_reset_token(self, token):
        """Verify password reset token"""
        if not self.password_reset_token or not self.password_reset_expires:
            return False
        if token != self.password_reset_token:
            return False
        if datetime.utcnow() > self.password_reset_expires:
            return False
        return True
    
    # Two-Factor Authentication
    def generate_2fa_secret(self):
        """Generate new 2FA secret"""
        self.two_fa_secret = pyotp.random_base32()
        db.session.commit()
        return self.two_fa_secret
    
    def get_2fa_uri(self):
        """Get 2FA provisioning URI for QR code"""
        if not self.two_fa_secret:
            self.generate_2fa_secret()
        
        totp = pyotp.TOTP(self.two_fa_secret)
        return totp.provisioning_uri(
            name=self.email,
            issuer_name='Kenya Transport Analytics'
        )
    
    def verify_2fa_token(self, token):
        """Verify 2FA token"""
        if not self.two_fa_secret:
            return False
        
        totp = pyotp.TOTP(self.two_fa_secret)
        return totp.verify(token, valid_window=1)
    
    def enable_2fa(self, token):
        """Enable 2FA after verifying setup token"""
        if self.verify_2fa_token(token):
            self.two_fa_enabled = True
            self.generate_backup_codes()
            db.session.commit()
            return True
        return False
    
    def disable_2fa(self):
        """Disable 2FA"""
        self.two_fa_enabled = False
        self.backup_codes = None
        db.session.commit()
    
    def generate_backup_codes(self, count=10):
        """Generate backup codes for 2FA"""
        codes = [secrets.token_hex(4).upper() for _ in range(count)]
        # In production, these should be hashed
        self.backup_codes = codes
        db.session.commit()
        return codes
    
    def verify_backup_code(self, code):
        """Verify and consume a backup code"""
        if not self.backup_codes or code.upper() not in self.backup_codes:
            return False
        
        self.backup_codes.remove(code.upper())
        db.session.commit()
        return True
    
    # Permissions
    def has_permission(self, permission_code):
        """Check if user has specific permission"""
        if self.is_superuser:
            return True
        
        if not self.role:
            return False
        
        return any(p.code == permission_code for p in self.role.permissions)
    
    def has_any_permission(self, permission_codes):
        """Check if user has any of the specified permissions"""
        if self.is_superuser:
            return True
        
        return any(self.has_permission(code) for code in permission_codes)
    
    def has_all_permissions(self, permission_codes):
        """Check if user has all specified permissions"""
        if self.is_superuser:
            return True
        
        return all(self.has_permission(code) for code in permission_codes)
    
    # Session Management
    def generate_session_token(self):
        """Generate new session token"""
        self.session_token = secrets.token_urlsafe(32)
        db.session.commit()
        return self.session_token
    
    def update_last_activity(self, ip_address=None, user_agent=None):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
        if ip_address:
            self.ip_address = ip_address
        if user_agent:
            self.user_agent = user_agent
        db.session.commit()
    
    def record_login(self, ip_address=None, user_agent=None):
        """Record successful login"""
        self.last_login = datetime.utcnow()
        self.failed_login_attempts = 0
        self.locked_until = None
        if ip_address:
            self.ip_address = ip_address
        if user_agent:
            self.user_agent = user_agent
        db.session.commit()
    
    # Properties
    @property
    def full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return self.email.split('@')[0]
    
    @property
    def initials(self):
        """Get user's initials"""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.first_name:
            return self.first_name[0].upper()
        return self.email[0].upper()
    
    @property
    def is_password_expired(self):
        """Check if password needs to be changed (90 days)"""
        if not self.password_changed_at:
            return False
        expiry_date = self.password_changed_at + timedelta(days=90)
        return datetime.utcnow() > expiry_date
    
    @property
    def days_since_last_login(self):
        """Get days since last login"""
        if not self.last_login:
            return None
        delta = datetime.utcnow() - self.last_login
        return delta.days
    
    @property
    def unread_notifications_count(self):
        """Return count of unread notifications"""
        return self.notifications.filter_by(is_read=False).count()
    
    @property
    def notifications_count(self):
        return self.notifications.count()

    @property
    def recent_notifications(self):
        return (
            self.notifications
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )

    # Serialization
    def to_dict(self, include_sensitive=False):
        """Convert user to dictionary"""
        data = {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'initials': self.initials,
            'phone': self.phone,
            'avatar_url': self.avatar_url,
            'job_title': self.job_title,
            'department': self.department,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'two_fa_enabled': self.two_fa_enabled,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'organization': {
                'id': self.organization.id,
                'name': self.organization.name,
                'code': self.organization.code
            } if self.organization else None,
            'role': {
                'id': self.role.id,
                'name': self.role.name
            } if self.role else None
        }
        
        if include_sensitive:
            data.update({
                'email_notifications': self.email_notifications,
                'sms_notifications': self.sms_notifications,
                'language': self.language,
                'timezone': self.timezone,
                'theme': self.theme,
                'is_locked': self.is_locked(),
                'failed_login_attempts': self.failed_login_attempts
            })
        
        return data


# Event listeners
@event.listens_for(User, 'before_insert')
def set_defaults(mapper, connection, target):
    """Set default values on user creation"""
    if not target.password_changed_at:
        target.password_changed_at = datetime.utcnow()


@event.listens_for(User, 'before_update')
def update_timestamp(mapper, connection, target):
    """Update timestamp on modification"""
    target.updated_at = datetime.utcnow()