"""
Creates the MySQL database and all required tables (clubs, events, races, race_results) for RowELO.
"""

import mysql.connector
from mysql.connector import Error
from config import get_db_config, DB_NAME
import os

def main(connection):
    config = get_db_config()
    try:
        print(f"            Connecting to MySQL at {config['host']}")
        cursor = connection.cursor()
        # Create database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        if cursor.rowcount == 0:
            print(f"            Database {DB_NAME} already exists")
        else:
            print(f"            Database {DB_NAME} created successfully")
        cursor.execute(f"USE {DB_NAME}")
        print("            Database created")
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clubs (
                club_id INT PRIMARY KEY AUTO_INCREMENT,
                club_name VARCHAR(100) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id    INT PRIMARY KEY AUTO_INCREMENT,
                event_name VARCHAR(200) NOT NULL,
                event_type VARCHAR(10) NOT NULL,
                course_distance INT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS races (
                race_id INT PRIMARY KEY AUTO_INCREMENT,
                event_id INT NOT NULL,
                race_round VARCHAR(20) NOT NULL,
                day_of_event DATE NULL,
                FOREIGN KEY (event_id) REFERENCES events(event_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS race_results (
                result_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                result_id INT PRIMARY KEY AUTO_INCREMENT,
                race_id INT NOT NULL,
                club_id INT NOT NULL,
                position INT NOT NULL,
                time_seconds FLOAT NULL,
                gmt_percentage DECIMAL(5,2) NULL,
                elo_after INT NULL,
                FOREIGN KEY (race_id) REFERENCES races(race_id),
                FOREIGN KEY (club_id) REFERENCES clubs(club_id),
                UNIQUE KEY unique_race_club (race_id, club_id)
            )
        """)
        connection.commit()
        cursor.close()
        connection.close()
        print("            Tables created successfully")  
    except Error as e:
        print(f"\nError: {e}")