"""
Organization Model
Represents transport agencies (KPA, KRC, KAA, etc.)
"""

from datetime import datetime
from sqlalchemy import event
from . import db


class Organization(db.Model):
    """
    Organization model representing transport agencies
    Supports multi-tenancy with data isolation
    """
    __tablename__ = 'organizations'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic Information
    name = db.Column(db.String(200), unique=True, nullable=False, index=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)  # KPA, KRC, etc.
    org_type = db.Column(db.String(100), nullable=False)
    
    # Details
    description = db.Column(db.Text)
    mission = db.Column(db.Text)
    vision = db.Column(db.Text)
    
    # Contact Information
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    website = db.Column(db.String(200))
    
    # Address
    address_line1 = db.Column(db.String(200))
    address_line2 = db.Column(db.String(200))
    city = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(100), default='Kenya')
    
    # Branding
    logo_url = db.Column(db.String(500))
    primary_color = db.Column(db.String(7), default='#1a237e')  # Hex color
    secondary_color = db.Column(db.String(7), default='#0d47a1')
    
    # Settings
    timezone = db.Column(db.String(50), default='Africa/Nairobi')
    locale = db.Column(db.String(10), default='en_KE')
    currency = db.Column(db.String(3), default='KES')
    
    # Features & Permissions
    features_enabled = db.Column(db.JSON, default=dict)  # Feature flags
    max_users = db.Column(db.Integer, default=50)
    max_dashboards = db.Column(db.Integer, default=20)
    max_data_sources = db.Column(db.Integer, default=100)
    
    # Status & Metadata
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_verified = db.Column(db.Boolean, default=False)
    subscription_tier = db.Column(db.String(20), default='standard')  # free, standard, premium, enterprise
    subscription_expires = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='organization', lazy='dynamic', cascade='all, delete-orphan')
    data_sources = db.relationship('DataSource', backref='organization', lazy='dynamic', cascade='all, delete-orphan')
    dashboards = db.relationship('Dashboard', backref='organization', lazy='dynamic', cascade='all, delete-orphan')
    api_keys = db.relationship('APIKey', backref='organization', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='organization', lazy='dynamic')
    
    def __repr__(self):
        return f'<Organization {self.code}: {self.name}>'
    
    @property
    def user_count(self):
        """Get total number of users"""
        return self.users.filter_by(is_active=True).count()
    
    @property
    def dashboard_count(self):
        """Get total number of dashboards"""
        return self.dashboards.filter_by(is_active=True).count()
    
    @property
    def data_source_count(self):
        """Get total number of data sources"""
        return self.data_sources.filter_by(is_active=True).count()
    
    @property
    def is_subscription_valid(self):
        """Check if subscription is still valid"""
        if not self.subscription_expires:
            return True
        return datetime.utcnow() < self.subscription_expires
    
    def can_add_user(self):
        """Check if organization can add more users"""
        return self.user_count < self.max_users
    
    def can_add_dashboard(self):
        """Check if organization can add more dashboards"""
        return self.dashboard_count < self.max_dashboards
    
    def can_add_data_source(self):
        """Check if organization can add more data sources"""
        return self.data_source_count < self.max_data_sources
    
    def has_feature(self, feature_name):
        """Check if organization has access to a feature"""
        if not self.features_enabled:
            return False
        return self.features_enabled.get(feature_name, False)
    
    def enable_feature(self, feature_name):
        """Enable a feature for the organization"""
        if not self.features_enabled:
            self.features_enabled = {}
        self.features_enabled[feature_name] = True
        db.session.commit()
    
    def disable_feature(self, feature_name):
        """Disable a feature for the organization"""
        if not self.features_enabled:
            return
        self.features_enabled[feature_name] = False
        db.session.commit()
    
    def to_dict(self, include_relationships=False):
        """Convert organization to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'org_type': self.org_type,
            'description': self.description,
            'email': self.email,
            'phone': self.phone,
            'website': self.website,
            'logo_url': self.logo_url,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'is_active': self.is_active,
            'subscription_tier': self.subscription_tier,
            'user_count': self.user_count,
            'dashboard_count': self.dashboard_count,
            'data_source_count': self.data_source_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_relationships:
            data['users'] = [user.to_dict() for user in self.users.filter_by(is_active=True).all()]
            data['dashboards'] = [dashboard.to_dict() for dashboard in self.dashboards.filter_by(is_active=True).all()]
        
        return data


# Event listeners
@event.listens_for(Organization, 'after_insert')
def create_default_dashboard(mapper, connection, target):
    """Create default dashboard for new organization"""
    # This will be handled in the service layer
    pass


@event.listens_for(Organization, 'before_update')
def update_timestamp(mapper, connection, target):
    """Update timestamp on modification"""
    target.updated_at = datetime.utcnow()