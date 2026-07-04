import config
import json
from datetime import datetime
import elo_calculator

def multi_lane_importer(event, year, connection): #Should be adaptable to other multilane regattas with similar data structure
    result_count = 0
    with open(config.DATA_DIR + "/" + str(year) + event + ".json", 'r') as f:
        data = json.load(f)
    date = data.get("date")
    if not date and event == "1shorr":
        date=datetime(year+1, 3, 20) # SHORR usually happens around late March, so if date is not found in data, set to 20th March of the following year (as SHORR happens in the following academic year)
        date=date.strftime("%Y-%m-%d")
    else:
        date = datetime.strptime(date, "%d-%b-%Y")
        date = date.strftime("%Y-%m-%d")
    cursor = connection.cursor()
    # Insert event into events table
    config_events = config.get_events()
    for config_event in config_events:
        if config_event[0] == event:
            event_name = config_event[1]
            event_type = config_event[2]
    cursor.execute(f"INSERT INTO events (event_name, event_type, course_distance) VALUES ('{event_name}', '{event_type}', 0);")
    cursor.execute("SELECT LAST_INSERT_ID();")
    event_id = cursor.fetchone()[0]
    for section in data.keys():
        if section != "date" and section != "year":
            race_round = "N/A"
            if section == "Time Trial":
                race_round = "Time Trial"
            if "Final" in section and "re-row" in section:
                race_round = "Final " + get_roundletter(section) + " Re-row"
            elif "Final" in section:
                race_round = "Final " + get_roundletter(section)
            elif "Repechage" in section:
                race_round = "Repechage " + get_roundletter(section)
            elif  "Semi-Final" in section or "Semifinal" in section:
                race_round = "Semi-Final " + get_roundletter(section)
            elif "Heat" in section:
                race_round = "Heat " + get_roundletter(section) if get_roundletter(section) else "Heats"
            cursor.execute(f"INSERT INTO races (event_id, race_round, day_of_event) VALUES ({event_id}, '{race_round}', '{date}');")
            cursor.execute("SELECT LAST_INSERT_ID();")
            race_id = cursor.fetchone()[0]
            for results in data[section]:
                result_count += 1
                club_name = results["crew_name"]
                club_name = club_name_strip(club_name)
                position = results["position"]
                if position == "":
                    position = 0
                finish_time = results["finish_time"]
                #Insert club into clubs table if it doesn't exist
                cursor.execute(f"INSERT IGNORE INTO clubs (club_name) VALUES ('{club_name}');")
                cursor.execute(f"SELECT club_id FROM clubs WHERE club_name = '{club_name}';")
                club_id = cursor.fetchone()[0]
                #Calculate GMT percentage if finish time is valid
                gmt_percentage = 0.00
                if finish_time != "N/A":
                    if position == "1":
                        gmt_percentage = 100.00
                        gmt_time = finish_time
                        gmt_parts = gmt_time.split(":")
                        gmt_seconds = int(gmt_parts[0]) * 60 + float(gmt_parts[1])
                        time_seconds = gmt_seconds
                    else:
                        time_parts = finish_time.split(":")
                        time_seconds = int(time_parts[0]) * 60 + float(time_parts[1])
                        gmt_percentage = round((gmt_seconds / time_seconds) * 100, 2)
                else:
                    time_seconds = "0.00"
                query = "INSERT INTO race_results (race_id, club_id, position, time_seconds, gmt_percentage) VALUES (%s, %s, %s, %s, %s)"
                values = (race_id, club_id, position, time_seconds, gmt_percentage)
                cursor.execute(query, values)
            connection.commit()
            #Calculate ELO ratings for each club
            cursor.execute(f"SELECT race_id, club_id, position, time_seconds FROM race_results WHERE race_id = {race_id};")
            race_results = cursor.fetchall()
            # Calculate all new ELOs first using current database values
            new_elos = {}
            for race_id, club_id, position, time_seconds in race_results:
                new_elos[club_id] = elo_calculator.calculate_elo_for_club(cursor, race_id, club_id)
            # Then update all rows
            for club_id, new_elo in new_elos.items():
                cursor.execute("UPDATE race_results SET elo_after = %s WHERE race_id = %s AND club_id = %s", 
                            (new_elo, race_id, club_id))
            connection.commit()
    print(f"            Imported {result_count} results") # Subtract 2 from length of data to account for "date" and "year" keys in JSON file which are not results)  

def henley_importer(year, connection):
        with open(config.DATA_DIR + "/" + str(year) + "3henley" + ".json", 'r') as f:
            data = json.load(f)
        cursor = connection.cursor()
        cursor.execute("INSERT INTO events (event_name, event_type) VALUES ('Henley Royal Regatta', 'Regatta');")
        cursor.execute("SELECT LAST_INSERT_ID();")
        event_id = cursor.fetchone()[0]
        data = sorted(data, key=lambda x: datetime.strptime(x["date"], "%d-%b-%Y"))
        for section in data:
            date = section["date"]
            date = datetime.strptime(date, "%d-%b-%Y")
            date = date.strftime("%Y-%m-%d")
            round = section["stage"].title()
            if round == "Heat": round = "Heats"
            cursor.execute(f"INSERT INTO races (event_id, race_round, day_of_event) VALUES ({event_id}, '{round}', '{date}');")
            cursor.execute("SELECT LAST_INSERT_ID();")
            race_id = cursor.fetchone()[0]
            club_name = club_name_strip(section["winner"])
            cursor.execute(f"INSERT IGNORE INTO clubs (club_name) VALUES ('{club_name}');")
            cursor.execute(f"SELECT club_id FROM clubs WHERE club_name = '{club_name}';")
            club_id = cursor.fetchone()[0]
            finish_time = section["finish_time"]
            time_parts = finish_time.split(":")
            time_seconds = int(time_parts[0]) * 60 + float(time_parts[1])
            cursor.execute(f"INSERT INTO race_results (race_id, club_id, position, time_seconds, gmt_percentage) VALUES ({race_id}, {club_id}, 1, {time_seconds}, 100.00);")
            club_name = club_name_strip(section["loser"])
            cursor.execute(f"INSERT IGNORE INTO clubs (club_name) VALUES ('{club_name}');")
            cursor.execute(f"SELECT club_id FROM clubs WHERE club_name = '{club_name}';")
            club_id_loser = cursor.fetchone()[0]
            cursor.execute(f"INSERT INTO race_results (race_id, club_id, position, time_seconds, gmt_percentage) VALUES ({race_id}, {club_id_loser}, 2, 0, 0);")
            connection.commit()
            elo_after = elo_calculator.calculate_elo_for_club(cursor, race_id, club_id)
            elo_after_loser = elo_calculator.calculate_elo_for_club(cursor, race_id, club_id_loser)
            cursor.execute(f"UPDATE race_results SET elo_after = {elo_after} WHERE race_id = {race_id} AND club_id = {club_id};")
            cursor.execute(f"UPDATE race_results SET elo_after = {elo_after_loser} WHERE race_id = {race_id} AND club_id = {club_id_loser};")
            connection.commit()
        print(f"            Imported {len(data)} races")

def get_roundletter(section):
    split = section.split(" ")
    for i in split:
        if len(i) == 1 and (i.isalpha()or i.isdigit()):
            return i
    
def club_name_strip(club_name):
    for punctuation in "',.?;-":
                    club_name = club_name.replace(punctuation, "")
    club_split = club_name.split(" ")
    club_name = [i for i in club_split if i not in config.CLUB_NAME_REMOVALS and len(i) > 1]
    club_name = [config.CLUB_NAME_REPLACEMENTS.get(i, i) for i in club_name] # Replace any words in club name based on CLUB_NAME_REPLACEMENTS dictionary in config file
    club_name = " ".join(club_name)
    if club_name in config.CLUB_NAME_SWITCHES.keys():
        club_name = config.CLUB_NAME_SWITCHES[club_name]
    return club_name