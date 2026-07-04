# RowELO Configuration Master File
# Contains all important configuration settings for the RowELO project

#=====Database configuration=====
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = '123'
DB_NAME = 'rowelo_db'

#=====ELO configuration=====
DEFAULT_ELO = 1500
K_FACTOR = 32

#=====Season/Year configuration=====
YEAR = 2020  # Starting year of first season. Only tested with year > 2020, as web scraping relies on websites keeping past results pages online, and in the same format as they are currently.
YEARS_COVERED = 5
SEASON_START_MONTH = 9

#=====Events=====
events = [["2nsr","National Schools Regatta","Regatta"], ["1shorr","Schools Head","Head"], ["3henley","Henley Royal Regatta","Regatta"]] # List of events to scrape and include in database. Must be lowercase and match the event names used in scraper and importer file names (e.g. "shorr" for scraper_shorr_v2.py and shorr_importer.py)

#=====Club name cleaning=====
CLUB_NAME_REMOVALS = ["BC", "RC", "Rowing", "Boat", "School", "College", "University", "Club", "Sch", "Coll", "Univ", "The","Royal","Ireland","GS","(IRL)","Habs","Haberdashers"] # List of words to remove from club names when importing into database, to help with club name consistency (e.g. "Eton College" and "Eton" will both be imported as "Eton")
CLUB_NAME_REPLACEMENTS = {"Rdg":"Reading", "Gt":"Great", "Sc":"Scullers"} # Dictionary of specific club name replacements to make when importing into database, to help with club name consistency (e.g. "Rdg" will be replaced with "Reading")
CLUB_NAME_SWITCHES = {"Chester":"Royal Chester"}
CLUB_NAME_INTERNATIONAL_TAGS = ["IRL","ITA","USA","Australia","Zealand","Germany","France"] # List of tags to identify international clubs. Clubs containing these tags are excluded from the UK only league table

#=====File paths=====
DATA_DIR = 'data'

def get_db_config():
    return {
        'host': DB_HOST,
        'user': DB_USER,
        'password': DB_PASSWORD,
        'database': DB_NAME,
        'auth_plugin': 'mysql_native_password'
    }

def get_current_season():
    return {
        'year': YEAR,
        'years_covered': YEARS_COVERED
    }

def get_events():
    return events