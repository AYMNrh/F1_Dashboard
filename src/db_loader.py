import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
import time
import psycopg2

def test_connection():
    load_dotenv()
    
    # Test direct connection first
    try:
        print("Attempting connection with these parameters:")
        print(f"Host: {os.getenv('DB_HOST')}")
        print(f"Port: {os.getenv('DB_PORT')}")
        print(f"Database: {os.getenv('DB_NAME')}")
        print(f"User: {os.getenv('DB_USER')}")
        
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )
        print("Direct connection successful!")
        conn.close()
        return True
    except Exception as e:
        print(f"Direct connection failed: {str(e)}")
        print(f"Error type: {type(e)}")
        return False

def wait_for_db(engine, max_attempts=5):
    for attempt in range(max_attempts):
        try:
            with engine.connect() as conn:
                return True
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_attempts}: Database not ready yet... Error: {str(e)}")
            time.sleep(2)
    return False

def load_data():
    # Test connection first
    if not test_connection():
        print("Failed to establish basic connection. Exiting...")
        return
        
    # Load environment variables
    load_dotenv()
    
    # Create database connection
    db_params = {
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT'),
        'database': os.getenv('DB_NAME')
    }
    
    print("Creating SQLAlchemy engine...")
    connection_url = f"postgresql://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_params['database']}"
    print(f"Connection URL (without password): {connection_url.replace(db_params['password'], '****')}")
    
    engine = create_engine(connection_url, 
                         connect_args={'connect_timeout': 10})
    
    # Wait for database to be ready
    if not wait_for_db(engine):
        print("Could not connect to database after multiple attempts")
        return

    # Define loading order based on dependencies
    data_files = {
        'seasons': 'data/seasons.csv',
        'circuits': 'data/circuits.csv',
        'constructors': 'data/constructors.csv',
        'drivers': 'data/drivers.csv',
        'status': 'data/status.csv',
        'races': 'data/races.csv',
        'constructor_results': 'data/constructor_results.csv',
        'constructor_standings': 'data/constructor_standings.csv',
        'driver_standings': 'data/driver_standings.csv',
        'qualifying': 'data/qualifying.csv',
        'results': 'data/results.csv',
        'lap_times': 'data/lap_times.csv',
        'pit_stops': 'data/pit_stops.csv'
    }
    
    # Load into database in order
    for table, file in data_files.items():
        if os.path.exists(file):
            print(f"\nProcessing {table}...")
            try:
                print(f"Reading {file}...")
                df = pd.read_csv(file)
                print(f"Found {len(df)} rows")
                
                # Convert column names to lowercase
                df.columns = df.columns.str.lower()
                print(f"Columns: {', '.join(df.columns)}")
                
                print(f"Loading {table} into database...")
                df.to_sql(table, engine, if_exists='append', index=False)
                print(f"Successfully loaded {table}!")
                
                # Verify the data
                result = pd.read_sql(f"SELECT COUNT(*) as count FROM {table}", engine)
                print(f"Verified {result['count'].iloc[0]} rows in database")
                
            except Exception as e:
                print(f"Error loading {table}: {str(e)}")
                print("Full error:", e.__class__.__name__)
                if hasattr(e, 'orig'):
                    print("Original error:", e.orig)
        else:
            print(f"Warning: {file} not found, skipping...")

if __name__ == "__main__":
    load_data() 