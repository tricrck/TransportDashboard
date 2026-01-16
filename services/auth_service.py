"""
Authentication Service
Handles user authentication, 2FA, password management
"""
from flask import current_app, session
from flask_login import login_user, logout_user

from models import db
from models.user import User
from models.support import (
    AuditLog,
    AuditAction,
    Notification,
    NotificationType
)

from .notification_service import NotificationService
from datetime import datetime

class AuthService:
    """
    Authentication service for user login, 2FA, and session management
    """
    
    @staticmethod
    def authenticate(email, password, remember=False, ip_address=None, user_agent=None):
        """
        Authenticate user with email and password
        
        Args:
            email: User email
            password: User password
            remember: Remember user session
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            dict: Authentication result with status and user/message
        """
        try:
            # Find user
            user = User.query.filter_by(email=email.lower()).first()
            
            if not user:
                # Log failed attempt
                AuditLog.log(
                    action=AuditAction.LOGIN_FAILED,
                    description=f'Login attempt with invalid email: {email}',
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status='failure',
                    error_message='Invalid credentials'
                )
                return {
                    'success': False,
                    'message': 'Invalid email or password',
                    'requires_2fa': False
                }
            
            # Check if account is active
            if not user.is_active:
                AuditLog.log(
                    action=AuditAction.LOGIN_FAILED,
                    user=user,
                    description='Login attempt on deactivated account',
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status='failure',
                    error_message='Account deactivated'
                )
                return {
                    'success': False,
                    'message': 'Your account has been deactivated. Please contact support.',
                    'requires_2fa': False
                }
            
            # Check if account is locked
            if user.is_locked():
                minutes_left = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
                AuditLog.log(
                    action=AuditAction.LOGIN_FAILED,
                    user=user,
                    description='Login attempt on locked account',
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status='failure',
                    error_message='Account locked'
                )
                return {
                    'success': False,
                    'message': f'Account locked due to too many failed attempts. Try again in {minutes_left} minutes.',
                    'requires_2fa': False
                }
            
            # Verify password
            if not user.check_password(password):
                AuditLog.log(
                    action=AuditAction.LOGIN_FAILED,
                    user=user,
                    description='Login attempt with incorrect password',
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status='failure',
                    error_message='Invalid password'
                )
                return {
                    'success': False,
                    'message': 'Invalid email or password',
                    'requires_2fa': False
                }
            
            # Check if 2FA is enabled
            if user.two_fa_enabled:
                # Store user ID in session for 2FA verification
                session['2fa_user_id'] = user.id
                session['2fa_remember'] = remember
                session['2fa_ip'] = ip_address
                session['2fa_user_agent'] = user_agent
                
                return {
                    'success': True,
                    'message': '2FA required',
                    'requires_2fa': True,
                    'user_id': user.id
                }
            
            # Log user in
            return AuthService._complete_login(user, remember, ip_address, user_agent)
            
        except Exception as e:
            current_app.logger.error(f'Authentication error: {str(e)}')
            return {
                'success': False,
                'message': 'An error occurred during authentication',
                'requires_2fa': False
            }
    
    @staticmethod
    def verify_2fa(token, use_backup_code=False):
        """
        Verify 2FA token and complete login
        
        Args:
            token: 6-digit TOTP token or backup code
            use_backup_code: Whether this is a backup code
            
        Returns:
            dict: Verification result
        """
        try:
            # Get user from session
            user_id = session.get('2fa_user_id')
            if not user_id:
                return {
                    'success': False,
                    'message': 'Invalid session. Please login again.'
                }
            
            user = User.query.get(user_id)
            if not user:
                return {
                    'success': False,
                    'message': 'User not found. Please login again.'
                }
            
            # Verify token
            valid = False
            if use_backup_code:
                valid = user.verify_backup_code(token)
            else:
                valid = user.verify_2fa_token(token)
            
            if not valid:
                AuditLog.log(
                    action=AuditAction.LOGIN_FAILED,
                    user=user,
                    description='Invalid 2FA token',
                    ip_address=session.get('2fa_ip'),
                    user_agent=session.get('2fa_user_agent'),
                    status='failure',
                    error_message='Invalid 2FA token'
                )
                return {
                    'success': False,
                    'message': 'Invalid token. Please try again.'
                }
            
            # Complete login
            remember = session.get('2fa_remember', False)
            ip_address = session.get('2fa_ip')
            user_agent = session.get('2fa_user_agent')
            
            # Clear 2FA session data
            session.pop('2fa_user_id', None)
            session.pop('2fa_remember', None)
            session.pop('2fa_ip', None)
            session.pop('2fa_user_agent', None)
            
            return AuthService._complete_login(user, remember, ip_address, user_agent)
            
        except Exception as e:
            current_app.logger.error(f'2FA verification error: {str(e)}')
            return {
                'success': False,
                'message': 'An error occurred during verification'
            }
    
    @staticmethod
    def _complete_login(user, remember, ip_address, user_agent):
        """Complete user login after successful authentication"""
        try:
            # Update user login info
            user.record_login(ip_address=ip_address, user_agent=user_agent)
            
            # Log user in with Flask-Login
            login_user(user, remember=remember)
            
            # Log successful login
            AuditLog.log(
                action=AuditAction.LOGIN,
                user=user,
                description='Successful login',
                ip_address=ip_address,
                user_agent=user_agent,
                status='success'
            )
            
            # Send notification for new login
            NotificationService.create_notification(
                user=user,
                title='New Login Detected',
                message=f'Your account was accessed from {ip_address or "unknown location"}',
                notification_type=NotificationType.INFO,
                priority=1
            )
            
            return {
                'success': True,
                'message': 'Login successful',
                'user': user.to_dict(),
                'requires_2fa': False
            }
            
        except Exception as e:
            current_app.logger.error(f'Login completion error: {str(e)}')
            return {
                'success': False,
                'message': 'An error occurred during login'
            }
    
    @staticmethod
    def logout(user, ip_address=None, user_agent=None):
        """
        Logout user
        
        Args:
            user: User object
            ip_address: Client IP address
            user_agent: Client user agent
        """
        try:
            # Log logout
            AuditLog.log(
                action=AuditAction.LOGOUT,
                user=user,
                description='User logged out',
                ip_address=ip_address,
                user_agent=user_agent,
                status='success'
            )
            
            # Logout with Flask-Login
            logout_user()
            
            # Clear session
            session.clear()
            
            return {
                'success': True,
                'message': 'Logged out successfully'
            }
            
        except Exception as e:
            current_app.logger.error(f'Logout error: {str(e)}')
            return {
                'success': False,
                'message': 'An error occurred during logout'
            }
    
    @staticmethod
    def enable_2fa(user, token):
        """
        Enable 2FA for user after verification
        
        Args:
            user: User object
            token: Verification token
            
        Returns:
            dict: Result with backup codes if successful
        """
        try:
            if user.enable_2fa(token):
                # Generate backup codes
                backup_codes = user.generate_backup_codes()
                
                # Log 2FA enabled
                AuditLog.log(
                    action=AuditAction.TWO_FA_ENABLED,
                    user=user,
                    description='2FA enabled',
                    status='success'
                )
                
                # Send notification
                NotificationService.create_notification(
                    user=user,
                    title='Two-Factor Authentication Enabled',
                    message='2FA has been successfully enabled for your account',
                    notification_type=NotificationType.SUCCESS
                )
                
                return {
                    'success': True,
                    'message': '2FA enabled successfully',
                    'backup_codes': backup_codes
                }
            else:
                return {
                    'success': False,
                    'message': 'Invalid verification code'
                }
                
        except Exception as e:
            current_app.logger.error(f'2FA enable error: {str(e)}')
            return {
                'success': False,
                'message': 'An error occurred while enabling 2FA'
            }
    
    @staticmethod
    def disable_2fa(user):
        """
        Disable 2FA for user
        
        Args:
            user: User object
            
        Returns:
            dict: Result
        """
        try:
            user.disable_2fa()
            
            # Log 2FA disabled
            AuditLog.log(
                action=AuditAction.TWO_FA_DISABLED,
                user=user,
                description='2FA disabled',
                status='success'
            )
            
            # Send notification
            NotificationService.create_notification(
                user=user,
                title='Two-Factor Authentication Disabled',
                message='2FA has been disabled for your account',
                notification_type=NotificationType.WARNING
            )
            
            return {
                'success': True,
                'message': '2FA disabled successfully'
            }
            
        except Exception as e:
            current_app.logger.error(f'2FA disable error: {str(e)}')
            return {
                'success': False,
                'message': 'An error occurred while disabling 2FA'
            }
    
    @staticmethod
    def request_password_reset(email):
        """
        Request password reset
        
        Args:
            email: User email
            
        Returns:
            dict: Result with reset token
        """
        try:
            user = User.query.filter_by(email=email.lower()).first()
            
            if not user:
                # Don't reveal if email exists
                return {
                    'success': True,
                    'message': 'If the email exists, a reset link has been sent'
                }
            
            if not user.is_active:
                return {
                    'success': False,
                    'message': 'Account is deactivated'
                }
            
            # Generate reset token
            token = user.generate_password_reset_token()
            
            # Log password reset request
            AuditLog.log(
                action=AuditAction.PASSWORD_RESET,
                user=user,
                description='Password reset requested',
                status='success'
            )
            
            # Send notification
            NotificationService.create_notification(
                user=user,
                title='Password Reset Requested',
                message='A password reset was requested for your account',
                notification_type=NotificationType.WARNING
            )
            
            # In production, send email with reset link
            # EmailService.send_password_reset_email(user, token)
            
            return {
                'success': True,
                'message': 'Password reset link sent',
                'token': token  # Remove in production, send via email only
            }
            
        except Exception as e:
            current_app.logger.error(f'Password reset request error: {str(e)}')
            return {
                'success': False,
                'message': 'An error occurred'
            }
    
    @staticmethod
    def reset_password(token, new_password):
        """
        Reset password with token
        
        Args:
            token: Reset token
            new_password: New password
            
        Returns:
            dict: Result
        """
        try:
            # Find user with token
            user = User.query.filter_by(password_reset_token=token).first()
            
            if not user or not user.verify_password_reset_token(token):
                return {
                    'success': False,
                    'message': 'Invalid or expired reset token'
                }
            
            # Set new password
            user.set_password(new_password)
            user.password_reset_token = None
            user.password_reset_expires = None
            db.session.commit()
            
            # Log password change
            AuditLog.log(
                action=AuditAction.PASSWORD_CHANGE,
                user=user,
                description='Password reset completed',
                status='success'
            )
            
            # Send notification
            NotificationService.create_notification(
                user=user,
                title='Password Changed',
                message='Your password has been successfully changed',
                notification_type=NotificationType.SUCCESS
            )
            
            return {
                'success': True,
                'message': 'Password reset successfully'
            }
            
        except Exception as e:
            current_app.logger.error(f'Password reset error: {str(e)}')
            db.session.rollback()
            return {
                'success': False,
                'message': 'An error occurred while resetting password'
            }
    
    @staticmethod
    def change_password(user, current_password, new_password):
        """
        Change user password
        
        Args:
            user: User object
            current_password: Current password
            new_password: New password
            
        Returns:
            dict: Result
        """
        try:
            # Verify current password
            if not user.check_password(current_password):
                return {
                    'success': False,
                    'message': 'Current password is incorrect'
                }
            
            # Set new password
            user.set_password(new_password)
            db.session.commit()
            
            # Log password change
            AuditLog.log(
                action=AuditAction.PASSWORD_CHANGE,
                user=user,
                description='Password changed by user',
                status='success'
            )
            
            # Send notification
            NotificationService.create_notification(
                user=user,
                title='Password Changed',
                message='Your password has been successfully changed',
                notification_type=NotificationType.SUCCESS
            )
            
            return {
                'success': True,
                'message': 'Password changed successfully'
            }
            
        except Exception as e:
            current_app.logger.error(f'Password change error: {str(e)}')
            db.session.rollback()
            return {
                'success': False,
                'message': 'An error occurred while changing password'
            }
    
    @staticmethod
    def check_permission(user, permission_code):
        """
        Check if user has permission
        
        Args:
            user: User object
            permission_code: Permission code to check
            
        Returns:
            bool: True if user has permission
        """
        if not user or not user.is_active:
            return False
        
        return user.has_permission(permission_code)
    
    @staticmethod
    def require_permission(user, permission_code):
        """
        Require user to have permission, raise exception if not
        
        Args:
            user: User object
            permission_code: Permission code to require
            
        Raises:
            PermissionError: If user doesn't have permission
        """
        if not AuthService.check_permission(user, permission_code):
            raise PermissionError(f'Permission required: {permission_code}')