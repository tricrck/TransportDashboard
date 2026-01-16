"""
Forms Package
WTForms for all CRUD operations with comprehensive validation
"""

from .auth import (
    LoginForm,
    TwoFAForm,
    ProfileForm,
    TwoFASetupForm,
    PasswordResetRequestForm,
    PasswordResetForm,
    ChangePasswordForm,
    RegisterForm
)

from .admin import (
    OrganizationForm,
    UserForm,
    UserEditForm,
    RoleForm,
    PermissionForm
)

from .data_source import (
    DataSourceForm,
    APIDataSourceForm,
    UploadDataSourceForm,
    QueryDataSourceForm,
    DatabaseDataSourceForm
)

from .widget import (
    WidgetForm,
    WidgetConfigForm,
    StatCardWidgetForm,
    ChartWidgetForm,
    TableWidgetForm
)

from .dashboard import (
    DashboardForm,
    DashboardLayoutForm,
    DashboardShareForm,
    DashboardWidgetAddForm
)

__all__ = [
    # Auth forms
    'LoginForm',
    'TwoFAForm',
    'TwoFASetupForm',
    'PasswordResetRequestForm',
    'PasswordResetForm',
    'ChangePasswordForm',
    'RegisterForm',
    
    # Admin forms
    'OrganizationForm',
    'UserForm',
    'UserEditForm',
    'RoleForm',
    'PermissionForm',
    
    # Data source forms
    'DataSourceForm',
    'APIDataSourceForm',
    'UploadDataSourceForm',
    'QueryDataSourceForm',
    'DatabaseDataSourceForm',
    
    # Widget forms
    'WidgetForm',
    'WidgetConfigForm',
    'StatCardWidgetForm',
    'ChartWidgetForm',
    'TableWidgetForm',
    
    # Dashboard forms
    'DashboardForm',
    'DashboardLayoutForm',
    'DashboardShareForm',
]