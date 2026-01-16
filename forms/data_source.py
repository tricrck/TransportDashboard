"""
Data Source Forms - Enhanced
Dynamic forms with auto-populated enums and validation
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import (
    StringField, TextAreaField, SelectField, IntegerField,
    BooleanField, PasswordField, SubmitField, HiddenField
)
from wtforms.validators import (
    DataRequired, Optional, Length, NumberRange, URL, ValidationError
)
from models import DataSourceType, AuthType, DataFormat


class DynamicEnumSelectField(SelectField):
    """Select field that dynamically populates from enum"""
    def __init__(self, enum_class, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choices = [(e.value, e.value.replace('_', ' ').title()) for e in enum_class]


class DataSourceForm(FlaskForm):
    """Base data source form with common fields"""
    
    name = StringField(
        'Data Source Name',
        validators=[
            DataRequired(message='Name is required'),
            Length(min=3, max=200)
        ],
        render_kw={'placeholder': 'e.g., Mombasa Port Traffic API', 'class': 'form-control'}
    )
    
    reference = StringField(
        'Reference Code',
        validators=[Optional(), Length(max=100)],
        render_kw={'placeholder': 'Short code (optional)', 'class': 'form-control'},
        description='Unique short code for easy reference'
    )
    
    description = TextAreaField(
        'Description',
        validators=[Optional(), Length(max=1000)],
        render_kw={'rows': 3, 'placeholder': 'Describe this data source', 'class': 'form-control'}
    )
    
    tags = StringField(
        'Tags',
        validators=[Optional()],
        render_kw={'placeholder': 'port, cargo, real-time (comma-separated)', 'class': 'form-control'}
    )
    
    # Refresh Settings
    auto_refresh = BooleanField(
        'Enable Auto-Refresh',
        description='Automatically fetch data at specified intervals'
    )
    
    refresh_frequency = IntegerField(
        'Refresh Frequency (seconds)',
        validators=[Optional(), NumberRange(min=30, max=86400)],
        default=300,
        render_kw={'class': 'form-control'},
        description='30 seconds to 24 hours'
    )
    
    # Cache Settings
    cache_enabled = BooleanField('Enable Caching', default=True)
    
    cache_ttl = IntegerField(
        'Cache Duration (seconds)',
        validators=[Optional(), NumberRange(min=60, max=3600)],
        default=300,
        render_kw={'class': 'form-control'},
        description='60 seconds to 1 hour'
    )
    
    # Validation
    validation_enabled = BooleanField('Enable Data Validation')
    
    # Alert Settings
    alert_on_failure = BooleanField('Alert on Failure', default=True)
    
    alert_threshold = IntegerField(
        'Alert Threshold (failures)',
        validators=[Optional(), NumberRange(min=1, max=10)],
        default=3,
        render_kw={'class': 'form-control'}
    )
    
    is_active = BooleanField('Active', default=True)
    
    submit = SubmitField('Save Data Source', render_kw={'class': 'btn btn-primary'})


class APIDataSourceForm(DataSourceForm):
    """API endpoint data source form"""
    
    source_type = HiddenField(default='api')
    
    data_format = SelectField(
        'Data Format',
        choices=[
            ('json', 'JSON'),
            ('csv', 'CSV'),
            ('xml', 'XML'),
            ('html', 'HTML'),
            ('txt', 'Text')
        ],
        validators=[DataRequired()],
        render_kw={'class': 'form-control'}
    )
    
    api_endpoint = StringField(
        'API Endpoint URL',
        validators=[
            DataRequired(message='API endpoint is required'),
            URL(message='Must be a valid URL'),
            Length(max=500)
        ],
        render_kw={'placeholder': 'https://api.example.com/v1/data', 'class': 'form-control'}
    )
    
    api_method = SelectField(
        'HTTP Method',
        choices=[
            ('GET', 'GET'),
            ('POST', 'POST'),
            ('PUT', 'PUT'),
            ('PATCH', 'PATCH')
        ],
        default='GET',
        render_kw={'class': 'form-control'}
    )
    
    api_timeout = IntegerField(
        'Request Timeout (seconds)',
        validators=[Optional(), NumberRange(min=5, max=300)],
        default=30,
        render_kw={'class': 'form-control'}
    )
    
    # Authentication
    auth_type = SelectField(
        'Authentication Type',
        choices=[
            ('none', 'None'),
            ('basic', 'Basic Authentication'),
            ('bearer', 'Bearer Token'),
            ('api_key', 'API Key'),
            ('query_param', 'Query Parameter')
        ],
        default='none',
        render_kw={'class': 'form-control', 'id': 'auth_type'}
    )
    
    # Basic Auth
    auth_username = StringField(
        'Username',
        validators=[Optional(), Length(max=200)],
        render_kw={'autocomplete': 'off', 'class': 'form-control'}
    )
    
    auth_password = PasswordField(
        'Password',
        validators=[Optional()],
        render_kw={'autocomplete': 'new-password', 'class': 'form-control'}
    )
    
    # Bearer/API Key
    auth_token = StringField(
        'Token / API Key',
        validators=[Optional(), Length(max=500)],
        render_kw={'placeholder': 'Enter your API token or key', 'class': 'form-control'}
    )
    
    # Query Parameters
    api_params = TextAreaField(
        'Query Parameters (JSON)',
        validators=[Optional()],
        render_kw={
            'rows': 4,
            'placeholder': '{"key1": "value1", "key2": "value2"}',
            'class': 'form-control font-monospace'
        }
    )
    
    # Custom Headers
    api_headers = TextAreaField(
        'Custom Headers (JSON)',
        validators=[Optional()],
        render_kw={
            'rows': 4,
            'placeholder': '{"Content-Type": "application/json"}',
            'class': 'form-control font-monospace'
        }
    )
    
    # Request Body
    api_body = TextAreaField(
        'Request Body (JSON)',
        validators=[Optional()],
        render_kw={
            'rows': 6,
            'placeholder': 'Request body for POST/PUT/PATCH methods',
            'class': 'form-control font-monospace'
        }
    )
    
    # Data Path
    data_path = StringField(
        'Data Path (JSONPath)',
        validators=[Optional(), Length(max=500)],
        render_kw={'placeholder': '$.data.items or data.results', 'class': 'form-control'},
        description='Path to extract data from API response'
    )
    
    def validate_api_params(self, field):
        """Validate JSON format for params"""
        if field.data:
            import json
            try:
                json.loads(field.data)
            except json.JSONDecodeError:
                raise ValidationError('Invalid JSON format')
    
    def validate_api_headers(self, field):
        """Validate JSON format for headers"""
        if field.data:
            import json
            try:
                json.loads(field.data)
            except json.JSONDecodeError:
                raise ValidationError('Invalid JSON format')
    
    def validate_api_body(self, field):
        """Validate JSON format for body"""
        if field.data:
            import json
            try:
                json.loads(field.data)
            except json.JSONDecodeError:
                raise ValidationError('Invalid JSON format')
    
    submit = SubmitField('Save API Data Source', render_kw={'class': 'btn btn-primary'})


class UploadDataSourceForm(DataSourceForm):
    """File upload data source form"""
    
    source_type = HiddenField(default='upload')
    
    file = FileField(
        'Upload File',
        validators=[
            FileRequired(message='Please select a file'),
            FileAllowed(
                ['json', 'csv', 'xml', 'xlsx', 'xls', 'parquet', 'pdf', 'docx', 'txt', 'html'],
                'Supported: JSON, CSV, XML, Excel, Parquet, PDF, DOCX, TXT, HTML'
            )
        ],
        render_kw={'class': 'form-control', 'accept': '.json,.csv,.xml,.xlsx,.xls,.parquet,.pdf,.docx,.txt,.html'}
    )
    
    data_format = SelectField(
        'Data Format',
        choices=[
            ('auto', 'Auto-Detect'),
            ('json', 'JSON'),
            ('csv', 'CSV'),
            ('xml', 'XML'),
            ('excel', 'Excel'),
            ('parquet', 'Parquet'),
            ('pdf', 'PDF'),
            ('docx', 'Word Document'),
            ('txt', 'Text'),
            ('html', 'HTML')
        ],
        default='auto',
        validators=[DataRequired()],
        render_kw={'class': 'form-control'}
    )
    
    # CSV-specific options
    csv_delimiter = StringField(
        'CSV Delimiter',
        validators=[Optional(), Length(max=5)],
        default=',',
        render_kw={'placeholder': 'Default: comma (,)', 'class': 'form-control'}
    )
    
    csv_has_header = BooleanField('CSV Has Header Row', default=True)
    
    # Excel-specific options
    excel_sheet_name = StringField(
        'Excel Sheet Name',
        validators=[Optional(), Length(max=100)],
        render_kw={'placeholder': 'Leave blank for first sheet', 'class': 'form-control'}
    )
    
    submit = SubmitField('Upload & Save', render_kw={'class': 'btn btn-primary'})


class LinkDataSourceForm(DataSourceForm):
    """External file link data source form"""
    
    source_type = HiddenField(default='link')
    
    file_url = StringField(
        'File URL',
        validators=[
            DataRequired(message='File URL is required'),
            URL(message='Must be a valid URL'),
            Length(max=1000)
        ],
        render_kw={'placeholder': 'https://example.com/data/file.csv', 'class': 'form-control'}
    )
    
    data_format = SelectField(
        'Data Format',
        choices=[
            ('auto', 'Auto-Detect'),
            ('json', 'JSON'),
            ('csv', 'CSV'),
            ('xml', 'XML'),
            ('excel', 'Excel'),
            ('parquet', 'Parquet'),
            ('pdf', 'PDF'),
            ('txt', 'Text')
        ],
        default='auto',
        validators=[DataRequired()],
        render_kw={'class': 'form-control'}
    )
    
    # Authentication for protected files
    requires_auth = BooleanField('Requires Authentication')
    
    auth_type = SelectField(
        'Authentication Type',
        choices=[
            ('none', 'None'),
            ('basic', 'Basic Authentication'),
            ('bearer', 'Bearer Token'),
            ('api_key', 'API Key')
        ],
        default='none',
        render_kw={'class': 'form-control'}
    )
    
    auth_username = StringField(
        'Username',
        validators=[Optional(), Length(max=200)],
        render_kw={'class': 'form-control'}
    )
    
    auth_password = PasswordField(
        'Password',
        validators=[Optional()],
        render_kw={'class': 'form-control'}
    )
    
    auth_token = StringField(
        'Token',
        validators=[Optional(), Length(max=500)],
        render_kw={'class': 'form-control'}
    )
    
    submit = SubmitField('Save Link Data Source', render_kw={'class': 'btn btn-primary'})


class DatabaseDataSourceForm(DataSourceForm):
    """Database connection data source form"""
    
    source_type = HiddenField(default='database')
    
    db_type = SelectField(
        'Database Type',
        choices=[
            ('postgresql', 'PostgreSQL'),
            ('mysql', 'MySQL / MariaDB'),
            ('mssql', 'Microsoft SQL Server'),
            ('oracle', 'Oracle'),
            ('sqlite', 'SQLite')
        ],
        validators=[DataRequired()],
        render_kw={'class': 'form-control'}
    )
    
    db_host = StringField(
        'Host',
        validators=[DataRequired(), Length(max=200)],
        render_kw={'placeholder': 'localhost or database.example.com', 'class': 'form-control'}
    )
    
    db_port = IntegerField(
        'Port',
        validators=[Optional(), NumberRange(min=1, max=65535)],
        default=5432,
        render_kw={'class': 'form-control'}
    )
    
    db_name = StringField(
        'Database Name',
        validators=[DataRequired(), Length(max=200)],
        render_kw={'class': 'form-control'}
    )
    
    db_username = StringField(
        'Username',
        validators=[DataRequired(), Length(max=200)],
        render_kw={'class': 'form-control'}
    )
    
    db_password = PasswordField(
        'Password',
        validators=[DataRequired()],
        render_kw={'autocomplete': 'new-password', 'class': 'form-control'}
    )
    
    db_schema = StringField(
        'Schema',
        validators=[Optional(), Length(max=100)],
        default='public',
        render_kw={'class': 'form-control'}
    )
    
    db_table = StringField(
        'Table Name',
        validators=[Optional(), Length(max=200)],
        render_kw={'placeholder': 'Optional: specific table', 'class': 'form-control'},
        description='Leave blank to specify in query'
    )
    
    query_string = TextAreaField(
        'SQL Query',
        validators=[Optional()],
        render_kw={
            'rows': 8,
            'placeholder': 'SELECT * FROM table_name WHERE ...',
            'class': 'form-control font-monospace'
        },
        description='Optional: custom SQL query'
    )
    
    data_format = HiddenField(default='json')  # Database results are always JSON
    
    submit = SubmitField('Save Database Connection', render_kw={'class': 'btn btn-primary'})


class QueryDataSourceForm(DataSourceForm):
    """Custom query/script data source form"""
    
    source_type = HiddenField(default='query')
    
    data_format = SelectField(
        'Data Format',
        choices=[
            ('json', 'JSON'),
            ('csv', 'CSV'),
            ('xml', 'XML'),
            ('txt', 'Text')
        ],
        default='json',
        validators=[DataRequired()],
        render_kw={'class': 'form-control'}
    )
    
    query_string = TextAreaField(
        'Query / Script',
        validators=[DataRequired()],
        render_kw={
            'rows': 10,
            'placeholder': 'Enter your query or script here',
            'class': 'form-control font-monospace'
        },
        description='Custom query or script to fetch data'
    )
    
    query_type = SelectField(
        'Query Type',
        choices=[
            ('sql', 'SQL Query'),
            ('python', 'Python Script'),
            ('custom', 'Custom Script')
        ],
        default='sql',
        render_kw={'class': 'form-control'}
    )
    
    submit = SubmitField('Save Query Data Source', render_kw={'class': 'btn btn-primary'})


class ValidationRuleForm(FlaskForm):
    """Form for adding validation rules"""
    
    column_name = StringField(
        'Column Name',
        validators=[DataRequired(), Length(max=200)],
        render_kw={'class': 'form-control'}
    )
    
    rule_type = SelectField(
        'Rule Type',
        choices=[
            ('required', 'Required (Not Null)'),
            ('type_check', 'Type Check'),
            ('range', 'Range Check'),
            ('pattern', 'Pattern Match (Regex)'),
            ('unique', 'Unique Values'),
            ('custom', 'Custom Expression')
        ],
        validators=[DataRequired()],
        render_kw={'class': 'form-control'}
    )
    
    rule_params = TextAreaField(
        'Rule Parameters (JSON)',
        validators=[Optional()],
        render_kw={
            'rows': 3,
            'placeholder': '{"min": 0, "max": 100}',
            'class': 'form-control font-monospace'
        }
    )
    
    error_message = StringField(
        'Error Message',
        validators=[Optional(), Length(max=200)],
        render_kw={'placeholder': 'Custom error message', 'class': 'form-control'}
    )
    
    submit = SubmitField('Add Rule', render_kw={'class': 'btn btn-sm btn-secondary'})


class DataSourceTestForm(FlaskForm):
    """Form for testing data source connection"""
    data_source_id = HiddenField(validators=[DataRequired()])
    submit = SubmitField('Test Connection', render_kw={'class': 'btn btn-warning'})


class DataSourceRefreshForm(FlaskForm):
    """Form for manually refreshing data source"""
    data_source_id = HiddenField(validators=[DataRequired()])
    force_refresh = BooleanField('Force Refresh (bypass cache)', default=True)
    submit = SubmitField('Refresh Now', render_kw={'class': 'btn btn-info'})


class SchemaInferenceForm(FlaskForm):
    """Form for triggering schema inference"""
    data_source_id = HiddenField(validators=[DataRequired()])
    sample_size = IntegerField(
        'Sample Size (rows)',
        validators=[Optional(), NumberRange(min=10, max=1000)],
        default=100,
        render_kw={'class': 'form-control'}
    )
    submit = SubmitField('Infer Schema', render_kw={'class': 'btn btn-secondary'})