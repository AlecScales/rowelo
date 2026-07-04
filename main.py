"""
Main management script for RowELO.
Handles database setup, scraping, data import, and HTML generation.
"""
import importer
import mysql.connector
import config
import create_database
import os
import htmlgen
import importlib

def main():
    # Check if database exists
    print("1. Creating database")
    connection = connect(False) # Connect to MySQL server without specifying database, so we can check if database exists and create it if not
    if connection is None:
        print("         Failed to connect to database. Please check your database configuration in config.py and ensure that MySQL server is running.")
        return
    create_database.main(connection)
    connection.close() # Close connection to MySQL server, as we will reconnect later with database specified after creating database if it does not exist
    connection = connect() # Connect to MySQL server with database specified, so we can import data into database and generate HTML pages
    datadir = os.getcwd() + "/" + config.DATA_DIR
    print(f"      Data directory set to {datadir}")
    start_year = config.get_current_season()['year']
    end_year = start_year + config.get_current_season()['years_covered']
    print("2. Scraping events")
    scrape_events(datadir,start_year, end_year)
    print("      All events scraped")
    propagate_tables(connection,datadir,start_year, end_year)
    print("3. Generating HTML pages")
    htmlgen.main(connection,start_year, end_year)
    print("WEBSITE GENERATED SUCCESSFULLY")

def connect(dbconnection=True):
    dbconfig = config.get_db_config()
    try:
        connection = mysql.connector.connect(
            host=dbconfig['host'],
            user=dbconfig['user'],
            password=dbconfig['password'],
            database=dbconfig['database'] if dbconnection else None
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

def check_database_exists(connection):
    dbconfig = config.get_db_config()
    if connection is None:
        return False
    cursor = connection.cursor()
    cursor.execute(f"SHOW DATABASES LIKE '{dbconfig['database']}'")
    return cursor.fetchone() is not None
    
def scrape_events(datadir,start_year, end_year):
    os.makedirs(datadir, exist_ok=True)
    print("      Data directory created")
    dir_files = os.listdir(datadir)
    tempfilejoin = "".join(dir_files)
    events = config.get_events()
    count = 1
    for event_code,event_name,_ in events:
        for year in range(start_year, end_year):
            if str(year) + event_code not in tempfilejoin: # Check if file for event already exists in data folder, if so skip scraping for that event
                # Imports scraper for event based on event name in config file
                print(f"      {count}. Scraping data for {event_name} {year}/{year+1} Season")
                count += 1
                command = f"scraper_{event_code}"
                scraper = importlib.import_module(command)
                scraper.main(year,datadir) # Run scraper function to scrape data and save to JSON file in data folder

def propagate_tables(connection,datadir,start_year,end_year):
    print("3. Importing data into database")
    # Checks if JSON files for each event have been imported yet, if not imports importer for that event and runs it to import data into database
    dir_files = os.listdir(datadir)
    dir_files.sort() # Sort files in data folder, to ensure importers are run in correct order (e.g. SHORR before NSR, as SHORR happens earlier in the year and some NSR data may be missing dates, so we can use SHORR date for those
    events = config.get_events()
    cursor = connection.cursor()
    cursor.execute("SELECT e.event_name, MIN(r.day_of_event) FROM events e JOIN races r ON e.event_id = r.event_id GROUP BY e.event_id")
    result = cursor.fetchall()
    count = 1
    for file in dir_files:
            for i in range(start_year, end_year):
                if str(i) in file: # Only check files for current season, as we may not have data for all events for previous seasons, and we want to avoid trying to import incomplete data
                    for event_code, event_name, _ in events:
                        already_imported = False
                        for result_event_name, day in result:
                            already_imported = False
                            if day.month > 8:
                                if event_name == result_event_name and i == day.year:
                                    already_imported = True
                                    break
                            else:
                                if event_name == result_event_name and i == day.year - 1:
                                    already_imported = True
                                    break
                        if str(i) + event_code in file and not already_imported: # Check if file for event exists in data folder, and if has not yet been imported into the database
                            print(f"      {count}. Importing data for {event_name} {i}/{i+1} Season")
                            if event_code == "2nsr" or event_code == "1shorr": # Currently only have importers for NSR and SHORR, so only run for those events
                                importer.multi_lane_importer(event_code, i, connection) # Run importer function to import data from JSON file into database
                            else:
                                importer_name = event_code[1:] # Get event name without the leading number (e.g. "nsr" from "2nsr")
                                getattr(importer, f"{importer_name}_importer")(i, connection) # Run importer function to import data from JSON file into database
                            count += 1
if __name__ == '__main__':
    main()