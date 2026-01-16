"""
Authentication Forms
Login, 2FA, password management
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, HiddenField, SelectField
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, ValidationError, Regexp
)
from models import User

class RegisterForm(FlaskForm):
    """User registration form"""
    
    # Personal Information
    first_name = StringField(
        'First Name',
        validators=[
            DataRequired(message='First name is required'),
            Length(min=2, max=100, message='First name must be between 2 and 100 characters'),
            Regexp(r'^[a-zA-Z\s\'-]+$', message='First name can only contain letters, spaces, hyphens, and apostrophes')
        ],
        render_kw={'placeholder': 'John'}
    )
    
    last_name = StringField(
        'Last Name',
        validators=[
            DataRequired(message='Last name is required'),
            Length(min=2, max=100, message='Last name must be between 2 and 100 characters'),
            Regexp(r'^[a-zA-Z\s\'-]+$', message='Last name can only contain letters, spaces, hyphens, and apostrophes')
        ],
        render_kw={'placeholder': 'Doe'}
    )
    
    # Contact Information
    email = StringField(
        'Email Address',
        validators=[
            DataRequired(message='Email address is required'),
            Email(message='Please enter a valid email address'),
            Length(max=120, message='Email address is too long')
        ],
        render_kw={'placeholder': 'john.doe@transport.go.ke'}
    )
    
    phone = StringField(
        'Phone Number',
        validators=[
            Length(max=20, message='Phone number is too long'),
            Regexp(r'^[+\d\s()-]*$', message='Please enter a valid phone number')
        ],
        render_kw={'placeholder': '+254 700 000000'}
    )
    
    # Organization Information
    organization_id = SelectField(
        'Organization',
        validators=[DataRequired(message='Please select your organization')],
        coerce=int,
        choices=[]  # Will be populated in the view
    )
    
    job_title = StringField(
        'Job Title',
        validators=[Length(max=100, message='Job title is too long')],
        render_kw={'placeholder': 'Data Analyst'}
    )
    
    department = StringField(
        'Department',
        validators=[Length(max=100, message='Department name is too long')],
        render_kw={'placeholder': 'Analytics Department'}
    )
    
    # Security
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message='Password is required'),
            Length(min=8, max=128, message='Password must be between 8 and 128 characters'),
            Regexp(
                r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]',
                message='Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character (@$!%*?&)'
            )
        ],
        render_kw={'placeholder': '••••••••'}
    )
    
    password_confirm = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message='Please confirm your password'),
            EqualTo('password', message='Passwords must match')
        ],
        render_kw={'placeholder': '••••••••'}
    )
    
    # Terms and Conditions
    accept_terms = BooleanField(
        'I agree to the Terms of Service and Privacy Policy',
        validators=[DataRequired(message='You must accept the terms and conditions to register')]
    )
    
    submit = SubmitField('Create Account')
    
    def validate_email(self, field):
        """Check if email already exists"""
        email = field.data.lower().strip()
        
        # Check if email already exists
        user = User.query.filter_by(email=email).first()
        if user:
            raise ValidationError('This email address is already registered. Please use a different email or sign in.')
        
        # Optional: Validate email domain for government organizations
        # Uncomment and customize based on your requirements
        """
        allowed_domains = ['transport.go.ke', 'ntsa.go.ke', 'kenha.co.ke']
        email_domain = email.split('@')[1] if '@' in email else ''
        
        if email_domain not in allowed_domains:
            raise ValidationError(f'Please use an official government email address from: {", ".join(allowed_domains)}')
        """
    
    def validate_phone(self, field):
        """Validate phone number format"""
        if field.data:
            phone = field.data.strip()
            # Remove all non-digit characters for length check
            digits_only = ''.join(filter(str.isdigit, phone))
            
            if len(digits_only) < 10:
                raise ValidationError('Phone number must contain at least 10 digits')
    
    def validate_password_confirm(self, field):
        """Additional password confirmation validation"""
        if self.password.data and field.data:
            if self.password.data != field.data:
                raise ValidationError('Passwords do not match. Please try again.')
                
class LoginForm(FlaskForm):
    """User login form"""
    email = StringField(
        'Email Address',
        validators=[
            DataRequired(message='Email is required'),
            Email(message='Invalid email address'),
            Length(max=120)
        ],
        render_kw={'placeholder': 'your.email@transport.go.ke', 'autofocus': True}
    )
    
    password = PasswordField(
        'Password',
        validators=[DataRequired(message='Password is required')],
        render_kw={'placeholder': 'Enter your password'}
    )
    
    remember = BooleanField('Remember Me')
    
    submit = SubmitField('Sign In')


class TwoFAForm(FlaskForm):
    """Two-factor authentication verification form"""
    token = StringField(
        '2FA Token',
        validators=[
            DataRequired(message='Token is required'),
            Length(min=6, max=6, message='Token must be 6 digits'),
            Regexp(r'^\d{6}$', message='Token must contain only digits')
        ],
        render_kw={'placeholder': '000000', 'maxlength': '6', 'autofocus': True}
    )
    
    submit = SubmitField('Verify & Continue')


class TwoFASetupForm(FlaskForm):
    """Form for setting up 2FA"""
    secret = HiddenField('Secret')
    
    token = StringField(
        'Verification Code',
        validators=[
            DataRequired(message='Verification code is required'),
            Length(min=6, max=6, message='Code must be 6 digits'),
            Regexp(r'^\d{6}$', message='Code must contain only digits')
        ],
        render_kw={'placeholder': '000000', 'maxlength': '6'}
    )
    
    submit = SubmitField('Enable 2FA')


class PasswordResetRequestForm(FlaskForm):
    """Request password reset form"""
    email = StringField(
        'Email Address',
        validators=[
            DataRequired(message='Email is required'),
            Email(message='Invalid email address')
        ],
        render_kw={'placeholder': 'your.email@transport.go.ke'}
    )
    
    submit = SubmitField('Request Password Reset')
    
    def validate_email(self, field):
        """Check if email exists"""
        user = User.query.filter_by(email=field.data.lower()).first()
        if not user:
            raise ValidationError('No account found with this email address.')
        if not user.is_active:
            raise ValidationError('This account has been deactivated.')


class PasswordResetForm(FlaskForm):
    """Reset password form"""
    password = PasswordField(
        'New Password',
        validators=[
            DataRequired(message='Password is required'),
            Length(min=8, max=128, message='Password must be between 8 and 128 characters'),
            Regexp(
                r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]',
                message='Password must contain uppercase, lowercase, number, and special character'
            )
        ],
        render_kw={'placeholder': 'Enter new password'}
    )
    
    password_confirm = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message='Please confirm your password'),
            EqualTo('password', message='Passwords must match')
        ],
        render_kw={'placeholder': 'Confirm new password'}
    )
    
    submit = SubmitField('Reset Password')


class ChangePasswordForm(FlaskForm):
    """Change password form for logged-in users"""
    current_password = PasswordField(
        'Current Password',
        validators=[DataRequired(message='Current password is required')],
        render_kw={'placeholder': 'Enter current password'}
    )
    
    new_password = PasswordField(
        'New Password',
        validators=[
            DataRequired(message='New password is required'),
            Length(min=8, max=128, message='Password must be between 8 and 128 characters'),
            Regexp(
                r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]',
                message='Password must contain uppercase, lowercase, number, and special character'
            )
        ],
        render_kw={'placeholder': 'Enter new password'}
    )
    
    new_password_confirm = PasswordField(
        'Confirm New Password',
        validators=[
            DataRequired(message='Please confirm your new password'),
            EqualTo('new_password', message='Passwords must match')
        ],
        render_kw={'placeholder': 'Confirm new password'}
    )
    
    submit = SubmitField('Change Password')
    
    def validate_new_password(self, field):
        """Ensure new password is different from current"""
        if field.data == self.current_password.data:
            raise ValidationError('New password must be different from current password.')


class ProfileForm(FlaskForm):
    """User profile edit form"""
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
        validators=[
            Length(max=20),
            Regexp(r'^[+\d\s()-]*$', message='Invalid phone number format')
        ],
        render_kw={'placeholder': '+254 700 000000'}
    )
    
    job_title = StringField(
        'Job Title',
        validators=[Length(max=100)],
        render_kw={'placeholder': 'e.g., Data Analyst'}
    )
    
    department = StringField(
        'Department',
        validators=[Length(max=100)],
        render_kw={'placeholder': 'e.g., Analytics'}
    )
    
    language = StringField(
        'Preferred Language',
        validators=[Length(max=10)]
    )
    
    timezone = StringField(
        'Timezone',
        validators=[Length(max=50)]
    )
    
    email_notifications = BooleanField('Enable Email Notifications')
    sms_notifications = BooleanField('Enable SMS Notifications')
    
    submit = SubmitField('Update Profile')