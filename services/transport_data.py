"""
Transport Data Service
Handles transport-specific data operations, route analysis, and fleet management
"""

from datetime import datetime, timedelta
from flask import current_app
from models import DataSource, db
import pandas as pd
import json
from .data_fetcher import DataFetcher


class TransportDataService:
    """
    Service for transport data processing and analysis
    Handles routes, vehicles, trips, and logistics data
    """
    
    @staticmethod
    def get_route_analytics(data_source, start_date=None, end_date=None):
        """
        Get analytics for transport routes
        
        Args:
            data_source: DataSource containing route data
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            dict: Route analytics including distance, duration, frequency
        """
        try:
            # Fetch route data
            result = DataFetcher.fetch_data(data_source)
            
            if not result['success']:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to fetch route data')
                }
            
            # Convert to DataFrame
            df = pd.DataFrame(result['data'])
            
            # Filter by date range if provided
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                if start_date:
                    df = df[df['date'] >= start_date]
                if end_date:
                    df = df[df['date'] <= end_date]
            
            # Calculate analytics
            analytics = {
                'total_routes': len(df['route_id'].unique()) if 'route_id' in df.columns else len(df),
                'total_trips': len(df),
                'total_distance_km': float(df['distance_km'].sum()) if 'distance_km' in df.columns else 0,
                'avg_distance_km': float(df['distance_km'].mean()) if 'distance_km' in df.columns else 0,
                'total_duration_hours': float(df['duration_hours'].sum()) if 'duration_hours' in df.columns else 0,
                'avg_duration_hours': float(df['duration_hours'].mean()) if 'duration_hours' in df.columns else 0,
            }
            
            # Route breakdown
            if 'route_id' in df.columns and 'route_name' in df.columns:
                route_stats = df.groupby(['route_id', 'route_name']).agg({
                    'distance_km': 'sum' if 'distance_km' in df.columns else 'count',
                    'route_id': 'count'
                }).rename(columns={'route_id': 'trip_count'}).reset_index()
                
                analytics['route_breakdown'] = route_stats.to_dict('records')
            
            # Time-based analysis
            if 'date' in df.columns:
                daily_stats = df.groupby(df['date'].dt.date).agg({
                    'route_id': 'count',
                    'distance_km': 'sum' if 'distance_km' in df.columns else 'count'
                }).rename(columns={'route_id': 'trip_count'}).reset_index()
                
                analytics['daily_trends'] = daily_stats.to_dict('records')
            
            return {
                'success': True,
                'analytics': analytics,
                'period': {
                    'start': start_date.isoformat() if start_date else None,
                    'end': end_date.isoformat() if end_date else None
                }
            }
            
        except Exception as e:
            current_app.logger.error(f'Route analytics error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_vehicle_performance(data_source, vehicle_ids=None):
        """
        Get performance metrics for vehicles
        
        Args:
            data_source: DataSource containing vehicle data
            vehicle_ids: Optional list of specific vehicle IDs to analyze
            
        Returns:
            dict: Vehicle performance metrics
        """
        try:
            result = DataFetcher.fetch_data(data_source)
            
            if not result['success']:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to fetch vehicle data')
                }
            
            df = pd.DataFrame(result['data'])
            
            # Filter by vehicle IDs if provided
            if vehicle_ids and 'vehicle_id' in df.columns:
                df = df[df['vehicle_id'].isin(vehicle_ids)]
            
            # Calculate performance metrics
            if 'vehicle_id' in df.columns:
                vehicle_stats = df.groupby('vehicle_id').agg({
                    'distance_km': 'sum' if 'distance_km' in df.columns else 'count',
                    'fuel_consumed_liters': 'sum' if 'fuel_consumed_liters' in df.columns else 'count',
                    'vehicle_id': 'count'
                }).rename(columns={'vehicle_id': 'trip_count'}).reset_index()
                
                # Calculate fuel efficiency
                if 'distance_km' in vehicle_stats.columns and 'fuel_consumed_liters' in vehicle_stats.columns:
                    vehicle_stats['km_per_liter'] = (
                        vehicle_stats['distance_km'] / vehicle_stats['fuel_consumed_liters']
                    ).round(2)
                
                performance = {
                    'total_vehicles': len(vehicle_stats),
                    'vehicle_metrics': vehicle_stats.to_dict('records')
                }
                
                # Overall fleet performance
                if 'km_per_liter' in vehicle_stats.columns:
                    performance['fleet_avg_efficiency'] = float(vehicle_stats['km_per_liter'].mean())
                    performance['best_efficiency'] = float(vehicle_stats['km_per_liter'].max())
                    performance['worst_efficiency'] = float(vehicle_stats['km_per_liter'].min())
                
                return {
                    'success': True,
                    'performance': performance
                }
            else:
                return {
                    'success': False,
                    'error': 'Vehicle ID column not found in data'
                }
            
        except Exception as e:
            current_app.logger.error(f'Vehicle performance error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def calculate_trip_costs(data_source, cost_config=None):
        """
        Calculate costs for trips
        
        Args:
            data_source: DataSource containing trip data
            cost_config: Configuration with cost parameters
                {
                    'fuel_cost_per_liter': 150,
                    'driver_cost_per_hour': 500,
                    'maintenance_cost_per_km': 5,
                    'overhead_percentage': 15
                }
            
        Returns:
            dict: Trip cost analysis
        """
        try:
            # Default cost configuration
            if not cost_config:
                cost_config = {
                    'fuel_cost_per_liter': 150,  # KES
                    'driver_cost_per_hour': 500,  # KES
                    'maintenance_cost_per_km': 5,  # KES
                    'overhead_percentage': 15
                }
            
            result = DataFetcher.fetch_data(data_source)
            
            if not result['success']:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to fetch trip data')
                }
            
            df = pd.DataFrame(result['data'])
            
            # Calculate costs
            if 'fuel_consumed_liters' in df.columns:
                df['fuel_cost'] = df['fuel_consumed_liters'] * cost_config['fuel_cost_per_liter']
            else:
                df['fuel_cost'] = 0
            
            if 'duration_hours' in df.columns:
                df['driver_cost'] = df['duration_hours'] * cost_config['driver_cost_per_hour']
            else:
                df['driver_cost'] = 0
            
            if 'distance_km' in df.columns:
                df['maintenance_cost'] = df['distance_km'] * cost_config['maintenance_cost_per_km']
            else:
                df['maintenance_cost'] = 0
            
            # Total direct costs
            df['direct_cost'] = df['fuel_cost'] + df['driver_cost'] + df['maintenance_cost']
            
            # Add overhead
            df['overhead_cost'] = df['direct_cost'] * (cost_config['overhead_percentage'] / 100)
            df['total_cost'] = df['direct_cost'] + df['overhead_cost']
            
            # Calculate cost per km
            if 'distance_km' in df.columns:
                df['cost_per_km'] = df['total_cost'] / df['distance_km']
            
            # Summary statistics
            cost_summary = {
                'total_trips': len(df),
                'total_fuel_cost': float(df['fuel_cost'].sum()),
                'total_driver_cost': float(df['driver_cost'].sum()),
                'total_maintenance_cost': float(df['maintenance_cost'].sum()),
                'total_overhead_cost': float(df['overhead_cost'].sum()),
                'total_cost': float(df['total_cost'].sum()),
                'avg_cost_per_trip': float(df['total_cost'].mean()),
            }
            
            if 'cost_per_km' in df.columns:
                cost_summary['avg_cost_per_km'] = float(df['cost_per_km'].mean())
            
            # Route-based costs
            if 'route_id' in df.columns:
                route_costs = df.groupby('route_id').agg({
                    'total_cost': ['sum', 'mean', 'count'],
                    'distance_km': 'sum' if 'distance_km' in df.columns else 'count'
                }).round(2)
                
                route_costs.columns = ['total_cost', 'avg_cost', 'trip_count', 'total_distance']
                cost_summary['route_breakdown'] = route_costs.reset_index().to_dict('records')
            
            return {
                'success': True,
                'cost_analysis': cost_summary,
                'cost_config': cost_config,
                'detailed_trips': df.to_dict('records')
            }
            
        except Exception as e:
            current_app.logger.error(f'Trip cost calculation error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_driver_performance(data_source, driver_ids=None):
        """
        Get performance metrics for drivers
        
        Args:
            data_source: DataSource containing driver trip data
            driver_ids: Optional list of specific driver IDs
            
        Returns:
            dict: Driver performance metrics
        """
        try:
            result = DataFetcher.fetch_data(data_source)
            
            if not result['success']:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to fetch driver data')
                }
            
            df = pd.DataFrame(result['data'])
            
            # Filter by driver IDs if provided
            if driver_ids and 'driver_id' in df.columns:
                df = df[df['driver_id'].isin(driver_ids)]
            
            if 'driver_id' not in df.columns:
                return {
                    'success': False,
                    'error': 'Driver ID column not found in data'
                }
            
            # Calculate driver metrics
            driver_stats = df.groupby('driver_id').agg({
                'distance_km': 'sum' if 'distance_km' in df.columns else 'count',
                'duration_hours': 'sum' if 'duration_hours' in df.columns else 'count',
                'driver_id': 'count'
            }).rename(columns={'driver_id': 'trip_count'}).reset_index()
            
            # Calculate additional metrics
            if 'distance_km' in driver_stats.columns and 'duration_hours' in driver_stats.columns:
                driver_stats['avg_speed_kmh'] = (
                    driver_stats['distance_km'] / driver_stats['duration_hours']
                ).round(2)
            
            # Safety metrics if available
            if 'incidents' in df.columns:
                incident_stats = df.groupby('driver_id')['incidents'].sum()
                driver_stats = driver_stats.merge(
                    incident_stats.to_frame('total_incidents'),
                    on='driver_id',
                    how='left'
                )
            
            performance = {
                'total_drivers': len(driver_stats),
                'driver_metrics': driver_stats.to_dict('records')
            }
            
            return {
                'success': True,
                'performance': performance
            }
            
        except Exception as e:
            current_app.logger.error(f'Driver performance error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def optimize_routes(data_source, optimization_criteria='distance'):
        """
        Analyze routes for optimization opportunities
        
        Args:
            data_source: DataSource containing route data
            optimization_criteria: 'distance', 'time', or 'cost'
            
        Returns:
            dict: Route optimization recommendations
        """
        try:
            result = DataFetcher.fetch_data(data_source)
            
            if not result['success']:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to fetch route data')
                }
            
            df = pd.DataFrame(result['data'])
            
            recommendations = []
            
            # Analyze route efficiency
            if 'route_id' in df.columns:
                route_analysis = df.groupby('route_id').agg({
                    'distance_km': ['mean', 'std'] if 'distance_km' in df.columns else ['count'],
                    'duration_hours': ['mean', 'std'] if 'duration_hours' in df.columns else ['count'],
                    'route_id': 'count'
                }).round(2)
                
                # Identify routes with high variation (potential for optimization)
                if 'distance_km' in df.columns:
                    high_variance_routes = route_analysis[
                        route_analysis[('distance_km', 'std')] > route_analysis[('distance_km', 'mean')] * 0.2
                    ]
                    
                    for route_id in high_variance_routes.index:
                        recommendations.append({
                            'route_id': route_id,
                            'type': 'high_variance',
                            'message': 'Route shows high distance variation, review for consistency',
                            'priority': 'medium'
                        })
                
                # Identify underutilized routes
                avg_trips = route_analysis[('route_id', 'count')].mean()
                underutilized = route_analysis[route_analysis[('route_id', 'count')] < avg_trips * 0.5]
                
                for route_id in underutilized.index:
                    recommendations.append({
                        'route_id': route_id,
                        'type': 'underutilized',
                        'message': 'Route is underutilized, consider consolidation',
                        'priority': 'low'
                    })
            
            return {
                'success': True,
                'optimization_criteria': optimization_criteria,
                'recommendations': recommendations,
                'total_recommendations': len(recommendations)
            }
            
        except Exception as e:
            current_app.logger.error(f'Route optimization error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_fleet_utilization(data_source, period_days=30):
        """
        Calculate fleet utilization metrics
        
        Args:
            data_source: DataSource containing vehicle usage data
            period_days: Number of days to analyze
            
        Returns:
            dict: Fleet utilization metrics
        """
        try:
            result = DataFetcher.fetch_data(data_source)
            
            if not result['success']:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to fetch fleet data')
                }
            
            df = pd.DataFrame(result['data'])
            
            # Filter by period if date column exists
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                cutoff_date = datetime.utcnow() - timedelta(days=period_days)
                df = df[df['date'] >= cutoff_date]
            
            utilization = {}
            
            # Vehicle utilization
            if 'vehicle_id' in df.columns:
                total_vehicles = df['vehicle_id'].nunique()
                active_days_per_vehicle = df.groupby('vehicle_id')['date'].nunique() if 'date' in df.columns else None
                
                utilization['total_vehicles'] = total_vehicles
                utilization['period_days'] = period_days
                
                if active_days_per_vehicle is not None:
                    utilization['avg_active_days_per_vehicle'] = float(active_days_per_vehicle.mean())
                    utilization['utilization_rate'] = float(
                        (active_days_per_vehicle.mean() / period_days) * 100
                    )
                    utilization['vehicle_utilization'] = active_days_per_vehicle.to_dict()
            
            # Distance utilization
            if 'distance_km' in df.columns:
                utilization['total_distance_km'] = float(df['distance_km'].sum())
                utilization['avg_distance_per_vehicle'] = float(
                    df.groupby('vehicle_id')['distance_km'].sum().mean()
                ) if 'vehicle_id' in df.columns else 0
            
            return {
                'success': True,
                'utilization': utilization
            }
            
        except Exception as e:
            current_app.logger.error(f'Fleet utilization error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def export_transport_report(data_source, report_type='summary', start_date=None, end_date=None):
        """
        Export comprehensive transport report
        
        Args:
            data_source: DataSource for transport data
            report_type: Type of report ('summary', 'detailed', 'financial')
            start_date: Start date for report
            end_date: End date for report
            
        Returns:
            dict: Comprehensive transport report
        """
        try:
            report = {
                'generated_at': datetime.utcnow().isoformat(),
                'report_type': report_type,
                'period': {
                    'start': start_date.isoformat() if start_date else None,
                    'end': end_date.isoformat() if end_date else None
                }
            }
            
            # Get various analytics
            route_analytics = TransportDataService.get_route_analytics(
                data_source, start_date, end_date
            )
            if route_analytics['success']:
                report['route_analytics'] = route_analytics['analytics']
            
            if report_type in ['detailed', 'financial']:
                vehicle_performance = TransportDataService.get_vehicle_performance(data_source)
                if vehicle_performance['success']:
                    report['vehicle_performance'] = vehicle_performance['performance']
                
                cost_analysis = TransportDataService.calculate_trip_costs(data_source)
                if cost_analysis['success']:
                    report['cost_analysis'] = cost_analysis['cost_analysis']
            
            if report_type == 'detailed':
                fleet_utilization = TransportDataService.get_fleet_utilization(data_source)
                if fleet_utilization['success']:
                    report['fleet_utilization'] = fleet_utilization['utilization']
            
            return {
                'success': True,
                'report': report
            }
            
        except Exception as e:
            current_app.logger.error(f'Transport report export error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }