"""
Permission and Role Models
Implements Role-Based Access Control (RBAC)
"""

from datetime import datetime
from sqlalchemy import event
from . import db


# Many-to-Many relationship table
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    db.Column('granted_at', db.DateTime, default=datetime.utcnow)
)


class Permission(db.Model):
    """
    Permission model for granular access control
    Defines specific actions users can perform
    """
    __tablename__ = 'permissions'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Identification
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    
    # Categorization
    category = db.Column(db.String(50), nullable=False, index=True)  # organization, user, data_source, widget, dashboard
    module = db.Column(db.String(50))  # Additional grouping
    
    # Metadata
    is_system = db.Column(db.Boolean, default=False)  # System permissions cannot be deleted
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    roles = db.relationship('Role', secondary=role_permissions, back_populates='permissions')
    
    def __repr__(self):
        return f'<Permission {self.code}: {self.name}>'
    
    @property
    def role_count(self):
        """Get number of roles with this permission"""
        return len(self.roles)
    
    @classmethod
    def get_by_code(cls, code):
        """Get permission by code"""
        return cls.query.filter_by(code=code, is_active=True).first()
    
    @classmethod
    def get_by_category(cls, category):
        """Get all permissions in a category"""
        return cls.query.filter_by(category=category, is_active=True).order_by(cls.display_order).all()
    
    @classmethod
    def get_system_permissions(cls):
        """Get all system permissions"""
        return cls.query.filter_by(is_system=True, is_active=True).all()
    
    def to_dict(self):
        """Convert permission to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'category': self.category,
            'module': self.module,
            'is_system': self.is_system,
            'role_count': self.role_count
        }


class Role(db.Model):
    """
    Role model for grouping permissions
    Simplifies permission assignment to users
    """
    __tablename__ = 'roles'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Identification
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    
    # Properties
    is_system_role = db.Column(db.Boolean, default=False)  # System roles cannot be deleted
    is_default = db.Column(db.Boolean, default=False)  # Assigned to new users by default
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Hierarchy (optional)
    parent_role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    level = db.Column(db.Integer, default=0)  # 0 = lowest, higher = more privileges
    
    # Display
    color = db.Column(db.String(7), default='#2196f3')  # Hex color for badges
    icon = db.Column(db.String(50))  # Font Awesome icon class
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    permissions = db.relationship('Permission', secondary=role_permissions, back_populates='roles')
    parent_role = db.relationship('Role', remote_side=[id], backref='child_roles')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    def __repr__(self):
        return f'<Role {self.code}: {self.name}>'
    
    @property
    def user_count(self):
        """Get number of users with this role"""
        from .user import User
        return User.query.filter_by(role_id=self.id, is_active=True).count()
    
    @property
    def permission_count(self):
        """Get number of permissions in this role"""
        return len(self.permissions)
    
    def has_permission(self, permission_code):
        """Check if role has specific permission"""
        return any(p.code == permission_code for p in self.permissions)
    
    def add_permission(self, permission):
        """Add permission to role"""
        if permission not in self.permissions:
            self.permissions.append(permission)
            db.session.commit()
    
    def remove_permission(self, permission):
        """Remove permission from role"""
        if permission in self.permissions:
            self.permissions.remove(permission)
            db.session.commit()
    
    def add_permissions(self, permissions):
        """Add multiple permissions to role"""
        for permission in permissions:
            if permission not in self.permissions:
                self.permissions.append(permission)
        db.session.commit()
    
    def set_permissions(self, permissions):
        """Replace all permissions with new set"""
        self.permissions = permissions
        db.session.commit()
    
    def clear_permissions(self):
        """Remove all permissions from role"""
        self.permissions = []
        db.session.commit()
    
    def inherit_from_parent(self):
        """Inherit permissions from parent role"""
        if self.parent_role:
            for permission in self.parent_role.permissions:
                if permission not in self.permissions:
                    self.permissions.append(permission)
            db.session.commit()
    
    @classmethod
    def get_default_role(cls):
        """Get the default role for new users"""
        return cls.query.filter_by(is_default=True, is_active=True).first()
    
    @classmethod
    def get_by_code(cls, code):
        """Get role by code"""
        return cls.query.filter_by(code=code, is_active=True).first()
    
    @classmethod
    def get_system_roles(cls):
        """Get all system roles"""
        return cls.query.filter_by(is_system_role=True, is_active=True).all()
    
    def to_dict(self, include_permissions=False):
        """Convert role to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'is_system_role': self.is_system_role,
            'is_default': self.is_default,
            'level': self.level,
            'color': self.color,
            'icon': self.icon,
            'user_count': self.user_count,
            'permission_count': self.permission_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_permissions:
            data['permissions'] = [p.to_dict() for p in self.permissions]
        
        if self.parent_role:
            data['parent_role'] = {
                'id': self.parent_role.id,
                'name': self.parent_role.name,
                'code': self.parent_role.code
            }
        
        return data


# Event listeners
@event.listens_for(Permission, 'before_update')
def update_permission_timestamp(mapper, connection, target):
    """Update timestamp on modification"""
    target.updated_at = datetime.utcnow()


@event.listens_for(Role, 'before_update')
def update_role_timestamp(mapper, connection, target):
    """Update timestamp on modification"""
    target.updated_at = datetime.utcnow()


@event.listens_for(Role, 'before_delete')
def prevent_system_role_deletion(mapper, connection, target):
    """Prevent deletion of system roles"""
    if target.is_system_role:
        raise ValueError(f"Cannot delete system role: {target.name}")


# Helper functions for seeding default permissions
def create_default_permissions():
    """Create default permissions for the system"""
    default_permissions = [
        # Organization Management
        ('view_organizations', 'View Organizations', 'organization', 'View organization details'),
        ('create_organization', 'Create Organization', 'organization', 'Create new organizations'),
        ('edit_organization', 'Edit Organization', 'organization', 'Edit organization details'),
        ('delete_organization', 'Delete Organization', 'organization', 'Delete organizations'),
        ('manage_organization_settings', 'Manage Organization Settings', 'organization', 'Manage organization settings'),
        
        # User Management
        ('view_users', 'View Users', 'user', 'View user list and details'),
        ('create_user', 'Create User', 'user', 'Create new users'),
        ('edit_user', 'Edit User', 'user', 'Edit user details'),
        ('delete_user', 'Delete User', 'user', 'Delete users'),
        ('manage_user_permissions', 'Manage User Permissions', 'user', 'Assign roles and permissions'),
        ('reset_user_password', 'Reset User Password', 'user', 'Reset user passwords'),
        
        # Role & Permission Management
        ('view_roles', 'View Roles', 'role', 'View role list and details'),
        ('create_role', 'Create Role', 'role', 'Create new roles'),
        ('edit_role', 'Edit Role', 'role', 'Edit role details'),
        ('delete_role', 'Delete Role', 'role', 'Delete roles'),
        ('assign_permissions', 'Assign Permissions', 'role', 'Assign permissions to roles'),
        
        # Data Source Management
        ('view_data_sources', 'View Data Sources', 'data_source', 'View data source list'),
        ('create_data_source', 'Create Data Source', 'data_source', 'Create new data sources'),
        ('edit_data_source', 'Edit Data Source', 'data_source', 'Edit data source configuration'),
        ('delete_data_source', 'Delete Data Source', 'data_source', 'Delete data sources'),
        ('test_data_source', 'Test Data Source', 'data_source', 'Test data source connections'),
        ('refresh_data_source', 'Refresh Data Source', 'data_source', 'Manually refresh data sources'),
        
        # Widget Management
        ('view_widgets', 'View Widgets', 'widget', 'View widget list'),
        ('create_widget', 'Create Widget', 'widget', 'Create new widgets'),
        ('edit_widget', 'Edit Widget', 'widget', 'Edit widget configuration'),
        ('delete_widget', 'Delete Widget', 'widget', 'Delete widgets'),
        ('preview_widget', 'Preview Widget', 'widget', 'Preview widget data'),
        
        # Dashboard Management
        ('view_dashboards', 'View Dashboards', 'dashboard', 'View dashboard list'),
        ('create_dashboard', 'Create Dashboard', 'dashboard', 'Create new dashboards'),
        ('edit_dashboard', 'Edit Dashboard', 'dashboard', 'Edit dashboard layout'),
        ('delete_dashboard', 'Delete Dashboard', 'dashboard', 'Delete dashboards'),
        ('share_dashboard', 'Share Dashboard', 'dashboard', 'Share dashboards with others'),
        ('export_dashboard', 'Export Dashboard', 'dashboard', 'Export dashboard data'),
        
        # Reporting
        ('view_reports', 'View Reports', 'report', 'View generated reports'),
        ('create_report', 'Create Report', 'report', 'Create new reports'),
        ('export_report', 'Export Report', 'report', 'Export reports to various formats'),
        
        # System Administration
        ('view_audit_logs', 'View Audit Logs', 'system', 'View system audit logs'),
        ('view_system_settings', 'View System Settings', 'system', 'View system settings'),
        ('edit_system_settings', 'Edit System Settings', 'system', 'Edit system settings'),
        ('manage_api_keys', 'Manage API Keys', 'system', 'Manage API access keys'),
    ]
    
    for code, name, category, description in default_permissions:
        if not Permission.query.filter_by(code=code).first():
            permission = Permission(
                code=code,
                name=name,
                category=category,
                description=description,
                is_system=True
            )
            db.session.add(permission)
    
    db.session.commit()


def create_default_roles():
    """Create default roles for the system"""
    # Super Admin - Full access
    super_admin = Role.query.filter_by(code='super_admin').first()
    if not super_admin:
        super_admin = Role(
            name='Super Administrator',
            code='super_admin',
            description='Full system access with all permissions',
            is_system_role=True,
            level=100,
            color='#f44336',
            icon='fa-crown'
        )
        super_admin.permissions = Permission.query.all()
        db.session.add(super_admin)
    
    # Organization Admin
    org_admin = Role.query.filter_by(code='org_admin').first()
    if not org_admin:
        org_admin = Role(
            name='Organization Administrator',
            code='org_admin',
            description='Full access within organization',
            is_system_role=True,
            level=80,
            color='#ff9800',
            icon='fa-user-shield'
        )
        # Add most permissions except system administration
        org_admin.permissions = Permission.query.filter(
            Permission.category.in_(['organization', 'user', 'role', 'data_source', 'widget', 'dashboard'])
        ).all()
        db.session.add(org_admin)
    
    # Analyst
    analyst = Role.query.filter_by(code='analyst').first()
    if not analyst:
        analyst = Role(
            name='Data Analyst',
            code='analyst',
            description='Create and manage dashboards and widgets',
            is_system_role=True,
            is_default=True,
            level=50,
            color='#2196f3',
            icon='fa-chart-line'
        )
        analyst.permissions = Permission.query.filter(
            Permission.code.in_([
                'view_data_sources', 'view_widgets', 'create_widget', 'edit_widget',
                'view_dashboards', 'create_dashboard', 'edit_dashboard', 'export_dashboard'
            ])
        ).all()
        db.session.add(analyst)
    
    # Viewer
    viewer = Role.query.filter_by(code='viewer').first()
    if not viewer:
        viewer = Role(
            name='Viewer',
            code='viewer',
            description='Read-only access to dashboards',
            is_system_role=True,
            level=10,
            color='#4caf50',
            icon='fa-eye'
        )
        viewer.permissions = Permission.query.filter(
            Permission.code.in_(['view_dashboards', 'view_widgets'])
        ).all()
        db.session.add(viewer)
    
    db.session.commit()