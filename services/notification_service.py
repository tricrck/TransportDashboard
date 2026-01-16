from datetime import datetime, timedelta
from flask import current_app
from models import (
    Notification, NotificationType, User,
    Dashboard, Widget, DataSource, db
)
import json
from io import BytesIO
import redis

# ============================================================================
# NOTIFICATION SERVICE
# ============================================================================

class NotificationService:
    """Service for creating and managing user notifications"""
    
    @staticmethod
    def create_notification(user, title, message, notification_type=NotificationType.INFO,
                          action_url=None, action_label=None, priority=0, expires_in_days=30):
        """
        Create a notification for a user
        
        Args:
            user: User object or user ID
            title: Notification title
            message: Notification message
            notification_type: NotificationType enum
            action_url: Optional URL for action button
            action_label: Optional label for action button
            priority: Priority level (higher = more important)
            expires_in_days: Days until notification expires
            
        Returns:
            Notification: Created notification object
        """
        try:
            if isinstance(user, int):
                user = User.query.get(user)
            
            notification = Notification.create(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type,
                action_url=action_url,
                action_label=action_label,
                priority=priority,
                expires_in_days=expires_in_days
            )
            
            # Send email if user has notifications enabled
            if user.email_notifications:
                # TODO: Integrate with email service
                pass
            
            return notification
            
        except Exception as e:
            current_app.logger.error(f'Error creating notification: {str(e)}')
            return None
    
    @staticmethod
    def notify_data_source_error(data_source, error_message):
        """Notify users about data source errors"""
        try:
            # Notify organization admins
            admins = User.query.filter_by(
                organization_id=data_source.organization_id,
                is_active=True
            ).join(User.role).filter(
                User.role.has(code='org_admin')
            ).all()
            
            for admin in admins:
                NotificationService.create_notification(
                    user=admin,
                    title=f'Data Source Error: {data_source.name}',
                    message=f'Error fetching data: {error_message}',
                    notification_type=NotificationType.ERROR,
                    action_url=f'/data-sources/{data_source.id}',
                    action_label='View Data Source',
                    priority=5
                )
                
        except Exception as e:
            current_app.logger.error(f'Error notifying data source error: {str(e)}')
    
    @staticmethod
    def notify_dashboard_shared(dashboard, shared_with_users, shared_by):
        """Notify users when dashboard is shared with them"""
        try:
            for user in shared_with_users:
                NotificationService.create_notification(
                    user=user,
                    title='Dashboard Shared With You',
                    message=f'{shared_by.full_name} shared "{dashboard.name}" dashboard with you',
                    notification_type=NotificationType.INFO,
                    action_url=f'/dashboards/{dashboard.id}',
                    action_label='View Dashboard',
                    priority=3
                )
                
        except Exception as e:
            current_app.logger.error(f'Error notifying dashboard share: {str(e)}')
    
    @staticmethod
    def get_user_notifications(user, unread_only=False, limit=50):
        """Get user notifications"""
        query = Notification.query.filter_by(user_id=user.id)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        query = query.order_by(
            Notification.priority.desc(),
            Notification.created_at.desc()
        ).limit(limit)
        
        return query.all()
    
    @staticmethod
    def mark_all_read(user):
        """Mark all notifications as read for a user"""
        try:
            Notification.query.filter_by(
                user_id=user.id,
                is_read=False
            ).update({'is_read': True, 'read_at': datetime.utcnow()})
            
            db.session.commit()
            return True
            
        except Exception as e:
            current_app.logger.error(f'Error marking notifications as read: {str(e)}')
            db.session.rollback()
            return False
    
    @staticmethod
    def cleanup_expired():
        """Remove expired notifications"""
        try:
            expired = Notification.query.filter(
                Notification.expires_at < datetime.utcnow()
            ).all()
            
            for notification in expired:
                db.session.delete(notification)
            
            db.session.commit()
            return len(expired)
            
        except Exception as e:
            current_app.logger.error(f'Error cleaning up notifications: {str(e)}')
            db.session.rollback()
            return 0

