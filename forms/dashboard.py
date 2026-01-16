"""
Widget and Dashboard Forms
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, IntegerField,
    BooleanField, SubmitField, HiddenField, SelectMultipleField
)
from wtforms.validators import (
    DataRequired, Optional, Length, NumberRange, ValidationError
)


class DashboardForm(FlaskForm):
    """Dashboard create/edit form"""
    name = StringField(
        'Dashboard Name',
        validators=[
            DataRequired(message='Dashboard name is required'),
            Length(min=3, max=200)
        ],
        render_kw={'placeholder': 'e.g., Port Operations Overview'}
    )
    
    slug = StringField(
        'URL Slug',
        validators=[Optional(), Length(max=200)],
        render_kw={'placeholder': 'auto-generated from name'}
    )
    
    description = TextAreaField(
        'Description',
        validators=[Length(max=1000)],
        render_kw={'rows': 3}
    )
    
    tags = StringField(
        'Tags',
        validators=[Optional()],
        render_kw={'placeholder': 'Comma-separated tags'}
    )
    
    # Layout Configuration
    layout_type = SelectField(
        'Layout Type',
        choices=[
            ('grid', 'Grid Layout'),
            ('flex', 'Flexible Layout'),
            ('custom', 'Custom Layout')
        ],
        default='grid'
    )
    
    columns = IntegerField(
        'Grid Columns',
        validators=[NumberRange(min=1, max=24)],
        default=12,
        description='Number of columns in grid (1-24)'
    )
    
    row_height = IntegerField(
        'Row Height (pixels)',
        validators=[NumberRange(min=50, max=500)],
        default=100
    )
    
    gap = IntegerField(
        'Gap Between Widgets (pixels)',
        validators=[NumberRange(min=0, max=50)],
        default=20
    )
    
    # Theme & Styling
    theme = SelectField(
        'Theme',
        choices=[
            ('light', 'Light'),
            ('dark', 'Dark'),
            ('auto', 'Auto (System)')
        ],
        default='light'
    )
    
    background_color = StringField(
        'Background Color',
        validators=[Optional()],
        render_kw={'type': 'color', 'value': '#f0f2f5'}
    )
    
    custom_css = TextAreaField(
        'Custom CSS',
        validators=[Optional()],
        render_kw={
            'rows': 8,
            'style': 'font-family: monospace;'
        }
    )
    
    # Behavior
    auto_refresh = BooleanField('Enable Auto-Refresh')
    
    refresh_interval = IntegerField(
        'Refresh Interval (seconds)',
        validators=[Optional(), NumberRange(min=30, max=3600)],
        default=300
    )
    
    enable_filters = BooleanField('Enable Filters', default=True)
    enable_export = BooleanField('Enable Export', default=True)
    enable_fullscreen = BooleanField('Enable Fullscreen', default=True)
    
    # Access Control
    is_public = BooleanField('Public Dashboard')
    is_default = BooleanField('Set as Default Dashboard')
    
    allowed_roles = SelectMultipleField(
        'Allowed Roles',
        coerce=int,
        description='Leave empty to allow all roles'
    )
    
    is_active = BooleanField('Active', default=True)
    is_template = BooleanField('Save as Template')
    
    submit = SubmitField('Save Dashboard')


class DashboardLayoutForm(FlaskForm):
    """Dashboard layout configuration form"""
    dashboard_id = HiddenField(validators=[DataRequired()])
    
    layout_config = TextAreaField(
        'Layout Configuration (JSON)',
        validators=[Optional()],
        render_kw={
            'rows': 15,
            'style': 'font-family: monospace;',
            'placeholder': 'Widget positions and sizes in JSON format'
        }
    )
    
    submit = SubmitField('Update Layout')


class DashboardWidgetAddForm(FlaskForm):
    """Form for adding widget to dashboard"""
    dashboard_id = HiddenField(validators=[DataRequired()])
    
    widget = SelectField(
        'Widget',
        coerce=int,
        validators=[DataRequired(message='Please select a widget')]
    )
    
    position_x = IntegerField(
        'Position X',
        validators=[NumberRange(min=0)],
        default=0
    )
    
    position_y = IntegerField(
        'Position Y',
        validators=[NumberRange(min=0)],
        default=0
    )
    
    width = IntegerField(
        'Width (columns)',
        validators=[NumberRange(min=1, max=12)],
        default=4
    )
    
    height = IntegerField(
        'Height (rows)',
        validators=[NumberRange(min=1, max=10)],
        default=3
    )
    
    submit = SubmitField('Add Widget')


class DashboardShareForm(FlaskForm):
    """Form for sharing dashboard"""
    dashboard_id = HiddenField(validators=[DataRequired()])
    
    share_with = SelectMultipleField(
        'Share With',
        coerce=int,
        validators=[DataRequired(message='Please select at least one user')],
        description='Select users to share this dashboard with'
    )
    
    send_notification = BooleanField(
        'Send Notification',
        default=True,
        description='Notify users when dashboard is shared'
    )
    
    message = TextAreaField(
        'Optional Message',
        validators=[Optional(), Length(max=500)],
        render_kw={'rows': 3, 'placeholder': 'Add a message for recipients'}
    )
    
    submit = SubmitField('Share Dashboard')


class DashboardExportForm(FlaskForm):
    """Form for exporting dashboard"""
    dashboard_id = HiddenField(validators=[DataRequired()])
    
    export_format = SelectField(
        'Export Format',
        choices=[
            ('pdf', 'PDF Document'),
            ('png', 'PNG Image'),
            ('json', 'JSON Data'),
            ('csv', 'CSV Data')
        ],
        validators=[DataRequired()]
    )
    
    include_data = BooleanField('Include Current Data', default=True)
    include_config = BooleanField('Include Configuration', default=False)
    
    submit = SubmitField('Export Dashboard')
    