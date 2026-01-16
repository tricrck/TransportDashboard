"""
Widget and Dashboard Models
Visualization and presentation layer
"""

from datetime import datetime
import enum
from sqlalchemy import event
from . import db


class WidgetType(enum.Enum):
    """Widget visualization types"""
    STAT_CARD = 'stat_card'
    TABLE = 'table'
    LIST = 'list'
    BAR_CHART = 'bar_chart'
    LINE_CHART = 'line_chart'
    PIE_CHART = 'pie_chart'
    DOUGHNUT_CHART = 'doughnut_chart'
    AREA_CHART = 'area_chart'
    SCATTER_CHART = 'scatter_chart'
    RADAR_CHART = 'radar_chart'
    POLAR_CHART = 'polar_chart'
    BUBBLE_CHART = 'bubble_chart'
    HEAT_MAP = 'heat_map'
    FUNNEL_CHART = 'funnel_chart'
    GAUGE_CHART = 'gauge_chart'
    MAP = 'map'
    TIMELINE = 'timeline'
    METRIC = 'metric'


class Widget(db.Model):
    """
    Widget model for data visualization
    Configurable components for dashboards
    """
    __tablename__ = 'widgets'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Identification
    name = db.Column(db.String(200), nullable=False, index=True)
    reference = db.Column(db.String(100))
    description = db.Column(db.Text)
    tags = db.Column(db.JSON)
    
    # Widget Configuration
    widget_type = db.Column(db.Enum(WidgetType), nullable=False)
    
    # Display Settings
    title = db.Column(db.String(200))
    subtitle = db.Column(db.String(200))
    icon = db.Column(db.String(50))  # Font Awesome icon
    color = db.Column(db.String(7))  # Primary color
    
    # Query Configuration
    query_config = db.Column(db.JSON)  # SQL-like query or filter configuration
    query_type = db.Column(db.String(50), default='simple')  # simple, advanced, custom
    
    # Data fields to fetch
    fields = db.Column(db.JSON)  # Array of field configurations
    filters = db.Column(db.JSON)  # Filter conditions
    aggregations = db.Column(db.JSON)  # Aggregation functions (SUM, AVG, COUNT, etc.)
    sorting = db.Column(db.JSON)  # Sort configuration
    grouping = db.Column(db.JSON)  # Group by configuration
    limit = db.Column(db.Integer)  # Record limit
    
    # Display Configuration
    display_config = db.Column(db.JSON)  # Chart.js or table configuration
    custom_css = db.Column(db.Text)  # Custom CSS
    custom_js = db.Column(db.Text)  # Custom JavaScript
    
    # KPI Configuration
    kpi_config = db.Column(db.JSON)  # KPI calculation and display
    show_kpi = db.Column(db.Boolean, default=False)
    kpi_position = db.Column(db.String(20), default='top')  # top, bottom, left, right
    
    # Interactivity
    is_interactive = db.Column(db.Boolean, default=True)
    click_action = db.Column(db.String(50))  # drill_down, navigate, modal, etc.
    drill_down_config = db.Column(db.JSON)
    
    # Refresh Settings
    auto_refresh = db.Column(db.Boolean, default=False)
    refresh_interval = db.Column(db.Integer, default=60)  # Seconds
    last_rendered = db.Column(db.DateTime)
    
    # Cache
    cache_enabled = db.Column(db.Boolean, default=True)
    cached_data = db.Column(db.JSON)
    cached_at = db.Column(db.DateTime)
    
    # Permissions
    is_public = db.Column(db.Boolean, default=False)
    allowed_roles = db.Column(db.JSON)  # Array of role IDs
    
    # Status & Metadata
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_template = db.Column(db.Boolean, default=False)
    version = db.Column(db.Integer, default=1)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    data_source_id = db.Column(db.Integer, db.ForeignKey('data_sources.id'), nullable=False, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    dashboard_widgets = db.relationship('DashboardWidget', backref='widget', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Widget {self.name}>'
    
    @property
    def dashboard_count(self):
        """Get number of dashboards using this widget"""
        return self.dashboard_widgets.count()
    
    def to_dict(self, include_config=False):
        """Convert widget to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'reference': self.reference,
            'description': self.description,
            'widget_type': self.widget_type.value if self.widget_type else None,
            'title': self.title,
            'subtitle': self.subtitle,
            'icon': self.icon,
            'color': self.color,
            'is_active': self.is_active,
            'is_template': self.is_template,
            'auto_refresh': self.auto_refresh,
            'refresh_interval': self.refresh_interval,
            'dashboard_count': self.dashboard_count,
            'data_source': {
                'id': self.data_source.id,
                'name': self.data_source.name
            } if self.data_source else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_config:
            data.update({
                'query_config': self.query_config,
                'display_config': self.display_config,
                'kpi_config': self.kpi_config,
                'fields': self.fields,
                'filters': self.filters,
                'aggregations': self.aggregations,
                'sorting': self.sorting,
                'grouping': self.grouping,
            })
        
        return data


# Event listeners
@event.listens_for(Widget, 'before_update')
def update_widget_timestamp(mapper, connection, target):
    """Update timestamp and version"""
    target.updated_at = datetime.utcnow()
    target.version += 1
