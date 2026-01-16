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
# REPORT SERVICE
# ============================================================================

class ReportService:
    """Service for generating reports and exports"""
    
    @staticmethod
    def generate_dashboard_report(dashboard, format='pdf', include_data=True):
        """
        Generate report from dashboard
        
        Args:
            dashboard: Dashboard object
            format: Report format (pdf, png, json, csv)
            include_data: Include current data in report
            
        Returns:
            BytesIO: Report file
        """
        try:
            if format == 'json':
                return ReportService._export_dashboard_json(dashboard, include_data)
            elif format == 'csv':
                return ReportService._export_dashboard_csv(dashboard)
            elif format == 'pdf':
                return ReportService._export_dashboard_pdf(dashboard, include_data)
            else:
                raise ValueError(f'Unsupported format: {format}')
                
        except Exception as e:
            current_app.logger.error(f'Error generating report: {str(e)}')
            raise
    
    @staticmethod
    def _export_dashboard_json(dashboard, include_data):
        """Export dashboard as JSON"""
        data = {
            'dashboard': dashboard.to_dict(include_widgets=True),
            'exported_at': datetime.utcnow().isoformat(),
            'organization': {
                'id': dashboard.organization.id,
                'name': dashboard.organization.name
            } if dashboard.organization else None
        }
        
        if include_data:
            # Fetch data for all widgets
            from .widget_processor import WidgetProcessor
            widget_data = {}
            
            for dw in dashboard.dashboard_widgets:
                result = WidgetProcessor.process_widget(dw.widget)
                if result['success']:
                    widget_data[dw.widget.id] = result['data']
            
            data['widget_data'] = widget_data
        
        # Convert to JSON
        json_str = json.dumps(data, indent=2, default=str)
        return BytesIO(json_str.encode('utf-8'))
    
    @staticmethod
    def _export_dashboard_csv(dashboard):
        """Export dashboard widgets data as CSV"""
        # This would collect data from all table widgets
        # and combine into a CSV
        import pandas as pd
        from .widget_processor import WidgetProcessor
        
        all_data = []
        
        for dw in dashboard.dashboard_widgets:
            if dw.widget.widget_type.value == 'table':
                result = WidgetProcessor.process_widget(dw.widget)
                if result['success'] and 'rows' in result['data']:
                    all_data.extend(result['data']['rows'])
        
        if all_data:
            df = pd.DataFrame(all_data)
            output = BytesIO()
            df.to_csv(output, index=False)
            output.seek(0)
            return output
        
        return BytesIO(b'No data available')
    
    @staticmethod
    def _export_dashboard_pdf(dashboard, include_data):
        """Export dashboard as PDF"""
        # This would use a library like ReportLab or WeasyPrint
        # to generate a PDF report
        raise NotImplementedError('PDF export not yet implemented')
    
    @staticmethod
    def generate_data_source_report(data_source, date_from=None, date_to=None):
        """Generate report for data source performance"""
        try:
            from models import DataRefreshLog
            
            query = DataRefreshLog.query.filter_by(data_source_id=data_source.id)
            
            if date_from:
                query = query.filter(DataRefreshLog.started_at >= date_from)
            if date_to:
                query = query.filter(DataRefreshLog.started_at <= date_to)
            
            logs = query.order_by(DataRefreshLog.started_at.desc()).limit(1000).all()
            
            # Calculate statistics
            successful = len([l for l in logs if l.status == 'success'])
            failed = len([l for l in logs if l.status == 'error'])
            
            avg_duration = sum([l.duration_ms for l in logs if l.duration_ms]) / len(logs) if logs else 0
            avg_records = sum([l.records_fetched for l in logs if l.records_fetched]) / len(logs) if logs else 0
            
            report = {
                'data_source': data_source.to_dict(),
                'period': {
                    'from': date_from.isoformat() if date_from else None,
                    'to': date_to.isoformat() if date_to else None
                },
                'statistics': {
                    'total_refreshes': len(logs),
                    'successful': successful,
                    'failed': failed,
                    'success_rate': (successful / len(logs) * 100) if logs else 0,
                    'avg_duration_ms': avg_duration,
                    'avg_records': avg_records
                },
                'recent_logs': [l.to_dict() for l in logs[:10]]
            }
            
            json_str = json.dumps(report, indent=2, default=str)
            return BytesIO(json_str.encode('utf-8'))
            
        except Exception as e:
            current_app.logger.error(f'Error generating data source report: {str(e)}')
            raise

