# blueprints/auth.py
"""
Authentication Blueprint
User login, logout, password management, 2FA
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, current_app
from flask_login import login_user, logout_user, current_user, login_required
from forms import LoginForm, TwoFAForm, TwoFASetupForm, PasswordResetRequestForm, PasswordResetForm, ChangePasswordForm, ProfileForm, RegisterForm
from services import AuthService
from models import User, db, AuditLog, AuditAction, Organization, Role, Dashboard
import pyotp
import qrcode
import io
import base64

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboards.view'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        # Get client info
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        # Authenticate user
        result = AuthService.authenticate(
            email=form.email.data,
            password=form.password.data,
            remember=form.remember.data,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if result['success']:
            if result['requires_2fa']:
                flash('Please enter your 2FA code to continue.', 'info')
                return redirect(url_for('auth.verify_2fa'))
            
            # Login successful
            user = User.query.get(result['user']['id'])
            login_user(user, remember=form.remember.data)
            flash('Login successful!', 'success')
            user_dashboard = Dashboard.query.filter_by(
                organization_id=current_user.organization_id,
                is_active=True
            ).first()

            if user_dashboard:
                return redirect(url_for('dashboards.view', id=user_dashboard.id))
            else:
                return redirect(url_for('main.index'))
        else:
            flash(result['message'], 'danger')
    
    return render_template('auth/login.html', form=form, title='Sign In')

@auth_bp.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    """Verify 2FA token"""
    if '2fa_user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('auth.login'))
    
    form = TwoFAForm()
    
    if form.validate_on_submit():
        result = AuthService.verify_2fa(form.token.data)
        
        if result['success']:
            user = User.query.get(result['user']['id'])
            login_user(user, remember=session.get('2fa_remember', False))
            flash('Login successful!', 'success')
            
            # Clear session
            session.pop('2fa_user_id', None)
            session.pop('2fa_remember', None)
            
            return redirect(url_for('dashboards.view'))
        else:
            flash(result['message'], 'danger')
    
    return render_template('auth/verify_2fa.html', form=form, title='Verify 2FA')

@auth_bp.route('/setup-2fa', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    """Setup two-factor authentication"""
    if current_user.two_fa_enabled:
        flash('2FA is already enabled for your account.', 'info')
        return redirect(url_for('profile.settings'))
    
    form = TwoFASetupForm()
    
    if request.method == 'GET':
        # Generate secret and QR code
        secret = current_user.generate_2fa_secret()
        form.secret.data = secret
        
        # Generate QR code
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(
            name=current_user.email,
            issuer_name='Kenya Transport Analytics'
        )
        
        # Create QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_code = base64.b64encode(buffer.getvalue()).decode()
    
    if form.validate_on_submit():
        result = AuthService.enable_2fa(current_user, form.token.data)
        
        if result['success']:
            flash('2FA enabled successfully!', 'success')
            
            # Show backup codes
            session['backup_codes'] = result['backup_codes']
            return redirect(url_for('auth.show_backup_codes'))
        else:
            flash(result['message'], 'danger')
    
    return render_template(
        'auth/setup_2fa.html',
        form=form,
        qr_code=qr_code if 'qr_code' in locals() else None,
        secret=secret if 'secret' in locals() else None,
        title='Setup Two-Factor Authentication'
    )

@auth_bp.route('/backup-codes')
@login_required
def show_backup_codes():
    """Show backup codes after 2FA setup"""
    if 'backup_codes' not in session:
        flash('No backup codes to display.', 'warning')
        return redirect(url_for('profile.settings'))
    
    backup_codes = session.pop('backup_codes')
    return render_template('auth/backup_codes.html', backup_codes=backup_codes, title='Backup Codes')

@auth_bp.route('/disable-2fa', methods=['POST'])
@login_required
def disable_2fa():
    """Disable two-factor authentication"""
    result = AuthService.disable_2fa(current_user)
    
    if result['success']:
        flash('2FA disabled successfully.', 'success')
    else:
        flash(result['message'], 'danger')
    
    return redirect(url_for('profile.settings'))

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    
    result = AuthService.logout(current_user, ip_address, user_agent)
    
    if result['success']:
        flash('You have been logged out successfully.', 'info')
    else:
        flash(result['message'], 'warning')
    
    return redirect(url_for('auth.login'))

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request():
    """Request password reset"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboards.view'))
    
    form = PasswordResetRequestForm()
    
    if form.validate_on_submit():
        result = AuthService.request_password_reset(form.email.data)
        
        if result['success']:
            flash('Password reset link has been sent to your email.', 'info')
            # In production, remove token from response
            if 'token' in result:
                flash(f'Reset token: {result["token"]} (for development only)', 'info')
        else:
            flash(result['message'], 'danger')
    
    return render_template('auth/reset_password_request.html', form=form, title='Reset Password')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboards.view'))
    
    form = PasswordResetForm()
    
    if form.validate_on_submit():
        result = AuthService.reset_password(token, form.password.data)
        
        if result['success']:
            flash('Your password has been reset successfully.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(result['message'], 'danger')
    
    return render_template('auth/reset_password.html', form=form, token=token, title='Reset Password')

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password for logged-in users"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        result = AuthService.change_password(
            current_user,
            form.current_password.data,
            form.new_password.data
        )
        
        if result['success']:
            flash('Password changed successfully.', 'success')
            return redirect(url_for('profile.settings'))
        else:
            flash(result['message'], 'danger')
    
    return render_template('auth/change_password.html', form=form, title='Change Password')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration endpoint
    Handles new user account creation with comprehensive validation
    """
    # Redirect if user is already logged in
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for('main.dashboard'))
    
    form = RegisterForm()
    
    # Populate organization choices
    organizations = Organization.query.filter_by(is_active=True).order_by(Organization.name).all()
    form.organization_id.choices = [(0, 'Select your organization...')] + [
        (org.id, f"{org.name} ({org.code})") for org in organizations
    ]
    
    if form.validate_on_submit():
        try:
            # Get default role for new users (usually 'viewer' or 'analyst')
            default_role = Role.query.filter_by(code='viewer').first()
            if not default_role:
                default_role = Role.query.filter_by(code='analyst').first()
            
            if not default_role:
                flash('System configuration error: No default role found. Please contact administrator.', 'error')
                current_app.logger.error('No default role (viewer/analyst) found in database')
                return render_template('auth/register.html', form=form, title='Register')
            
            # Create new user
            user = User(
                email=form.email.data.lower().strip(),
                first_name=form.first_name.data.strip(),
                last_name=form.last_name.data.strip(),
                phone=form.phone.data.strip() if form.phone.data else None,
                organization_id=form.organization_id.data,
                role_id=default_role.id,
                job_title=form.job_title.data.strip() if form.job_title.data else None,
                department=form.department.data.strip() if form.department.data else None,
                is_active=False,  # Requires admin approval
                is_superuser=False
            )
            
            # Set password (hashed automatically by the model)
            user.set_password(form.password.data)
            
            # Add to database
            db.session.add(user)
            db.session.commit()
            
            # Log the registration
            current_app.logger.info(f'New user registered: {user.email} (ID: {user.id})')
            
            # Create audit log
            try:
                from models import AuditLog
                audit = AuditLog(
                    user_id=user.id,
                    action='user_registered',
                    resource_type='User',
                    resource_id=user.id,
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string,
                    details={
                        'email': user.email,
                        'organization_id': user.organization_id,
                        'registration_method': 'web_form'
                    }
                )
                db.session.add(audit)
                db.session.commit()
            except Exception as e:
                current_app.logger.warning(f'Failed to create audit log for registration: {str(e)}')
            
            # Send notification to admins
            try:
                from services import NotificationService
                NotificationService.notify_admins_new_user_registration(user)
            except Exception as e:
                current_app.logger.warning(f'Failed to send admin notification: {str(e)}')
            
            # Success message
            flash(
                'Registration successful! Your account has been created and is pending administrator approval. '
                'You will receive an email notification once your account is activated.',
                'success'
            )
            
            # Redirect to login page
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Registration error: {str(e)}', exc_info=True)
            flash('An error occurred during registration. Please try again or contact support.', 'error')
    
    # Display form errors
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                current_app.logger.warning(f'Registration form error - {field}: {error}')
    
    return render_template(
        'auth/register.html',
        form=form,
        title='Register'
    )


# Optional: Add approval route for admins
@auth_bp.route('/admin/approve-user/<int:user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    """
    Admin endpoint to approve pending user registrations
    """
    if not current_user.has_permission('manage_users'):
        flash('You do not have permission to approve users.', 'error')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if user.is_active:
        flash(f'User {user.email} is already active.', 'info')
        return redirect(request.referrer or url_for('admin.users'))
    
    try:
        user.is_active = True
        db.session.commit()
        
        # Create audit log
        from models import AuditLog
        audit = AuditLog(
            user_id=current_user.id,
            action='user_approved',
            resource_type='User',
            resource_id=user.id,
            ip_address=request.remote_addr,
            details={
                'approved_user_email': user.email,
                'approved_by': current_user.email
            }
        )
        db.session.add(audit)
        db.session.commit()
        
        # Send welcome email to user
        try:
            from services import NotificationService
            NotificationService.send_account_activated_email(user)
        except Exception as e:
            current_app.logger.warning(f'Failed to send activation email: {str(e)}')
        
        flash(f'User {user.full_name} ({user.email}) has been approved and can now log in.', 'success')
        current_app.logger.info(f'User {user.email} approved by {current_user.email}')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error approving user: {str(e)}', exc_info=True)
        flash('An error occurred while approving the user.', 'error')
    
    return redirect(request.referrer or url_for('admin.users'))


@auth_bp.route('/admin/reject-user/<int:user_id>', methods=['POST'])
@login_required
def reject_user(user_id):
    """
    Admin endpoint to reject pending user registrations
    """
    if not current_user.has_permission('manage_users'):
        flash('You do not have permission to reject users.', 'error')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    try:
        # Create audit log before deletion
        from models import AuditLog
        audit = AuditLog(
            user_id=current_user.id,
            action='user_rejected',
            resource_type='User',
            resource_id=user.id,
            ip_address=request.remote_addr,
            details={
                'rejected_user_email': user.email,
                'rejected_by': current_user.email
            }
        )
        db.session.add(audit)
        
        user_email = user.email
        user_name = user.full_name
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        
        flash(f'Registration for {user_name} ({user_email}) has been rejected.', 'success')
        current_app.logger.info(f'User registration {user_email} rejected by {current_user.email}')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error rejecting user: {str(e)}', exc_info=True)
        flash('An error occurred while rejecting the user.', 'error')
    
    return redirect(request.referrer or url_for('admin.users'))