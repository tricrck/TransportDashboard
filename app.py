from flask import Flask, jsonify, render_template, send_file
from flask_cors import CORS
from datetime import datetime
import pandas as pd
import pickle
from pathlib import Path
import io
import logging
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask setup
app = Flask(__name__)
CORS(app)

# Load pre-processed DataFrames from pickle file
PICKLE_FILE = Path("data/transport_tables_2019_2023.pkl")

try:
    with open(PICKLE_FILE, 'rb') as f:
        DATA = pickle.load(f)
    logger.info(f"Successfully loaded {len(DATA)} DataFrames from pickle file")
    logger.info(f"Available DataFrames: {list(DATA.keys())}")
except Exception as e:
    logger.error(f"Failed to load pickle file: {e}")
    DATA = {}

# Data processing helpers
def safe_divide(numerator, denominator, default=0):
    """Safely divide two numbers, returning default if denominator is 0"""
    try:
        if denominator and denominator != 0:
            return numerator / denominator
        return default
    except:
        return default

def get_latest_year(df):
    """Extract the latest year from DataFrame columns"""
    # Handle different DataFrame structures
    if 'Year' in df.columns:
        # For DataFrames with Year column
        if not df['Year'].empty:
            return int(df['Year'].max())
    
    # For DataFrames with year columns (2019, 2020, etc.)
    year_cols = []
    for col in df.columns:
        if isinstance(col, (int, float)):
            year_cols.append(int(col))
        elif isinstance(col, str) and col.isdigit():
            year_cols.append(int(col))
    
    if year_cols:
        return max(year_cols)
    return 2023  # Default to 2023 if no year found

def extract_value(df, condition_col, condition_value, year_col=None):
    """Extract value based on condition"""
    try:
        # If year_col is provided as int/string, use it directly
        if year_col is not None:
            if year_col not in df.columns and str(year_col) in df.columns:
                year_col = str(year_col)
            
            if condition_col in df.columns and year_col in df.columns:
                # Find rows matching condition
                if condition_value is None:
                    # Get first value if no condition
                    value = df[year_col].iloc[0]
                else:
                    mask = df[condition_col].astype(str).str.contains(str(condition_value), case=False, na=False)
                    if mask.any():
                        value = df.loc[mask, year_col].values[0]
                    else:
                        return 0
                
                if pd.isna(value):
                    return 0
                
                # Try to convert to float
                try:
                    return float(value)
                except (ValueError, TypeError):
                    # If it's a string with commas, remove them
                    if isinstance(value, str):
                        value = value.replace(',', '')
                    try:
                        return float(value)
                    except:
                        return 0
        else:
            # For DataFrames without year columns, get the last value
            if condition_col in df.columns:
                mask = df[condition_col].astype(str).str.contains(str(condition_value), case=False, na=False)
                if mask.any():
                    # Get the last numeric column
                    numeric_cols = []
                    for col in df.columns:
                        if col != condition_col:
                            try:
                                # Try to convert to float
                                _ = float(str(df[col].iloc[0]).replace(',', ''))
                                numeric_cols.append(col)
                            except:
                                pass
                    
                    if numeric_cols:
                        # Sort columns and get the last one
                        numeric_cols.sort()
                        last_col = numeric_cols[-1]
                        value = df.loc[mask, last_col].values[0]
                        
                        if pd.isna(value):
                            return 0
                        
                        try:
                            return float(str(value).replace(',', ''))
                        except:
                            return 0
    except Exception as e:
        logger.warning(f"Error extracting value: {e}")
        return 0
    return 0

def sum_column(df, column_name):
    """Safely sum a column"""
    try:
        if column_name in df.columns:
            return df[column_name].sum()
        return 0
    except:
        return 0

# Transport Data Service (using pre-processed DataFrames)
class TransportDataService:

    @staticmethod
    def get_kpa_data():
        """Get Kenya Ports Authority data"""
        try:
            df_traffic = DATA.get('mombasa_port')
            df_containers = DATA.get('container_traffic')
            
            if df_traffic is None or df_containers is None:
                raise ValueError("Required DataFrames not found")
            
            latest_year = get_latest_year(df_traffic)
            year_str = str(latest_year)
            
            # Extract values from Mombasa Port data
            grand_total = extract_value(df_traffic, 'Category', 'Grand Total', year_str)
            container_traffic = extract_value(df_traffic, 'Category', 'Container Traffic', year_str)
            turnaround = extract_value(df_traffic, 'Category', 'Ships Turnaround Time', year_str)
            ships_docked = extract_value(df_traffic, 'Category', 'Ships Docking', year_str)
            moves_per_hour = extract_value(df_traffic, 'Category', 'Avg Gross Moves Per Ship Per Hour', year_str)
            
            # Extract imports and exports
            imports_total = extract_value(df_traffic, 'Category', 'Total Imports', year_str)
            exports_total = extract_value(df_traffic, 'Category', 'Total Exports', year_str)
            
            # Extract transit traffic
            transit_in = extract_value(df_traffic, 'Category', 'Imports - Of which: Transit In', year_str)
            transit_out = extract_value(df_traffic, 'Category', 'Exports - Of which: Transit Out', year_str)
            
            # Monthly container trend
            monthly_trend = []
            if year_str in df_containers.columns:
                for idx, row in df_containers.iterrows():
                    month = str(row['Month'])
                    if month != 'TOTAL' and month != 'Total' and pd.notna(month):
                        containers = extract_value(df_containers, 'Month', month, year_str)
                        monthly_trend.append({
                            "month": month,
                            "containers": containers / 1000  # Convert to K TEUs
                        })
            else:
                # If no year column, use the last column
                last_col = df_containers.columns[-1]
                for idx, row in df_containers.iterrows():
                    month = str(row['Month'])
                    if month != 'TOTAL' and month != 'Total' and pd.notna(month):
                        containers = float(row[last_col]) if pd.notna(row[last_col]) else 0
                        monthly_trend.append({
                            "month": month,
                            "containers": containers / 1000  # Convert to K TEUs
                        })
            
            # Summary statistics
            summary_stats = {
                "cargo_throughput": grand_total / 1000,  # Convert to M MT
                "container_traffic": container_traffic / 1000000,  # Convert to M TEUs
                "vessel_turnaround": turnaround,
                "ships_docked": ships_docked,
                "moves_per_hour": moves_per_hour,
                "imports_total": imports_total,
                "exports_total": exports_total,
                "transit_total": transit_in + transit_out,
                "year": latest_year
            }
            
            return {
                "summary": summary_stats,
                "monthly_trend": monthly_trend,
                "source": "KNBS Economic Survey 2024 – Tables 13.8 & 13.19",
            }
        except Exception as e:
            logger.error(f"Error loading KPA data: {e}")
            raise

    @staticmethod
    def get_rail_data():
        """Get Kenya Railways Corporation data"""
        try:
            df_sgr = DATA.get('sgr_traffic')
            df_mgr = DATA.get('mgr_traffic')
            
            if df_sgr is None or df_mgr is None:
                raise ValueError("Required DataFrames not found")
            
            latest_year = get_latest_year(df_sgr)
            year_str = str(latest_year)
            
            # SGR data - need to adjust column names
            sgr_passengers = 0
            sgr_cargo = 0
            sgr_revenue = 0
            
            # Try different column names for SGR
            passenger_cols = ['Passenger numbers', 'Passenger numbers (000)', 'Passenger']
            cargo_cols = ['Tonnes', 'Tonnes (000)', 'Cargo']
            revenue_cols = ['Revenue', 'Revenue (KSh Million)', 'Revenue (KSh)']
            
            for col in passenger_cols:
                sgr_passengers = extract_value(df_sgr, 'Metric', col, year_str)
                if sgr_passengers > 0:
                    break
            
            for col in cargo_cols:
                sgr_cargo = extract_value(df_sgr, 'Metric', col, year_str)
                if sgr_cargo > 0:
                    break
            
            for col in revenue_cols:
                sgr_revenue = extract_value(df_sgr, 'Metric', col, year_str)
                if sgr_revenue > 0:
                    break
            
            # MGR data
            mgr_passengers = extract_value(df_mgr, 'Metric', 'Passenger', year_str)
            mgr_cargo = extract_value(df_mgr, 'Metric', 'Tonnes', year_str)
            mgr_revenue = extract_value(df_mgr, 'Metric', 'Revenue (KSh Million)', year_str)
            
            # Get previous year data for growth calculation
            prev_year = latest_year - 1
            prev_year_str = str(prev_year)
            
            sgr_passengers_prev = extract_value(df_sgr, 'Metric', 'Passenger numbers', prev_year_str)
            mgr_passengers_prev = extract_value(df_mgr, 'Metric', 'Passenger', prev_year_str)
            sgr_cargo_prev = extract_value(df_sgr, 'Metric', 'Tonnes', prev_year_str)
            mgr_cargo_prev = extract_value(df_mgr, 'Metric', 'Tonnes', prev_year_str)
            
            # Summary statistics
            summary_stats = {
                "total_passengers": sgr_passengers + mgr_passengers,
                "total_cargo": sgr_cargo + mgr_cargo,
                "total_revenue": sgr_revenue + mgr_revenue,
                "sgr_passengers": sgr_passengers,
                "sgr_cargo": sgr_cargo,
                "sgr_revenue": sgr_revenue,
                "mgr_passengers": mgr_passengers,
                "mgr_cargo": mgr_cargo,
                "mgr_revenue": mgr_revenue,
                "passenger_growth": safe_divide(
                    (sgr_passengers + mgr_passengers) - (sgr_passengers_prev + mgr_passengers_prev),
                    sgr_passengers_prev + mgr_passengers_prev
                ) * 100,
                "cargo_growth": safe_divide(
                    (sgr_cargo + mgr_cargo) - (sgr_cargo_prev + mgr_cargo_prev),
                    sgr_cargo_prev + mgr_cargo_prev
                ) * 100,
                "year": latest_year
            }
            
            return {
                "sgr": {
                    "passengers": sgr_passengers / 1000,  # Convert to thousands
                    "cargo": sgr_cargo / 1000,  # Convert to thousands
                    "revenue": sgr_revenue
                },
                "mgr": {
                    "passengers": mgr_passengers / 1000,  # Convert to thousands
                    "cargo": mgr_cargo / 1000,  # Convert to thousands
                    "revenue": mgr_revenue
                },
                "combined": summary_stats,
                "source": "KNBS Economic Survey 2024 – Table 13.7",
            }
        except Exception as e:
            logger.error(f"Error loading rail data: {e}")
            raise

    @staticmethod
    def get_air_data():
        """Get Kenya Aviation Authority data"""
        try:
            df_passengers = DATA.get('passenger_traffic')
            df_cargo = DATA.get('cargo_mail')
            df_movements = DATA.get('aircraft_movement')
            
            if df_passengers is None or df_cargo is None or df_movements is None:
                raise ValueError("Required DataFrames not found")
            
            latest_year = get_latest_year(df_passengers)
            
            # Filter for latest year
            df_passengers_latest = df_passengers[df_passengers['Year'] == latest_year]
            df_cargo_latest = df_cargo[df_cargo['Year'] == latest_year]
            
            # Passenger data - sum across all categories
            total_passengers = 0
            if not df_passengers_latest.empty:
                # Sum Total_Passenger_Traffic for Sub-Total and In Transit categories
                domestic_mask = (df_passengers_latest['Category'] == 'Domestic') & (df_passengers_latest['Sub_Category'] == 'Sub-Total')
                international_mask = (df_passengers_latest['Category'] == 'International') & (df_passengers_latest['Sub_Category'] == 'Sub-Total')
                transit_mask = (df_passengers_latest['Category'] == 'Total') & (df_passengers_latest['Sub_Category'] == 'In Transit')
                
                domestic_total = df_passengers_latest.loc[domestic_mask, 'Total_Passenger_Traffic'].sum()
                international_total = df_passengers_latest.loc[international_mask, 'Total_Passenger_Traffic'].sum()
                in_transit = df_passengers_latest.loc[transit_mask, 'Total_Passenger_Traffic'].sum()
                
                total_passengers = domestic_total + international_total + in_transit
            
            # Cargo data - filter for Total category
            total_cargo = 0
            if not df_cargo_latest.empty:
                total_mask = (df_cargo_latest['Category'] == 'Total')
                total_cargo = df_cargo_latest.loc[total_mask, 'Cargo_Total'].sum()
            
            # Movement data
            year_str = str(latest_year)
            total_movements = extract_value(df_movements, 'Movement', 'Grand Total', year_str)
            domestic_movements = extract_value(df_movements, 'Movement', 'Total', year_str)
            # For domestic, need to filter by Type first
            df_domestic = df_movements[df_movements['Type'] == 'Domestic']
            df_international = df_movements[df_movements['Type'] == 'International']
            domestic_movements = extract_value(df_domestic, 'Movement', 'Total', year_str)
            international_movements = extract_value(df_international, 'Movement', 'Total', year_str)
            
            # Airport breakdown
            jkia_passengers = df_passengers_latest['JKIA'].sum() if not df_passengers_latest.empty else 0
            mia_passengers = df_passengers_latest['MIA'].sum() if not df_passengers_latest.empty else 0
            other_airports_passengers = df_passengers_latest['Other_Airports'].sum() if not df_passengers_latest.empty else 0
            
            # Summary statistics
            summary_stats = {
                "total_passengers": total_passengers,
                "domestic_passengers": domestic_total,
                "international_passengers": international_total,
                "transit_passengers": in_transit,
                "total_cargo": total_cargo,
                "total_movements": total_movements,
                "domestic_movements": domestic_movements,
                "international_movements": international_movements,
                "jkia_passengers": jkia_passengers,
                "mia_passengers": mia_passengers,
                "other_airports_passengers": other_airports_passengers,
                "year": latest_year
            }
            
            return {
                "passengers": {
                    "total": total_passengers / 1000,  # Convert to millions
                    "domestic": domestic_total / 1000,
                    "international": international_total / 1000,
                    "transit": in_transit / 1000
                },
                "cargo": {
                    "total": total_cargo
                },
                "movements": {
                    "total": total_movements,
                    "domestic": domestic_movements,
                    "international": international_movements
                },
                "airports": {
                    "jkia": jkia_passengers / 1000,
                    "mia": mia_passengers / 1000,
                    "other": other_airports_passengers / 1000
                },
                "summary": summary_stats,
                "source": "KNBS Economic Survey 2024 – Tables 13.12–13.14",
            }
        except Exception as e:
            logger.error(f"Error loading air data: {e}")
            raise

    @staticmethod
    def get_road_data():
        """Get NTSA/KeNHA road transport data"""
        try:
            df_vehicles = DATA.get('vehicle_registration')
            df_licenses = DATA.get('road_licenses')
            df_accidents = DATA.get('road_accidents')
            
            if df_vehicles is None or df_licenses is None or df_accidents is None:
                raise ValueError("Required DataFrames not found")
            
            latest_year = get_latest_year(df_vehicles)
            year_str = str(latest_year)
            
            # Vehicle registration
            total_vehicles = extract_value(df_vehicles, 'Vehicle_Type', 'Total Units Registered', year_str)
            motor_vehicles = extract_value(df_vehicles, 'Vehicle_Type', 'Total Motor Vehicles', year_str)
            motor_cycles = extract_value(df_vehicles, 'Vehicle_Type', 'Total Motor Cycles', year_str)
            
            # Licenses
            psv_licenses = extract_value(df_licenses, 'Type', 'Total', year_str)
            # Adjust for PSV Licenses category
            df_psv = df_licenses[df_licenses['Category'] == 'PSV Licenses']
            psv_licenses = extract_value(df_psv, 'Type', 'Total', year_str)
            
            df_driving = df_licenses[df_licenses['Category'] == 'Driving Licenses']
            driving_licenses = extract_value(df_driving, 'Type', 'Total', year_str)
            
            # Accidents
            total_accidents = extract_value(df_accidents, 'Category', 'Total Number of Reported Traffic Accidents', year_str)
            fatalities = extract_value(df_accidents, 'Category', 'Of which: Killed', year_str)
            injuries = extract_value(df_accidents, 'Category', 'Persons Killed or Injured', year_str)
            serious_injuries = extract_value(df_accidents, 'Category', 'Of which: Seriously Injured', year_str)
            slight_injuries = extract_value(df_accidents, 'Category', 'Of which: Slightly Injured', year_str)
            
            # Summary statistics
            summary_stats = {
                "total_vehicles": total_vehicles,
                "motor_vehicles": motor_vehicles,
                "motor_cycles": motor_cycles,
                "psv_licenses": psv_licenses,
                "driving_licenses": driving_licenses,
                "total_accidents": total_accidents,
                "fatalities": fatalities,
                "total_injuries": injuries,
                "serious_injuries": serious_injuries,
                "slight_injuries": slight_injuries,
                "fatality_rate": safe_divide(fatalities, total_accidents, 0) * 100,
                "casualties_per_accident": safe_divide(injuries, total_accidents, 0),
                "year": latest_year
            }
            
            return {
                "vehicles": {
                    "total": total_vehicles / 1000000,  # Convert to millions
                    "motor_vehicles": motor_vehicles / 1000,  # Convert to thousands
                    "motor_cycles": motor_cycles / 1000  # Convert to thousands
                },
                "licenses": {
                    "psv": psv_licenses,
                    "driving": driving_licenses
                },
                "safety": summary_stats,
                "source": "KNBS Economic Survey 2024 – Tables 13.4–13.6",
            }
        except Exception as e:
            logger.error(f"Error loading road data: {e}")
            raise

    @staticmethod
    def get_pipeline_data():
        """Get Kenya Pipeline Company data"""
        try:
            df_pipeline = DATA.get('pipeline_throughput')
            
            if df_pipeline is None:
                raise ValueError("Pipeline DataFrame not found")
            
            latest_year = get_latest_year(df_pipeline)
            year_str = str(latest_year)
            
            # Extract values
            grand_total = extract_value(df_pipeline, 'Category', 'Grand Total', year_str)
            transit_total = extract_value(df_pipeline, 'Category', 'Transit - Sub-Total', year_str)
            domestic_total = extract_value(df_pipeline, 'Category', 'Domestic Consumption - Sub-Total', year_str)
            
            # Product breakdown - need to filter by Transit_Domestic column
            df_transit = df_pipeline[df_pipeline['Transit_Domestic'] == 'Transit']
            df_domestic = df_pipeline[df_pipeline['Transit_Domestic'] == 'Domestic']
            
            motor_spirit_transit = extract_value(df_transit, 'Product_Type', 'Motor Spirit', year_str)
            motor_spirit_domestic = extract_value(df_domestic, 'Product_Type', 'Motor Spirit', year_str)
            motor_spirit = motor_spirit_transit + motor_spirit_domestic
            
            kerosene_transit = extract_value(df_transit, 'Product_Type', 'Kerosene', year_str)
            kerosene_domestic = extract_value(df_domestic, 'Product_Type', 'Kerosene', year_str)
            kerosene = kerosene_transit + kerosene_domestic
            
            light_diesel_transit = extract_value(df_transit, 'Product_Type', 'Light Diesel', year_str)
            light_diesel_domestic = extract_value(df_domestic, 'Product_Type', 'Light Diesel', year_str)
            light_diesel = light_diesel_transit + light_diesel_domestic
            
            jet_fuel_transit = extract_value(df_transit, 'Product_Type', 'Jet Fuel', year_str)
            jet_fuel_domestic = extract_value(df_domestic, 'Product_Type', 'Jet Fuel', year_str)
            jet_fuel = jet_fuel_transit + jet_fuel_domestic
            
            # Get previous year for growth calculation
            prev_year = latest_year - 1
            prev_year_str = str(prev_year)
            grand_total_prev = extract_value(df_pipeline, 'Category', 'Grand Total', prev_year_str)
            
            # Summary statistics
            summary_stats = {
                "total_throughput": grand_total,
                "transit": transit_total,
                "domestic": domestic_total,
                "transit_percentage": safe_divide(transit_total, grand_total, 0) * 100,
                "domestic_percentage": safe_divide(domestic_total, grand_total, 0) * 100,
                "motor_spirit": motor_spirit,
                "kerosene": kerosene,
                "light_diesel": light_diesel,
                "jet_fuel": jet_fuel,
                "growth_rate": safe_divide(grand_total - grand_total_prev, grand_total_prev, 0) * 100,
                "year": latest_year
            }
            
            return {
                "operations": {
                    "throughput": grand_total / 1000,  # Convert to thousands
                    "transit": transit_total / 1000,
                    "domestic": domestic_total / 1000,
                    "transit_percentage": summary_stats["transit_percentage"],
                    "domestic_percentage": summary_stats["domestic_percentage"]
                },
                "products": {
                    "motor_spirit": motor_spirit / 1000,
                    "kerosene": kerosene / 1000,
                    "light_diesel": light_diesel / 1000,
                    "jet_fuel": jet_fuel / 1000
                },
                "summary": summary_stats,
                "source": "KNBS Economic Survey 2024 – Table 13.11",
            }
        except Exception as e:
            logger.error(f"Error loading pipeline data: {e}")
            raise

# API endpoints

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/overview")
def get_overview():
    try:
        kpa = TransportDataService.get_kpa_data()
        rail = TransportDataService.get_rail_data()
        air = TransportDataService.get_air_data()
        road = TransportDataService.get_road_data()
        pipeline = TransportDataService.get_pipeline_data()

        overview = {
            "sea": {
                "cargo_throughput": kpa["summary"]["cargo_throughput"],
                "container_traffic": kpa["summary"]["container_traffic"],
                "ships_docked": kpa["summary"]["ships_docked"],
                "year": kpa["summary"].get("year", 2023)
            },
            "rail": {
                "total_passengers": rail["combined"]["total_passengers"] / 1000,  # Already in thousands, convert to proper units
                "total_cargo": rail["combined"]["total_cargo"] / 1000,  # Already in thousands, convert to proper units
                "total_revenue": rail["combined"]["total_revenue"],
                "year": rail["combined"].get("year", 2023)
            },
            "air": {
                "total_passengers": air["passengers"]["total"],
                "total_freight": air["cargo"]["total"],
                "flight_movements": air["movements"]["total"],
                "year": air["summary"].get("year", 2023)
            },
            "road": {
                "total_vehicles": road["vehicles"]["total"],
                "psv_licenses": road["licenses"]["psv"],
                "road_fatalities": road["safety"]["fatalities"],
                "total_accidents": road["safety"]["total_accidents"],
                "year": road["safety"].get("year", 2023)
            },
            "pipeline": {
                "throughput": pipeline["operations"]["throughput"],
                "domestic_consumption": pipeline["operations"]["domestic"],
                "transit_percentage": pipeline["operations"]["transit_percentage"],
                "year": pipeline["summary"].get("year", 2023)
            },
            "sources": {
                "sea": kpa.get("source", ""),
                "rail": rail.get("source", ""),
                "air": air.get("source", ""),
                "road": road.get("source", ""),
                "pipeline": pipeline.get("source", "")
            }
        }

        return jsonify({
            "success": True,
            "data": overview,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error in overview endpoint: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/<mode>")
def get_mode(mode):
    try:
        services = {
            "kpa": TransportDataService.get_kpa_data,
            "rail": TransportDataService.get_rail_data,
            "air": TransportDataService.get_air_data,
            "road": TransportDataService.get_road_data,
            "pipeline": TransportDataService.get_pipeline_data,
        }

        if mode not in services:
            return jsonify({"success": False, "error": "Invalid mode"}), 400

        data = services[mode]()
        return jsonify({
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error in {mode} endpoint: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/health")
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "dataframes_loaded": len(DATA),
        "available_dataframes": list(DATA.keys()),
        "timestamp": datetime.now().isoformat()
    })

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)