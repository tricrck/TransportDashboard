"""
Celery Tasks for Data Source Refresh
"""

from celery import Celery
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Initialize Celery immediately with default config
celery = Celery('transport_dashboard')
celery.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

def init_celery(app):
    """Initialize Celery with Flask app context"""
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery


@celery.task(bind=True, name='tasks.refresh_data_source')
def refresh_data_source_task(self, data_source_id):
    """
    Background task to refresh a data source
    """
    from app import create_app
    from models import DataSource, db
    from services import DataFetcher
    
    app = create_app()
    
    with app.app_context():
        try:
            data_source = DataSource.query.get(data_source_id)
            
            if not data_source:
                logger.error(f"Data source {data_source_id} not found")
                return {'success': False, 'error': 'Data source not found'}
            
            logger.info(f"Refreshing data source: {data_source.name}")
            
            # Fetch data
            result = DataFetcher.fetch_data(data_source, force_refresh=True)
            
            if result['success']:
                # Update last fetched timestamp
                data_source.last_fetched_at = datetime.utcnow()
                data_source.status = 'active'
                data_source.error_count = 0
                db.session.commit()
                
                logger.info(f"Successfully refreshed data source: {data_source.name}")
                return {
                    'success': True,
                    'data_source_id': data_source_id,
                    'record_count': result.get('record_count', 0)
                }
            else:
                # Update error count
                data_source.error_count = (data_source.error_count or 0) + 1
                data_source.last_error = result.get('error', 'Unknown error')
                
                # Mark as failed if threshold exceeded
                if data_source.error_count >= (data_source.alert_threshold or 3):
                    data_source.status = 'failed'
                
                db.session.commit()
                
                logger.error(f"Failed to refresh data source: {data_source.name} - {result.get('error')}")
                return {
                    'success': False,
                    'data_source_id': data_source_id,
                    'error': result.get('error')
                }
                
        except Exception as e:
            logger.exception(f"Error in refresh task for data source {data_source_id}")
            return {
                'success': False,
                'data_source_id': data_source_id,
                'error': str(e)
            }


@celery.task(name='tasks.refresh_all_data_sources')
def refresh_all_data_sources_task():
    """
    Background task to refresh all active data sources with auto-refresh enabled
    """
    from app import create_app
    from models import DataSource
    
    app = create_app()
    
    with app.app_context():
        try:
            data_sources = DataSource.query.filter_by(
                is_active=True,
                auto_refresh=True
            ).all()
            
            logger.info(f"Refreshing {len(data_sources)} data sources")
            
            results = []
            for ds in data_sources:
                result = refresh_data_source_task.delay(ds.id)
                results.append({
                    'data_source_id': ds.id,
                    'task_id': result.id
                })
            
            return {
                'success': True,
                'total': len(data_sources),
                'tasks': results
            }
            
        except Exception as e:
            logger.exception("Error in refresh all task")
            return {
                'success': False,
                'error': str(e)
            }