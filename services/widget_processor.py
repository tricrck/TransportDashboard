
class WidgetProcessor:
    """
    Service for processing widget data and configurations
    Transforms data source data into widget-ready format
    """
    
    @staticmethod
    def process_widget(widget, filters=None):
        """
        Process widget to get display-ready data
        
        Args:
            widget: Widget object
            filters: Optional filters to apply
            
        Returns:
            dict: Processed widget data ready for rendering
        """
        try:
            # Fetch data from source
            fetch_result = DataFetcher.fetch_data(widget.data_source)
            
            if not fetch_result['success']:
                return {
                    'success': False,
                    'error': fetch_result.get('error', 'Failed to fetch data'),
                    'data': None
                }
            
            raw_data = fetch_result['data']
            
            # Apply widget-specific processing
            if widget.widget_type.value == 'stat_card':
                processed = WidgetProcessor._process_stat_card(widget, raw_data, filters)
            elif widget.widget_type.value in ['bar_chart', 'line_chart', 'area_chart']:
                processed = WidgetProcessor._process_chart(widget, raw_data, filters)
            elif widget.widget_type.value in ['pie_chart', 'doughnut_chart']:
                processed = WidgetProcessor._process_pie_chart(widget, raw_data, filters)
            elif widget.widget_type.value == 'table':
                processed = WidgetProcessor._process_table(widget, raw_data, filters)
            else:
                processed = {'data': raw_data}
            
            # Add KPI if configured
            if widget.show_kpi and widget.kpi_config:
                processed['kpi'] = WidgetProcessor._calculate_kpi(widget, raw_data)
            
            return {
                'success': True,
                'widget': widget.to_dict(include_config=True),
                'data': processed,
                'from_cache': fetch_result.get('from_cache', False),
                'cached_at': fetch_result.get('cached_at')
            }
            
        except Exception as e:
            current_app.logger.error(f'Widget processing error: {str(e)}')
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    @staticmethod
    def _process_stat_card(widget, data, filters):
        """Process data for stat card widget"""
        query_config = widget.query_config or {}
        
        # Convert to DataFrame for easier processing
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame([data])
        
        # Apply filters
        if filters:
            df = WidgetProcessor._apply_filters(df, filters)
        
        # Get field and aggregation
        field = query_config.get('field', df.columns[0])
        agg_func = query_config.get('aggregation', 'sum')
        
        # Calculate value
        if agg_func == 'sum':
            value = df[field].sum()
        elif agg_func == 'avg':
            value = df[field].mean()
        elif agg_func == 'count':
            value = len(df)
        elif agg_func == 'min':
            value = df[field].min()
        elif agg_func == 'max':
            value = df[field].max()
        else:
            value = df[field].iloc[0] if len(df) > 0 else 0
        
        return {
            'value': float(value) if pd.notna(value) else 0,
            'formatted_value': WidgetProcessor._format_value(value, query_config.get('format')),
            'unit': query_config.get('unit', ''),
            'trend': WidgetProcessor._calculate_trend(df, field, agg_func)
        }
    
    @staticmethod
    def _process_chart(widget, data, filters):
        """Process data for chart widgets"""
        query_config = widget.query_config or {}
        
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame([data])
        
        # Apply filters
        if filters:
            df = WidgetProcessor._apply_filters(df, filters)
        
        # Get fields
        x_field = query_config.get('x_axis', df.columns[0])
        y_field = query_config.get('y_axis', df.columns[1])
        
        # Apply grouping if specified
        if query_config.get('grouping'):
            group_by = query_config['grouping']
            agg_func = query_config.get('aggregation', 'sum')
            df = df.groupby(group_by)[y_field].agg(agg_func).reset_index()
        
        # Sort if specified
        if query_config.get('sorting'):
            sort_field = query_config['sorting'].get('field', x_field)
            sort_order = query_config['sorting'].get('order', 'asc')
            df = df.sort_values(sort_field, ascending=(sort_order == 'asc'))
        
        # Limit records
        limit = widget.limit or 100
        df = df.head(limit)
        
        return {
            'labels': df[x_field].tolist(),
            'datasets': [{
                'label': y_field,
                'data': df[y_field].tolist()
            }]
        }
    
    @staticmethod
    def _process_pie_chart(widget, data, filters):
        """Process data for pie/doughnut charts"""
        query_config = widget.query_config or {}
        
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame([data])
        
        # Apply filters
        if filters:
            df = WidgetProcessor._apply_filters(df, filters)
        
        # Get fields
        label_field = query_config.get('label_field', df.columns[0])
        value_field = query_config.get('value_field', df.columns[1])
        
        # Group and aggregate
        df = df.groupby(label_field)[value_field].sum().reset_index()
        
        return {
            'labels': df[label_field].tolist(),
            'datasets': [{
                'data': df[value_field].tolist()
            }]
        }
    
    @staticmethod
    def _process_table(widget, data, filters):
        """Process data for table widget"""
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame([data])
        
        # Apply filters
        if filters:
            df = WidgetProcessor._apply_filters(df, filters)
        
        # Select fields if specified
        if widget.fields:
            fields = json.loads(widget.fields) if isinstance(widget.fields, str) else widget.fields
            df = df[fields]
        
        # Sort if specified
        if widget.sorting:
            sorting = json.loads(widget.sorting) if isinstance(widget.sorting, str) else widget.sorting
            df = df.sort_values(
                sorting.get('field'),
                ascending=(sorting.get('order', 'asc') == 'asc')
            )
        
        # Limit records
        limit = widget.limit or 100
        df = df.head(limit)
        
        return {
            'columns': df.columns.tolist(),
            'rows': df.to_dict('records'),
            'total_rows': len(df)
        }
    
    @staticmethod
    def _apply_filters(df, filters):
        """Apply filters to DataFrame"""
        for filter_config in filters:
            field = filter_config.get('field')
            operator = filter_config.get('operator', 'equals')
            value = filter_config.get('value')
            
            if operator == 'equals':
                df = df[df[field] == value]
            elif operator == 'not_equals':
                df = df[df[field] != value]
            elif operator == 'greater_than':
                df = df[df[field] > value]
            elif operator == 'less_than':
                df = df[df[field] < value]
            elif operator == 'contains':
                df = df[df[field].str.contains(value, na=False)]
        
        return df
    
    @staticmethod
    def _calculate_trend(df, field, agg_func):
        """Calculate trend for comparison"""
        if len(df) < 2:
            return None
        
        # Simple trend calculation
        first_half = df.head(len(df) // 2)
        second_half = df.tail(len(df) // 2)
        
        if agg_func == 'sum':
            first_value = first_half[field].sum()
            second_value = second_half[field].sum()
        elif agg_func == 'avg':
            first_value = first_half[field].mean()
            second_value = second_half[field].mean()
        else:
            return None
        
        if first_value == 0:
            return None
        
        change = ((second_value - first_value) / first_value) * 100
        
        return {
            'direction': 'up' if change > 0 else 'down' if change < 0 else 'neutral',
            'percentage': abs(change),
            'value': change
        }
    
    @staticmethod
    def _calculate_kpi(widget, data):
        """Calculate KPI based on configuration"""
        kpi_config = json.loads(widget.kpi_config) if isinstance(widget.kpi_config, str) else widget.kpi_config
        
        # Implementation depends on KPI configuration
        return {
            'value': 0,
            'target': 0,
            'percentage': 0,
            'status': 'neutral'
        }
    
    @staticmethod
    def _format_value(value, format_type=None):
        """Format value for display"""
        if pd.isna(value):
            return 'N/A'
        
        if format_type == 'currency':
            return f'KES {value:,.2f}'
        elif format_type == 'percentage':
            return f'{value:.1f}%'
        elif format_type == 'integer':
            return f'{int(value):,}'
        elif format_type == 'decimal':
            return f'{value:,.2f}'
        else:
            return str(value)
