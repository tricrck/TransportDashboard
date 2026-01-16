from datetime import datetime
import enum
from sqlalchemy import event
from . import db


class Dashboard(db.Model):
    """
    Dashboard model for organizing widgets
    Provides customizable layouts for data visualization
    """
    __tablename__ = 'dashboards'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Identification
    name = db.Column(db.String(200), nullable=False, index=True)
    slug = db.Column(db.String(200), unique=True, index=True)
    description = db.Column(db.Text)
    tags = db.Column(db.JSON)
    
    # Layout Configuration
    layout_type = db.Column(db.String(50), default='grid')  # grid, flex, custom
    layout_config = db.Column(db.JSON)  # Grid/flex configuration
    columns = db.Column(db.Integer, default=12)  # Grid columns
    row_height = db.Column(db.Integer, default=100)  # Pixels
    gap = db.Column(db.Integer, default=20)  # Gap between widgets
    
    # Theme & Styling
    theme = db.Column(db.String(20), default='light')
    background_color = db.Column(db.String(7), default='#f0f2f5')
    background_image = db.Column(db.String(500))
    custom_css = db.Column(db.Text)
    
    # Behavior
    auto_refresh = db.Column(db.Boolean, default=False)
    refresh_interval = db.Column(db.Integer, default=300)  # Seconds
    enable_filters = db.Column(db.Boolean, default=True)
    enable_export = db.Column(db.Boolean, default=True)
    enable_fullscreen = db.Column(db.Boolean, default=True)
    
    # Sharing & Permissions
    is_public = db.Column(db.Boolean, default=False)
    is_default = db.Column(db.Boolean, default=False)
    share_token = db.Column(db.String(100))
    allowed_roles = db.Column(db.JSON)
    
    # Status & Metadata
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_template = db.Column(db.Boolean, default=False)
    view_count = db.Column(db.Integer, default=0)
    last_viewed = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    dashboard_widgets = db.relationship('DashboardWidget', backref='dashboard', lazy='dynamic', 
                                       cascade='all, delete-orphan', order_by='DashboardWidget.position_y, DashboardWidget.position_x')
    
    def __repr__(self):
        return f'<Dashboard {self.name}>'
    
    @property
    def widget_count(self):
        """Get number of widgets in dashboard"""
        return self.dashboard_widgets.count()
    
    def add_widget(self, widget, position_x=0, position_y=0, width=4, height=3):
        """Add widget to dashboard"""
        dw = DashboardWidget(
            dashboard_id=self.id,
            widget_id=widget.id,
            position_x=position_x,
            position_y=position_y,
            width=width,
            height=height
        )
        db.session.add(dw)
        db.session.commit()
        return dw
    
    def remove_widget(self, widget):
        """Remove widget from dashboard"""
        dw = self.dashboard_widgets.filter_by(widget_id=widget.id).first()
        if dw:
            db.session.delete(dw)
            db.session.commit()
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        self.last_viewed = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self, include_widgets=False):
        """Convert dashboard to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'tags': self.tags,
            'layout_type': self.layout_type,
            'columns': self.columns,
            'theme': self.theme,
            'is_public': self.is_public,
            'is_default': self.is_default,
            'is_active': self.is_active,
            'widget_count': self.widget_count,
            'view_count': self.view_count,
            'organization': {
                'id': self.organization.id,
                'name': self.organization.name
            } if self.organization else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_widgets:
            data['widgets'] = [dw.to_dict() for dw in self.dashboard_widgets.all()]
        
        return data


class DashboardWidget(db.Model):
    """
    Association between dashboards and widgets
    Includes positioning and sizing information
    """
    __tablename__ = 'dashboard_widgets'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Position & Size
    position_x = db.Column(db.Integer, default=0, nullable=False)
    position_y = db.Column(db.Integer, default=0, nullable=False)
    width = db.Column(db.Integer, default=4, nullable=False)
    height = db.Column(db.Integer, default=3, nullable=False)
    
    # Display Override
    title_override = db.Column(db.String(200))
    color_override = db.Column(db.String(7))
    
    # Widget-specific filters
    local_filters = db.Column(db.JSON)
    
    # Order
    display_order = db.Column(db.Integer, default=0)
    
    # Status
    is_visible = db.Column(db.Boolean, default=True)
    is_locked = db.Column(db.Boolean, default=False)  # Prevent moving/resizing
    
    # Timestamps
    added_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Foreign Keys
    dashboard_id = db.Column(db.Integer, db.ForeignKey('dashboards.id'), nullable=False, index=True)
    widget_id = db.Column(db.Integer, db.ForeignKey('widgets.id'), nullable=False, index=True)
    
    def __repr__(self):
        return f'<DashboardWidget D:{self.dashboard_id} W:{self.widget_id}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'position_x': self.position_x,
            'position_y': self.position_y,
            'width': self.width,
            'height': self.height,
            'is_visible': self.is_visible,
            'is_locked': self.is_locked,
            'widget': self.widget.to_dict(include_config=True) if self.widget else None
        }

@event.listens_for(Dashboard, 'before_update')
def update_dashboard_timestamp(mapper, connection, target):
    """Update timestamp"""
    target.updated_at = datetime.utcnow()


@event.listens_for(Dashboard, 'before_insert')
def generate_slug(mapper, connection, target):
    """Generate URL-friendly slug"""
    if not target.slug:
        import re
        slug = re.sub(r'[^\w\s-]', '', target.name.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        target.slug = slug