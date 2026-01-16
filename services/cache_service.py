"""
Supporting Services: Notifications, Reports, and Caching
"""

from datetime import datetime, timedelta
from flask import current_app
from models import (
    Notification, NotificationType, User,
    Dashboard, Widget, DataSource, db
)
import json
from io import BytesIO
import redis
import logging # Add this import at the top

# Create a standard logger for this module
logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.redis_client = None
        self.enabled = False

    def init_app(self, app):
        """Initialize Redis with Flask app context"""
        try:
            redis_url = app.config.get(
                'REDIS_URL',
                'redis://default:PN3NRmnlLZy8TRJjos5HiUAnd4z9tpdp@redis-10680.c323.us-east-1-2.ec2.cloud.redislabs.com:10680'
            )
            self.redis_client = redis.from_url(redis_url)
            self.enabled = True
            app.logger.info("Redis cache initialized successfully")
        except Exception as e:
            app.logger.warning(f"Redis disabled: {e}")
            self.redis_client = None
            self.enabled = False

    
    def get(self, key):
        """Get value from cache"""
        if not self.enabled:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            current_app.logger.error(f'Cache get error: {str(e)}')
            return None
    
    def set(self, key, value, ttl=300):
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (default 5 minutes)
        """
        if not self.enabled:
            return False
        
        try:
            json_value = json.dumps(value, default=str)
            self.redis_client.setex(key, ttl, json_value)
            return True
        except Exception as e:
            current_app.logger.error(f'Cache set error: {str(e)}')
            return False
    
    def delete(self, key):
        """Delete value from cache"""
        if not self.enabled:
            return False
        
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            current_app.logger.error(f'Cache delete error: {str(e)}')
            return False
    
    def clear_pattern(self, pattern):
        """Delete all keys matching pattern"""
        if not self.enabled:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            current_app.logger.error(f'Cache clear pattern error: {str(e)}')
            return 0
    
    def get_widget_data(self, widget_id):
        """Get cached widget data"""
        return self.get(f'widget:{widget_id}:data')
    
    def set_widget_data(self, widget_id, data, ttl=300):
        """Cache widget data"""
        return self.set(f'widget:{widget_id}:data', data, ttl)
    
    def clear_widget_cache(self, widget_id):
        """Clear widget cache"""
        return self.delete(f'widget:{widget_id}:data')
    
    def get_dashboard_data(self, dashboard_id):
        """Get cached dashboard data"""
        return self.get(f'dashboard:{dashboard_id}:data')
    
    def set_dashboard_data(self, dashboard_id, data, ttl=300):
        """Cache dashboard data"""
        return self.set(f'dashboard:{dashboard_id}:data', data, ttl)
    
    def clear_dashboard_cache(self, dashboard_id):
        """Clear dashboard cache"""
        return self.delete(f'dashboard:{dashboard_id}:data')
    
    def clear_organization_cache(self, organization_id):
        """Clear all caches for an organization"""
        patterns = [
            f'org:{organization_id}:*',
            f'dashboard:*:org:{organization_id}',
            f'widget:*:org:{organization_id}'
        ]
        
        total = 0
        for pattern in patterns:
            total += self.clear_pattern(pattern)
        
        return total


# Global cache service instance
cache_service = CacheService()