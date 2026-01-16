# blueprints/__init__.py
"""
Blueprints Package
Flask blueprints for modular route organization
"""

from .auth import auth_bp
from .admin import admin_bp, main_bp
from .data_sources import data_sources_bp
from .dashboard import widgets_bp
from .dashboard import dashboards_bp
from .dashboard import api_bp, profile_bp

__all__ = [
    'auth_bp',
    'admin_bp',
    'data_sources_bp',
    'widgets_bp',
    'dashboards_bp',
    'api_bp',
    'main_bp',
    'profile_bp'
]