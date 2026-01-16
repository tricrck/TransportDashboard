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
from models import WidgetType


# ============================================================================
# WIDGET FORMS
# ============================================================================

class WidgetForm(FlaskForm):
    """Base widget form"""
    name = StringField(
        'Widget Name',
        validators=[
            DataRequired(message='Widget name is required'),
            Length(min=3, max=200)
        ],
        render_kw={'placeholder': 'e.g., Monthly Cargo Chart'}
    )
    
    reference = StringField(
        'Reference Code',
        validators=[Optional(), Length(max=100)],
        render_kw={'placeholder': 'Optional short code'}
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
    
    widget_type = SelectField(
        'Widget Type',
        choices=[
            (WidgetType.STAT_CARD.value, 'Stat Card'),
            (WidgetType.TABLE.value, 'Table'),
            (WidgetType.LIST.value, 'List'),
            (WidgetType.BAR_CHART.value, 'Bar Chart'),
            (WidgetType.LINE_CHART.value, 'Line Chart'),
            (WidgetType.PIE_CHART.value, 'Pie Chart'),
            (WidgetType.DOUGHNUT_CHART.value, 'Doughnut Chart'),
            (WidgetType.AREA_CHART.value, 'Area Chart'),
            (WidgetType.SCATTER_CHART.value, 'Scatter Chart'),
            (WidgetType.RADAR_CHART.value, 'Radar Chart'),
            (WidgetType.HEAT_MAP.value, 'Heat Map'),
            (WidgetType.FUNNEL_CHART.value, 'Funnel Chart'),
            (WidgetType.GAUGE_CHART.value, 'Gauge Chart'),
            (WidgetType.MAP.value, 'Map'),
            (WidgetType.METRIC.value, 'Metric Display')
        ],
        validators=[DataRequired()]
    )
    
    data_source = SelectField(
        'Data Source',
        coerce=int,
        validators=[DataRequired(message='Data source is required')]
    )
    
    # Display Settings
    title = StringField(
        'Display Title',
        validators=[Optional(), Length(max=200)],
        render_kw={'placeholder': 'Title shown on dashboard'}
    )
    
    subtitle = StringField(
        'Subtitle',
        validators=[Optional(), Length(max=200)],
        render_kw={'placeholder': 'Optional subtitle'}
    )
    
    icon = StringField(
        'Icon (Font Awesome)',
        validators=[Optional(), Length(max=50)],
        render_kw={'placeholder': 'e.g., fa-chart-line'}
    )
    
    color = StringField(
        'Primary Color',
        validators=[Optional()],
        render_kw={'type': 'color', 'value': '#2196f3'}
    )
    
    # Query Configuration
    query_type = SelectField(
        'Query Type',
        choices=[
            ('simple', 'Simple Query'),
            ('advanced', 'Advanced Query Builder'),
            ('custom', 'Custom Query')
        ],
        default='simple'
    )
    
    fields = TextAreaField(
        'Fields (JSON)',
        validators=[Optional()],
        render_kw={
            'rows': 4,
            'placeholder': '["field1", "field2", "field3"]'
        }
    )
    
    filters = TextAreaField(
        'Filters (JSON)',
        validators=[Optional()],
        render_kw={
            'rows': 4,
            'placeholder': '{"field": "value", "operator": "equals"}'
        }
    )
    
    aggregations = TextAreaField(
        'Aggregations (JSON)',
        validators=[Optional()],
        render_kw={
            'rows': 3,
            'placeholder': '[{"field": "amount", "function": "SUM"}]'
        }
    )
    
    sorting = TextAreaField(
        'Sorting (JSON)',
        validators=[Optional()],
        render_kw={
            'rows': 2,
            'placeholder': '{"field": "date", "order": "DESC"}'
        }
    )
    
    grouping = TextAreaField(
        'Grouping (JSON)',
        validators=[Optional()],
        render_kw={
            'rows': 2,
            'placeholder': '["month", "category"]'
        }
    )
    
    limit = IntegerField(
        'Record Limit',
        validators=[Optional(), NumberRange(min=1, max=10000)],
        default=100
    )
    
    # Display Configuration
    display_config = TextAreaField(
        'Display Configuration (JSON)',
        validators=[Optional()],
        render_kw={
            'rows': 8,
            'placeholder': 'Chart.js or table configuration',
            'style': 'font-family: monospace;'
        }
    )
    
    # KPI Settings
    show_kpi = BooleanField('Show KPI')
    
    kpi_config = TextAreaField(
        'KPI Configuration (JSON)',
        validators=[Optional()],
        render_kw={'rows': 4}
    )
    
    # Refresh Settings
    auto_refresh = BooleanField('Enable Auto-Refresh')
    
    refresh_interval = IntegerField(
        'Refresh Interval (seconds)',
        validators=[Optional(), NumberRange(min=10, max=3600)],
        default=60
    )
    
    is_active = BooleanField('Active', default=True)
    is_template = BooleanField('Save as Template')
    
    submit = SubmitField('Save Widget')


class StatCardWidgetForm(WidgetForm):
    """Stat card specific form"""
    stat_field = StringField(
        'Statistic Field',
        validators=[DataRequired()],
        render_kw={'placeholder': 'Field to display as main statistic'}
    )
    
    stat_function = SelectField(
        'Aggregation Function',
        choices=[
            ('value', 'Value'),
            ('sum', 'Sum'),
            ('avg', 'Average'),
            ('count', 'Count'),
            ('min', 'Minimum'),
            ('max', 'Maximum')
        ],
        default='value'
    )
    
    comparison_field = StringField(
        'Comparison Field',
        validators=[Optional()],
        description='Optional: Field to compare against'
    )
    
    show_trend = BooleanField('Show Trend Arrow', default=True)
    
    submit = SubmitField('Save Stat Card')


class ChartWidgetForm(WidgetForm):
    """Chart widget specific form"""
    x_axis_field = StringField(
        'X-Axis Field',
        validators=[DataRequired()],
        render_kw={'placeholder': 'e.g., month, date'}
    )
    
    y_axis_field = StringField(
        'Y-Axis Field',
        validators=[DataRequired()],
        render_kw={'placeholder': 'e.g., amount, count'}
    )
    
    series_field = StringField(
        'Series Field',
        validators=[Optional()],
        description='Optional: Field for multiple series'
    )
    
    chart_title = StringField(
        'Chart Title',
        validators=[Optional(), Length(max=200)]
    )
    
    x_axis_label = StringField(
        'X-Axis Label',
        validators=[Optional(), Length(max=100)]
    )
    
    y_axis_label = StringField(
        'Y-Axis Label',
        validators=[Optional(), Length(max=100)]
    )
    
    show_legend = BooleanField('Show Legend', default=True)
    show_grid = BooleanField('Show Grid', default=True)
    show_tooltips = BooleanField('Show Tooltips', default=True)
    
    submit = SubmitField('Save Chart Widget')


class TableWidgetForm(WidgetForm):
    """Table widget specific form"""
    columns = TextAreaField(
        'Columns (JSON)',
        validators=[DataRequired()],
        render_kw={
            'rows': 6,
            'placeholder': '[{"field": "name", "header": "Name", "sortable": true}]'
        }
    )
    
    enable_pagination = BooleanField('Enable Pagination', default=True)
    
    page_size = IntegerField(
        'Rows Per Page',
        validators=[Optional(), NumberRange(min=5, max=100)],
        default=10
    )
    
    enable_search = BooleanField('Enable Search', default=True)
    enable_export = BooleanField('Enable Export', default=True)
    
    submit = SubmitField('Save Table Widget')


class WidgetConfigForm(FlaskForm):
    """Widget configuration form for advanced settings"""
    widget_id = HiddenField(validators=[DataRequired()])
    
    query_config = TextAreaField(
        'Query Configuration',
        validators=[Optional()],
        render_kw={'rows': 10, 'style': 'font-family: monospace;'}
    )
    
    display_config = TextAreaField(
        'Display Configuration',
        validators=[Optional()],
        render_kw={'rows': 10, 'style': 'font-family: monospace;'}
    )
    
    kpi_config = TextAreaField(
        'KPI Configuration',
        validators=[Optional()],
        render_kw={'rows': 6, 'style': 'font-family: monospace;'}
    )
    
    custom_css = TextAreaField(
        'Custom CSS',
        validators=[Optional()],
        render_kw={'rows': 8, 'style': 'font-family: monospace;'}
    )
    
    custom_js = TextAreaField(
        'Custom JavaScript',
        validators=[Optional()],
        render_kw={'rows': 8, 'style': 'font-family: monospace;'}
    )
    
    submit = SubmitField('Update Configuration')
