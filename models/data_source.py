"""
Data Source Model - Enhanced
Manages external data connections with full validation, schema inference, and health monitoring
"""

from datetime import datetime, timedelta
import enum
import mimetypes
# import magic
from sqlalchemy import event, text
from cryptography.fernet import Fernet
import os

from . import db


class DataSourceType(enum.Enum):
    """Data source connection types"""
    API = 'api'
    UPLOAD = 'upload'
    DATABASE = 'database'
    WEBSOCKET = 'websocket'
    DOCUMENT = 'document'
    SPREADSHEET = 'spreadsheet'
    LINK = 'link'  # External URL to file


class AuthType(enum.Enum):
    """Authentication methods"""
    NONE = 'none'
    BASIC = 'basic'
    BEARER = 'bearer'
    API_KEY = 'api_key'
    OAUTH2 = 'oauth2'
    QUERY_PARAM = 'query_param'


class DataFormat(enum.Enum):
    """Supported data formats"""
    JSON = 'json'
    CSV = 'csv'
    XML = 'xml'
    EXCEL = 'excel'
    PARQUET = 'parquet'
    PDF = 'pdf'
    DOCX = 'docx'
    TXT = 'txt'
    HTML = 'html'


class ValidationRuleType(enum.Enum):
    """Validation rule types"""
    REQUIRED = 'required'
    TYPE_CHECK = 'type_check'
    RANGE = 'range'
    PATTERN = 'pattern'
    UNIQUE = 'unique'
    CUSTOM = 'custom'


class DataSource(db.Model):
    """
    Enhanced data source model with schema inference, validation, and monitoring
    """
    __tablename__ = 'data_sources'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Identification
    name = db.Column(db.String(200), nullable=False, index=True)
    reference = db.Column(db.String(100), unique=True, index=True)
    description = db.Column(db.Text)
    tags = db.Column(db.JSON)
    
    # Source Configuration
    source_type = db.Column(db.Enum(DataSourceType), nullable=False, index=True)
    data_format = db.Column(db.Enum(DataFormat), nullable=False)
    detected_format = db.Column(db.Enum(DataFormat))  # Auto-detected format
    mime_type = db.Column(db.String(100))
    
    # API Configuration
    api_endpoint = db.Column(db.String(500))
    api_method = db.Column(db.String(10), default='GET')
    api_headers = db.Column(db.JSON)
    api_params = db.Column(db.JSON)
    api_body = db.Column(db.Text)
    api_timeout = db.Column(db.Integer, default=30)
    
    # Authentication
    auth_type = db.Column(db.Enum(AuthType), default=AuthType.NONE)
    auth_username = db.Column(db.String(200))
    auth_password_encrypted = db.Column(db.Text)
    auth_token_encrypted = db.Column(db.Text)
    auth_api_key_encrypted = db.Column(db.Text)
    auth_oauth_config = db.Column(db.JSON)
    
    # File/Upload Configuration
    file_path = db.Column(db.String(500))
    file_url = db.Column(db.String(1000))  # External file URL
    file_size = db.Column(db.BigInteger)
    file_mime_type = db.Column(db.String(100))
    file_hash = db.Column(db.String(64))  # SHA-256 hash
    
    # Database Configuration
    db_connection_string_encrypted = db.Column(db.Text)
    db_type = db.Column(db.String(50))  # postgresql, mysql, mssql, etc.
    db_host = db.Column(db.String(200))
    db_port = db.Column(db.Integer)
    db_name = db.Column(db.String(200))
    db_username = db.Column(db.String(200))
    db_password_encrypted = db.Column(db.Text)
    db_schema = db.Column(db.String(100))
    db_table = db.Column(db.String(200))
    
    # Data Processing
    data_path = db.Column(db.String(500))  # JSONPath or XPath
    query_string = db.Column(db.Text)
    transform_script = db.Column(db.Text)
    
    # Schema Information (Inferred)
    schema = db.Column(db.JSON)  # {columns: [{name, type, nullable, sample_values}]}
    schema_inferred_at = db.Column(db.DateTime)
    column_count = db.Column(db.Integer)
    sample_data = db.Column(db.JSON)  # First 5 rows for preview
    
    # Validation Rules
    validation_rules = db.Column(db.JSON)  # [{column, rule_type, params}]
    validation_enabled = db.Column(db.Boolean, default=False)
    last_validation_status = db.Column(db.String(20))  # passed, failed, skipped
    last_validation_errors = db.Column(db.JSON)
    
    # Refresh Settings
    refresh_frequency = db.Column(db.Integer)
    auto_refresh = db.Column(db.Boolean, default=False)
    last_refresh = db.Column(db.DateTime)
    last_refresh_status = db.Column(db.String(20))
    last_refresh_error = db.Column(db.Text)
    next_refresh = db.Column(db.DateTime)
    refresh_in_progress = db.Column(db.Boolean, default=False)
    
    # Background Job
    celery_task_id = db.Column(db.String(255))  # Current background task
    
    # Cache Settings
    cache_enabled = db.Column(db.Boolean, default=True)
    cache_ttl = db.Column(db.Integer, default=300)
    cached_data = db.Column(db.JSON)
    cached_at = db.Column(db.DateTime)
    cache_key = db.Column(db.String(255), index=True)
    
    # Data Statistics
    record_count = db.Column(db.Integer, default=0)
    last_record_count = db.Column(db.Integer)
    data_size_bytes = db.Column(db.BigInteger)
    first_data_received = db.Column(db.DateTime)
    data_updated_at = db.Column(db.DateTime)
    
    # Health & Monitoring
    health_status = db.Column(db.String(20), default='unknown', index=True)
    health_checked_at = db.Column(db.DateTime)
    uptime_percentage = db.Column(db.Float, default=100.0)
    avg_response_time = db.Column(db.Float)
    min_response_time = db.Column(db.Float)
    max_response_time = db.Column(db.Float)
    error_count = db.Column(db.Integer, default=0)
    success_count = db.Column(db.Integer, default=0)
    consecutive_failures = db.Column(db.Integer, default=0)
    last_error_message = db.Column(db.Text)
    
    # Alert Configuration
    alert_on_failure = db.Column(db.Boolean, default=True)
    alert_threshold = db.Column(db.Integer, default=3)  # Alert after N failures
    alert_sent_at = db.Column(db.DateTime)
    
    # Status & Metadata
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_public = db.Column(db.Boolean, default=False)
    requires_approval = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)  # Soft delete
    
    # Foreign Keys
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    widgets = db.relationship('Widget', backref='data_source', lazy='dynamic', cascade='all, delete-orphan')
    refresh_logs = db.relationship('DataRefreshLog', backref='data_source', lazy='dynamic', cascade='all, delete-orphan')
    validation_logs = db.relationship('DataValidationLog', backref='data_source', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<DataSource {self.name}>'
    
    # Encryption helpers
    @staticmethod
    def _get_cipher():
        """Get Fernet cipher for encryption"""
        key = os.environ.get('ENCRYPTION_KEY')
        if not key:
            key = Fernet.generate_key()
            # In production, this should be stored securely
        if isinstance(key, str):
            key = key.encode()
        return Fernet(key)
    
    def _encrypt(self, value):
        """Encrypt a value"""
        if not value:
            return None
        cipher = self._get_cipher()
        return cipher.encrypt(value.encode()).decode()
    
    def _decrypt(self, encrypted_value):
        """Decrypt a value"""
        if not encrypted_value:
            return None
        try:
            cipher = self._get_cipher()
            return cipher.decrypt(encrypted_value.encode()).decode()
        except Exception:
            return None
    
    # Credential properties
    @property
    def auth_password(self):
        return self._decrypt(self.auth_password_encrypted)
    
    @auth_password.setter
    def auth_password(self, value):
        self.auth_password_encrypted = self._encrypt(value)
    
    @property
    def auth_token(self):
        return self._decrypt(self.auth_token_encrypted)
    
    @auth_token.setter
    def auth_token(self, value):
        self.auth_token_encrypted = self._encrypt(value)
    
    @property
    def auth_api_key(self):
        return self._decrypt(self.auth_api_key_encrypted)
    
    @auth_api_key.setter
    def auth_api_key(self, value):
        self.auth_api_key_encrypted = self._encrypt(value)
    
    @property
    def db_password(self):
        return self._decrypt(self.db_password_encrypted)
    
    @db_password.setter
    def db_password(self, value):
        self.db_password_encrypted = self._encrypt(value)
    
    @property
    def db_connection_string(self):
        return self._decrypt(self.db_connection_string_encrypted)
    
    @db_connection_string.setter
    def db_connection_string(self, value):
        self.db_connection_string_encrypted = self._encrypt(value)
    
    # Computed properties
    @property
    def widget_count(self):
        """Get number of active widgets using this data source"""
        return self.widgets.filter_by(is_active=True).count()
    
    @property
    def is_cache_valid(self):
        """Check if cached data is still valid"""
        if not self.cache_enabled or not self.cached_at:
            return False
        expiry = self.cached_at + timedelta(seconds=self.cache_ttl)
        return datetime.utcnow() < expiry
    
    @property
    def needs_refresh(self):
        """Check if data source needs refresh"""
        if not self.auto_refresh or not self.refresh_frequency or self.refresh_in_progress:
            return False
        if not self.last_refresh:
            return True
        next_refresh = self.last_refresh + timedelta(seconds=self.refresh_frequency)
        return datetime.utcnow() >= next_refresh
    
    @property
    def success_rate(self):
        """Calculate success rate percentage"""
        total = self.success_count + self.error_count
        if total == 0:
            return 100.0
        return round((self.success_count / total) * 100, 2)
    
    @property
    def has_schema(self):
        """Check if schema has been inferred"""
        return bool(self.schema and self.schema_inferred_at)
    
    @property
    def is_healthy(self):
        """Quick health check"""
        return self.health_status == 'healthy' and self.consecutive_failures == 0
    
        # Format detection
    @staticmethod
    def detect_format_from_file(file_path):
        """Auto-detect data format from file using mimetypes and file signatures"""
        try:
            import mimetypes
            
            # Get MIME type using standard library
            mime_type, _ = mimetypes.guess_type(file_path)
            
            # Map MIME types to formats
            mime_mapping = {
                'application/json': DataFormat.JSON,
                'text/csv': DataFormat.CSV,
                'application/vnd.ms-excel': DataFormat.EXCEL,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': DataFormat.EXCEL,
                'application/xml': DataFormat.XML,
                'text/xml': DataFormat.XML,
                'application/pdf': DataFormat.PDF,
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': DataFormat.DOCX,
                'text/plain': DataFormat.TXT,
                'text/html': DataFormat.HTML,
            }
            
            detected = mime_mapping.get(mime_type) if mime_type else None
            
            # Fallback to extension-based detection
            if not detected:
                ext = os.path.splitext(file_path)[1].lower()
                ext_mapping = {
                    '.json': DataFormat.JSON,
                    '.csv': DataFormat.CSV,
                    '.xlsx': DataFormat.EXCEL,
                    '.xls': DataFormat.EXCEL,
                    '.xml': DataFormat.XML,
                    '.parquet': DataFormat.PARQUET,
                    '.pdf': DataFormat.PDF,
                    '.docx': DataFormat.DOCX,
                    '.txt': DataFormat.TXT,
                    '.html': DataFormat.HTML,
                    '.htm': DataFormat.HTML,
                }
                detected = ext_mapping.get(ext)
            
            # Enhanced detection using file signatures (magic bytes)
            if not detected and os.path.exists(file_path):
                detected = DataSource._detect_by_signature(file_path)
            
            return detected, mime_type
        except Exception:
            return None, None
    
    @staticmethod
    def _detect_by_signature(file_path):
        """Detect format by reading file signature (magic bytes)"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(8)
            
            # Common file signatures
            if header.startswith(b'PK\x03\x04'):
                # ZIP-based formats (XLSX, DOCX, Parquet)
                if file_path.lower().endswith(('.xlsx', '.xls')):
                    return DataFormat.EXCEL
                elif file_path.lower().endswith('.docx'):
                    return DataFormat.DOCX
                elif file_path.lower().endswith('.parquet'):
                    return DataFormat.PARQUET
            elif header.startswith(b'%PDF'):
                return DataFormat.PDF
            elif header.startswith(b'<?xml') or header.startswith(b'<'):
                return DataFormat.XML
            elif header.startswith(b'{') or header.startswith(b'['):
                return DataFormat.JSON
            elif b',' in header or b'\t' in header:
                # Likely CSV/TSV
                return DataFormat.CSV
            
            return None
        except Exception:
            return None
    
    # Methods
    def schedule_refresh(self):
        """Schedule next refresh"""
        if self.auto_refresh and self.refresh_frequency:
            self.next_refresh = datetime.utcnow() + timedelta(seconds=self.refresh_frequency)
    
    def record_success(self, response_time=None, record_count=None):
        """Record successful data fetch"""
        self.success_count += 1
        self.consecutive_failures = 0
        self.last_refresh = datetime.utcnow()
        self.last_refresh_status = 'success'
        self.last_refresh_error = None
        self.last_error_message = None
        self.health_status = 'healthy'
        self.health_checked_at = datetime.utcnow()
        self.refresh_in_progress = False
        
        if response_time:
            # Update response time statistics
            if self.avg_response_time:
                self.avg_response_time = (self.avg_response_time * 0.7) + (response_time * 0.3)
            else:
                self.avg_response_time = response_time
            
            if not self.min_response_time or response_time < self.min_response_time:
                self.min_response_time = response_time
            if not self.max_response_time or response_time > self.max_response_time:
                self.max_response_time = response_time
        
        if record_count is not None:
            self.last_record_count = self.record_count
            self.record_count = record_count
            self.data_updated_at = datetime.utcnow()
        
        if not self.first_data_received:
            self.first_data_received = datetime.utcnow()
        
        self.schedule_refresh()
    
    def record_error(self, error_message):
        """Record failed data fetch"""
        self.error_count += 1
        self.consecutive_failures += 1
        self.last_refresh = datetime.utcnow()
        self.last_refresh_status = 'error'
        self.last_refresh_error = error_message[:1000]  # Truncate
        self.last_error_message = error_message[:1000]
        self.refresh_in_progress = False
        
        # Update health status based on consecutive failures
        if self.consecutive_failures >= 5:
            self.health_status = 'down'
        elif self.consecutive_failures >= 3:
            self.health_status = 'degraded'
        elif self.success_rate < 80:
            self.health_status = 'degraded'
        
        self.health_checked_at = datetime.utcnow()
        self.schedule_refresh()
        
        # Check if alert should be sent
        if (self.alert_on_failure and 
            self.consecutive_failures >= self.alert_threshold and
            (not self.alert_sent_at or 
             (datetime.utcnow() - self.alert_sent_at) > timedelta(hours=1))):
            self.alert_sent_at = datetime.utcnow()
            # Trigger alert (implement in service)
    
    def cache_data(self, data):
        """Cache fetched data"""
        if self.cache_enabled:
            self.cached_data = data
            self.cached_at = datetime.utcnow()
    
    def clear_cache(self):
        """Clear cached data"""
        self.cached_data = None
        self.cached_at = None
    
    def get_data(self):
        """Get data from cache if valid"""
        if self.is_cache_valid:
            return self.cached_data
        return None
    
    def infer_schema(self, data_sample):
        """Infer schema from data sample"""
        if not data_sample:
            return
        
        try:
            import pandas as pd
            
            # Convert to DataFrame
            if isinstance(data_sample, list):
                df = pd.DataFrame(data_sample[:100])  # Use first 100 rows
            elif isinstance(data_sample, dict):
                df = pd.DataFrame([data_sample])
            else:
                return
            
            # Infer schema
            columns = []
            for col in df.columns:
                col_info = {
                    'name': col,
                    'type': str(df[col].dtype),
                    'nullable': bool(df[col].isnull().any()),
                    'unique_count': int(df[col].nunique()),
                    'sample_values': df[col].dropna().head(5).tolist()
                }
                columns.append(col_info)
            
            self.schema = {'columns': columns}
            self.schema_inferred_at = datetime.utcnow()
            self.column_count = len(columns)
            self.sample_data = data_sample[:5] if isinstance(data_sample, list) else [data_sample]
            
        except Exception as e:
            # Log error but don't fail
            pass
    
    def validate_data(self, data):
        """Validate data against rules"""
        if not self.validation_enabled or not self.validation_rules:
            return True, []
        
        errors = []
        # Implement validation logic based on rules
        # This is a placeholder for the full implementation
        
        self.last_validation_status = 'passed' if not errors else 'failed'
        self.last_validation_errors = errors if errors else None
        
        return len(errors) == 0, errors
    
    # Serialization
    def to_dict(self, include_sensitive=False, include_schema=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'reference': self.reference,
            'description': self.description,
            'tags': self.tags,
            'source_type': self.source_type.value if self.source_type else None,
            'data_format': self.data_format.value if self.data_format else None,
            'detected_format': self.detected_format.value if self.detected_format else None,
            'mime_type': self.mime_type,
            'auth_type': self.auth_type.value if self.auth_type else None,
            'refresh_frequency': self.refresh_frequency,
            'auto_refresh': self.auto_refresh,
            'cache_enabled': self.cache_enabled,
            'is_active': self.is_active,
            'health_status': self.health_status,
            'uptime_percentage': self.uptime_percentage,
            'success_rate': self.success_rate,
            'record_count': self.record_count,
            'widget_count': self.widget_count,
            'has_schema': self.has_schema,
            'column_count': self.column_count,
            'last_refresh': self.last_refresh.isoformat() if self.last_refresh else None,
            'next_refresh': self.next_refresh.isoformat() if self.next_refresh else None,
            'created_at': self.created_at.isoformat(),
        }
        
        if include_schema and self.schema:
            data['schema'] = self.schema
            data['sample_data'] = self.sample_data
        
        if include_sensitive:
            data.update({
                'api_endpoint': self.api_endpoint,
                'file_path': self.file_path,
                'file_url': self.file_url,
                'has_credentials': bool(
                    self.auth_password_encrypted or 
                    self.auth_token_encrypted or 
                    self.auth_api_key_encrypted
                ),
            })
        
        return data


# Event listeners
@event.listens_for(DataSource, 'before_update')
def update_timestamp(mapper, connection, target):
    """Update timestamp on modification"""
    target.updated_at = datetime.utcnow()