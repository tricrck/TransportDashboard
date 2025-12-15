from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from datetime import datetime, timedelta
import json

app = Flask(__name__)
CORS(app)

# Sample data - Replace with actual database queries or API calls

class TransportDataService:
    """Service to fetch transport data from various sources"""
    
    @staticmethod
    def get_kpa_data():
        """Kenya Ports Authority data"""
        return {
            'summary': {
                'cargo_throughput': 34.5,  # Million MT
                'container_traffic': 1.45,  # Million TEUs
                'vessel_turnaround': 3.2,  # days
                'berth_productivity': 28,  # moves/hour
                'container_dwell_time': 4.5,  # days
                'transit_traffic': 8.5  # Million MT
            },
            'monthly_trend': [
                {'month': 'Jan', 'cargo': 2.8, 'containers': 115, 'vessels': 245},
                {'month': 'Feb', 'cargo': 2.9, 'containers': 120, 'vessels': 252},
                {'month': 'Mar', 'cargo': 3.1, 'containers': 125, 'vessels': 268},
                {'month': 'Apr', 'cargo': 2.7, 'containers': 118, 'vessels': 238},
                {'month': 'May', 'cargo': 3.0, 'containers': 128, 'vessels': 255},
                {'month': 'Jun', 'cargo': 3.2, 'containers': 132, 'vessels': 270}
            ],
            'ports': [
                {'name': 'Mombasa', 'cargo': 32.5, 'containers': 1.4},
                {'name': 'Lamu', 'cargo': 1.5, 'containers': 0.03},
                {'name': 'Kisumu (Inland)', 'cargo': 0.5, 'containers': 0.02}
            ]
        }
    
    @staticmethod
    def get_rail_data():
        """Kenya Railways Corporation data"""
        return {
            'sgr': {
                'passengers': 4.2,  # Million
                'cargo': 5.5,  # Million MT
                'revenue': 12.5,  # Billion KES
                'trip_time': 4.5  # hours (Mombasa-Nairobi)
            },
            'mgr': {
                'passengers': 0.8,  # Million
                'cargo': 0.3,  # Million MT
                'revenue': 1.2  # Billion KES
            },
            'monthly_passengers': [
                {'month': 'Jan', 'sgr': 340, 'mgr': 65},
                {'month': 'Feb', 'sgr': 355, 'mgr': 68},
                {'month': 'Mar', 'sgr': 370, 'mgr': 70},
                {'month': 'Apr', 'sgr': 345, 'mgr': 67},
                {'month': 'May', 'sgr': 360, 'mgr': 72},
                {'month': 'Jun', 'sgr': 375, 'mgr': 75}
            ],
            'monthly_cargo': [
                {'month': 'Jan', 'sgr': 450, 'mgr': 25},
                {'month': 'Feb', 'sgr': 460, 'mgr': 26},
                {'month': 'Mar', 'sgr': 475, 'mgr': 27},
                {'month': 'Apr', 'sgr': 445, 'mgr': 24},
                {'month': 'May', 'sgr': 465, 'mgr': 28},
                {'month': 'Jun', 'sgr': 480, 'mgr': 30}
            ]
        }
    
    @staticmethod
    def get_air_data():
        """KAA and KCAA data"""
        return {
            'infrastructure': {
                'airports': 28,
                'airstrips': 187,
                'international_airports': 4
            },
            'passengers': {
                'jkia': 8.5,  # Million
                'mia': 1.2,  # Million
                'eld': 0.8,  # Million
                'total': 10.8  # Million
            },
            'freight': {
                'total': 285,  # Thousand MT
                'international': 245,
                'domestic': 40
            },
            'operations': {
                'flight_movements': 95000,
                'on_time_performance': 78.5,  # %
                'turnaround_time': 45  # minutes
            },
            'monthly_trend': [
                {'month': 'Jan', 'international': 680, 'domestic': 320, 'freight': 22},
                {'month': 'Feb', 'international': 720, 'domestic': 340, 'freight': 23},
                {'month': 'Mar', 'international': 750, 'domestic': 360, 'freight': 24},
                {'month': 'Apr', 'international': 690, 'domestic': 330, 'freight': 21},
                {'month': 'May', 'international': 740, 'domestic': 350, 'freight': 25},
                {'month': 'Jun', 'international': 770, 'domestic': 370, 'freight': 26}
            ]
        }
    
    @staticmethod
    def get_road_data():
        """NTSA and KeNHA data"""
        return {
            'vehicles': {
                'total': 4.8,  # Million
                'by_category': [
                    {'category': 'Private Cars', 'count': 2100000},
                    {'category': 'Motorcycles', 'count': 1500000},
                    {'category': 'Commercial', 'count': 850000},
                    {'category': 'PSV', 'count': 350000}
                ],
                'new_registrations': 285000  # Annual
            },
            'psv': {
                'licenses_issued': 45000,
                'saccos_registered': 280,
                'active_routes': 1250
            },
            'safety': {
                'total_accidents': 15420,
                'fatalities': 3500,
                'injuries': 8920,
                'severity_rate': 22.7  # %
            },
            'road_network': {
                'total_km': 177800,
                'paved_km': 14500,
                'good_condition_percent': 68.5,
                'projects_completed': 45
            }
        }
    
    @staticmethod
    def get_pipeline_data():
        """Kenya Pipeline Corporation data"""
        return {
            'operations': {
                'throughput': 4.8,  # Billion litres
                'system_uptime': 98.5,  # %
                'delivery_efficiency': 96.8  # %
            },
            'safety': {
                'incidents': 2,
                'spills': 0,
                'safety_score': 98.2
            },
            'infrastructure': {
                'pipeline_length': 1254,  # km
                'storage_capacity': 458,  # Million litres
                'depots': 18
            },
            'monthly_trend': [
                {'month': 'Jan', 'throughput': 385, 'uptime': 98.2},
                {'month': 'Feb', 'throughput': 395, 'uptime': 98.5},
                {'month': 'Mar', 'throughput': 410, 'uptime': 98.8},
                {'month': 'Apr', 'throughput': 380, 'uptime': 98.0},
                {'month': 'May', 'throughput': 405, 'uptime': 98.7},
                {'month': 'Jun', 'throughput': 420, 'uptime': 99.0}
            ]
        }


# API Endpoints

@app.route('/')
def index():
    """Serve the main dashboard page"""
    return render_template('index.html')

@app.route('/api/overview')
def get_overview():
    """Get overview data for all transport modes"""
    try:
        kpa = TransportDataService.get_kpa_data()
        rail = TransportDataService.get_rail_data()
        air = TransportDataService.get_air_data()
        road = TransportDataService.get_road_data()
        pipeline = TransportDataService.get_pipeline_data()
        
        overview = {
            'sea': {
                'cargo_throughput': kpa['summary']['cargo_throughput'],
                'container_traffic': kpa['summary']['container_traffic']
            },
            'rail': {
                'total_passengers': rail['sgr']['passengers'] + rail['mgr']['passengers'],
                'total_cargo': rail['sgr']['cargo'] + rail['mgr']['cargo'],
                'total_revenue': rail['sgr']['revenue'] + rail['mgr']['revenue']
            },
            'air': {
                'total_passengers': air['passengers']['total'],
                'total_freight': air['freight']['total'],
                'flight_movements': air['operations']['flight_movements']
            },
            'road': {
                'total_vehicles': road['vehicles']['total'],
                'psv_licenses': road['psv']['licenses_issued'],
                'road_fatalities': road['safety']['fatalities']
            },
            'pipeline': {
                'throughput': pipeline['operations']['throughput'],
                'system_uptime': pipeline['operations']['system_uptime']
            }
        }
        
        return jsonify({
            'success': True,
            'data': overview,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kpa')
def get_kpa():
    """Get KPA data"""
    try:
        data = TransportDataService.get_kpa_data()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rail')
def get_rail():
    """Get Kenya Railways data"""
    try:
        data = TransportDataService.get_rail_data()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/air')
def get_air():
    """Get aviation data (KAA/KCAA)"""
    try:
        data = TransportDataService.get_air_data()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/road')
def get_road():
    """Get road transport data (NTSA/KeNHA)"""
    try:
        data = TransportDataService.get_road_data()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pipeline')
def get_pipeline():
    """Get pipeline data (KPC)"""
    try:
        data = TransportDataService.get_pipeline_data()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/<mode>')
def export_data(mode):
    """Export data for a specific transport mode as JSON"""
    try:
        data_map = {
            'kpa': TransportDataService.get_kpa_data,
            'rail': TransportDataService.get_rail_data,
            'air': TransportDataService.get_air_data,
            'road': TransportDataService.get_road_data,
            'pipeline': TransportDataService.get_pipeline_data
        }
        
        if mode not in data_map:
            return jsonify({'success': False, 'error': 'Invalid transport mode'}), 400
        
        data = data_map[mode]()
        return jsonify({
            'success': True,
            'mode': mode,
            'data': data,
            'exported_at': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)