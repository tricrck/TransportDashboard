"""
Database Models Package
Centralized model definitions
"""

from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

# ---- Core models (NO services, NO app, NO current_app) ----
from .organization import Organization
from .permission import Permission, Role, role_permissions
from .user import User

from .data_source import (
    DataSource,
    DataSourceType,
    AuthType,
    DataFormat
)

from .widget import Widget, WidgetType
from .dashboard import Dashboard, DashboardWidget

# ---- Logging / audit models (SAFE ONLY) ----
from .support import (
    AuditLog,
    AuditAction,
    Notification,
    NotificationType,
    APIKey,
    DataRefreshLog
)

from .data_validation_log import DataValidationLog

__all__ = [
    'db',
    'Organization',
    'Permission',
    'Role',
    'role_permissions',
    'User',
    'DataSource',
    'DataSourceType',
    'AuthType',
    'DataFormat',
    'Widget',
    'WidgetType',
    'Dashboard',
    'DashboardWidget',
    'AuditLog',
    'AuditAction',
    'Notification',
    'NotificationType',
    'APIKey',
    'DataRefreshLog',
    'DataValidationLog',
]