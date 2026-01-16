"""
Admin Forms
Organization, User, Role, Permission management
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, TextAreaField, SelectField, SelectMultipleField,
    BooleanField, IntegerField, PasswordField, SubmitField, HiddenField
)
from wtforms.validators import (
    DataRequired, Email, Length, Optional, NumberRange,
    ValidationError, URL, Regexp, EqualTo
)
from models import Organization, User, Role


class OrganizationForm(FlaskForm):
    """Organization create/edit form"""
    name = StringField(
        'Organization Name',
        validators=[
            DataRequired(message='Organization name is required'),
            Length(min=3, max=200, message='Name must be between 3 and 200 characters')
        ],
        render_kw={'placeholder': 'e.g., Kenya Ports Authority'}
    )
    
    code = StringField(
        'Organization Code',
        validators=[
            DataRequired(message='Organization code is required'),
            Length(min=2, max=20, message='Code must be between 2 and 20 characters'),
            Regexp(r'^[A-Z0-9_-]+$', message='Code must contain only uppercase letters, numbers, underscores, and hyphens')
        ],
        render_kw={'placeholder': 'e.g., KPA', 'style': 'text-transform: uppercase;'}
    )
    
    org_type = SelectField(
        'Organization Type',
        choices=[
            ('Port Authority', 'Port Authority'),
            ('Railway Corporation', 'Railway Corporation'),
            ('Aviation Authority', 'Aviation Authority'),
            ('Civil Aviation', 'Civil Aviation'),
            ('Pipeline Company', 'Pipeline Company'),
            ('Transport & Safety', 'Transport & Safety Authority'),
            ('Highway Authority', 'Highway Authority'),
            ('Other', 'Other')
        ],
        validators=[DataRequired(message='Organization type is required')]
    )
    
    description = TextAreaField(
        'Description',
        validators=[Length(max=1000)],
        render_kw={'rows': 4, 'placeholder': 'Brief description of the organization'}
    )
    
    mission = TextAreaField(
        'Mission Statement',
        validators=[Length(max=1000)],
        render_kw={'rows': 3}
    )
    
    vision = TextAreaField(
        'Vision Statement',
        validators=[Length(max=1000)],
        render_kw={'rows': 3}
    )
    
    # Contact Information
    email = StringField(
        'Official Email',
        validators=[Optional(), Email(), Length(max=120)],
        render_kw={'placeholder': 'contact@organization.go.ke'}
    )
    
    phone = StringField(
        'Phone Number',
        validators=[Optional(), Length(max=20)],
        render_kw={'placeholder': '+254 700 000000'}
    )
    
    website = StringField(
        'Website',
        validators=[Optional(), URL(), Length(max=200)],
        render_kw={'placeholder': 'https://www.organization.go.ke'}
    )
    
    # Address
    address_line1 = StringField(
        'Address Line 1',
        validators=[Optional(), Length(max=200)]
    )
    
    address_line2 = StringField(
        'Address Line 2',
        validators=[Optional(), Length(max=200)]
    )
    
    city = StringField(
        'City',
        validators=[Optional(), Length(max=100)]
    )
    
    postal_code = StringField(
        'Postal Code',
        validators=[Optional(), Length(max=20)]
    )
    
    # Branding
    logo = FileField(
        'Logo',
        validators=[FileAllowed(['jpg', 'jpeg', 'png', 'svg'], 'Images only!')]
    )
    
    primary_color = StringField(
        'Primary Brand Color',
        validators=[
            Optional(),
            Regexp(r'^#[0-9A-Fa-f]{6}$', message='Must be a valid hex color (e.g., #1a237e)')
        ],
        render_kw={'type': 'color', 'value': '#1a237e'}
    )
    
    secondary_color = StringField(
        'Secondary Brand Color',
        validators=[
            Optional(),
            Regexp(r'^#[0-9A-Fa-f]{6}$', message='Must be a valid hex color')
        ],
        render_kw={'type': 'color', 'value': '#0d47a1'}
    )
    
    # Subscription & Limits
    subscription_tier = SelectField(
        'Subscription Tier',
        choices=[
            ('free', 'Free'),
            ('standard', 'Standard'),
            ('premium', 'Premium'),
            ('enterprise', 'Enterprise')
        ],
        default='standard'
    )
    
    max_users = IntegerField(
        'Maximum Users',
        validators=[NumberRange(min=1, max=10000)],
        default=50
    )
    
    max_dashboards = IntegerField(
        'Maximum Dashboards',
        validators=[NumberRange(min=1, max=1000)],
        default=20
    )
    
    max_data_sources = IntegerField(
        'Maximum Data Sources',
        validators=[NumberRange(min=1, max=1000)],
        default=100
    )
    
    is_active = BooleanField('Active', default=True)
    
    submit = SubmitField('Save Organization')
    
    def __init__(self, original_code=None, *args, **kwargs):
        super(OrganizationForm, self).__init__(*args, **kwargs)
        self.original_code = original_code
    
    def validate_code(self, field):
        """Check if code is unique"""
        if field.data != self.original_code:
            org = Organization.query.filter_by(code=field.data.upper()).first()
            if org:
                raise ValidationError('This organization code is already in use.')


class UserForm(FlaskForm):
    """User create form"""
    email = StringField(
        'Email Address',
        validators=[
            DataRequired(message='Email is required'),
            Email(message='Invalid email address'),
            Length(max=120)
        ],
        render_kw={'placeholder': 'user@organization.go.ke'}
    )
    
    first_name = StringField(
        'First Name',
        validators=[
            DataRequired(message='First name is required'),
            Length(max=100)
        ]
    )
    
    last_name = StringField(
        'Last Name',
        validators=[
            DataRequired(message='Last name is required'),
            Length(max=100)
        ]
    )
    
    phone = StringField(
        'Phone Number',
        validators=[Optional(), Length(max=20)],
        render_kw={'placeholder': '+254 700 000000'}
    )
    
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message='Password is required'),
            Length(min=8, max=128),
            Regexp(
                r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]',
                message='Password must contain uppercase, lowercase, number, and special character'
            )
        ]
    )
    
    password_confirm = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message='Please confirm password'),
            EqualTo('password', message='Passwords must match')
        ]
    )
    
    organization = SelectField(
        'Organization',
        coerce=int,
        validators=[DataRequired(message='Organization is required')]
    )
    
    role = SelectField(
        'Role',
        coerce=int,
        validators=[DataRequired(message='Role is required')]
    )
    
    job_title = StringField(
        'Job Title',
        validators=[Optional(), Length(max=100)]
    )
    
    department = StringField(
        'Department',
        validators=[Optional(), Length(max=100)]
    )
    
    employee_id = StringField(
        'Employee ID',
        validators=[Optional(), Length(max=50)]
    )
    
    is_active = BooleanField('Active', default=True)
    
    email_notifications = BooleanField('Enable Email Notifications', default=True)
    
    submit = SubmitField('Create User')
    
    def validate_email(self, field):
        """Check if email is unique"""
        user = User.query.filter_by(email=field.data.lower()).first()
        if user:
            raise ValidationError('This email address is already registered.')


class UserEditForm(FlaskForm):
    """User edit form (without password)"""
    email = StringField(
        'Email Address',
        validators=[
            DataRequired(message='Email is required'),
            Email(message='Invalid email address'),
            Length(max=120)
        ]
    )
    
    first_name = StringField(
        'First Name',
        validators=[
            DataRequired(message='First name is required'),
            Length(max=100)
        ]
    )
    
    last_name = StringField(
        'Last Name',
        validators=[
            DataRequired(message='Last name is required'),
            Length(max=100)
        ]
    )
    
    phone = StringField(
        'Phone Number',
        validators=[Optional(), Length(max=20)]
    )
    
    organization = SelectField(
        'Organization',
        coerce=int,
        validators=[DataRequired(message='Organization is required')]
    )
    
    role = SelectField(
        'Role',
        coerce=int,
        validators=[DataRequired(message='Role is required')]
    )
    
    job_title = StringField('Job Title', validators=[Optional(), Length(max=100)])
    department = StringField('Department', validators=[Optional(), Length(max=100)])
    employee_id = StringField('Employee ID', validators=[Optional(), Length(max=50)])
    
    is_active = BooleanField('Active')
    two_fa_enabled = BooleanField('2FA Enabled')
    email_notifications = BooleanField('Email Notifications')
    sms_notifications = BooleanField('SMS Notifications')
    
    submit = SubmitField('Update User')
    
    def __init__(self, original_email=None, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.original_email = original_email
    
    def validate_email(self, field):
        """Check if email is unique"""
        if field.data.lower() != self.original_email:
            user = User.query.filter_by(email=field.data.lower()).first()
            if user:
                raise ValidationError('This email address is already in use.')


class RoleForm(FlaskForm):
    """Role create/edit form"""
    name = StringField(
        'Role Name',
        validators=[
            DataRequired(message='Role name is required'),
            Length(min=3, max=100)
        ],
        render_kw={'placeholder': 'e.g., Data Analyst'}
    )
    
    code = StringField(
        'Role Code',
        validators=[
            DataRequired(message='Role code is required'),
            Length(min=2, max=50),
            Regexp(r'^[a-z0-9_]+$', message='Code must contain only lowercase letters, numbers, and underscores')
        ],
        render_kw={'placeholder': 'e.g., data_analyst'}
    )
    
    description = TextAreaField(
        'Description',
        validators=[Length(max=500)],
        render_kw={'rows': 3}
    )
    
    level = IntegerField(
        'Access Level',
        validators=[NumberRange(min=0, max=100)],
        default=50,
        description='Higher number = more privileges (0-100)'
    )
    
    color = StringField(
        'Badge Color',
        validators=[
            Optional(),
            Regexp(r'^#[0-9A-Fa-f]{6}$', message='Must be a valid hex color')
        ],
        render_kw={'type': 'color', 'value': '#2196f3'}
    )
    
    icon = StringField(
        'Icon (Font Awesome)',
        validators=[Optional(), Length(max=50)],
        render_kw={'placeholder': 'e.g., fa-user'}
    )
    
    permissions = SelectMultipleField(
        'Permissions',
        coerce=int,
        description='Hold Ctrl/Cmd to select multiple'
    )
    
    is_default = BooleanField('Default Role for New Users')
    is_active = BooleanField('Active', default=True)
    
    submit = SubmitField('Save Role')
    
    def __init__(self, original_code=None, *args, **kwargs):
        super(RoleForm, self).__init__(*args, **kwargs)
        self.original_code = original_code
    
    def validate_code(self, field):
        """Check if code is unique"""
        if field.data != self.original_code:
            role = Role.query.filter_by(code=field.data).first()
            if role:
                raise ValidationError('This role code is already in use.')


class PermissionForm(FlaskForm):
    """Permission create/edit form"""
    name = StringField(
        'Permission Name',
        validators=[
            DataRequired(message='Permission name is required'),
            Length(min=3, max=100)
        ],
        render_kw={'placeholder': 'e.g., Create Dashboard'}
    )
    
    code = StringField(
        'Permission Code',
        validators=[
            DataRequired(message='Permission code is required'),
            Length(min=2, max=50),
            Regexp(r'^[a-z0-9_]+$', message='Code must contain only lowercase letters, numbers, and underscores')
        ],
        render_kw={'placeholder': 'e.g., create_dashboard'}
    )
    
    description = TextAreaField(
        'Description',
        validators=[Length(max=500)],
        render_kw={'rows': 3}
    )
    
    category = SelectField(
        'Category',
        choices=[
            ('organization', 'Organization'),
            ('user', 'User Management'),
            ('role', 'Role & Permissions'),
            ('data_source', 'Data Sources'),
            ('widget', 'Widgets'),
            ('dashboard', 'Dashboards'),
            ('report', 'Reports'),
            ('system', 'System Administration')
        ],
        validators=[DataRequired()]
    )
    
    module = StringField(
        'Module',
        validators=[Optional(), Length(max=50)],
        description='Optional: Further grouping within category'
    )
    
    display_order = IntegerField(
        'Display Order',
        validators=[Optional(), NumberRange(min=0)],
        default=0
    )
    
    is_active = BooleanField('Active', default=True)
    
    submit = SubmitField('Save Permission')