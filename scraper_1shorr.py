'''
Scrapes Schools Head of the River data from rowresults.co.uk, combines the Championship Eights (Ch 8+) and School 1st Eights (Sch 1st 8+) events into a single list of results with unified positions, and saves the data to a JSON file.'''

import requests
import bs4
import json

def scrape_schools_head(year):
    url = f"https://www.rowresults.co.uk/shorr{year}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()  # Check for HTTP errors
        soup = bs4.BeautifulSoup(response.content, 'html.parser')
        # Combine both events into one with unified positions
        combined_data = combine_events(soup)
        return {
            'year': f"20{year}",
            'Combined Championship Eights (Ch 8+ & Sch 1st 8+)': combined_data
        }
    except Exception as e:
        print(f"        Error scraping Schools Head 20{year}: {e}")
        return None


def get_event_crews(soup, event_name):
    crews = []
    # Find the table containing this event
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            first_td = row.find('td')
            if first_td:
                event_text = first_td.get_text().strip()
                # Match exact event name (not "G Ch 8+")
                if event_name in event_text and not event_text.startswith("G "):
                    # Extract crew data from this row
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        # Crew name is in the third cell (index 2)
                        crew_name = cells[2].get_text().strip()
                        # Time is in the fifth cell (index 4)
                        finish_time = cells[4].get_text().strip() if len(cells) > 4 else "N/A"
                        # Original position from the event
                        original_position = cells[-1].get_text().strip()
                        crews.append({
                            'original_position': original_position,
                            'crew_name': crew_name,
                            'finish_time': finish_time,
                            'original_event': event_name
                        })
    
    return crews


def remove_duplicate_schools(ch_crews, sch_crews):
    # Create a set of school names that appear in Ch 8+
    ch_schools = set()
    for crew in ch_crews:
        # Extract base school name (remove common suffixes for better matching)
        school_name = crew['crew_name'].strip()
        ch_schools.add(school_name.lower())
    # Filter Sch 1st 8+ crews, keeping only those not in Ch 8+
    filtered_sch_crews = []
    for crew in sch_crews:
        school_name = crew['crew_name'].strip()
        if school_name.lower() not in ch_schools:
            filtered_sch_crews.append(crew)
    return filtered_sch_crews


def combine_events(soup):
    all_crews = []
    # Get crews from Ch 8+ first
    print(f"            Processing Ch 8+...")
    ch_crews = get_event_crews(soup, "Ch 8+")
    print(f"                Found {len(ch_crews)} crews")
    # Get crews from Sch 1st 8+
    print(f"            Processing Sch 1st 8+...")
    sch_crews = get_event_crews(soup, "Sch 1st 8+")
    print(f"                Found {len(sch_crews)} crews")
    # Remove duplicate schools from Sch 1st 8+
    sch_crews_filtered = remove_duplicate_schools(ch_crews, sch_crews)
    # Combine all crews
    all_crews = ch_crews + sch_crews_filtered
    # Sort by finish time (fastest first)
    all_crews.sort(key=lambda x: time_to_seconds(x['finish_time']))
    # Assign unified positions based on finish time order
    for i, crew in enumerate(all_crews, 1):
        crew['position'] = str(i)
    print(f"            Total combined crews: {len(all_crews)}")
    return all_crews


def main(year,datadir):
    # Set the year you want to scrape   
    file =  datadir + "/" + str(year) + "1shorr.json"
    year += -1999  # As SHORR happens in 2025, but in the 2024 academic year, and we need last two digits of year for url 
    data = scrape_schools_head(year)
    if data:
        # Save data to JSON file
        with open(file, 'w') as f:
            json.dump(data, f, indent=2)
    else:
        print("         Failed to scrape data")

def time_to_seconds(time_str):
    minutes, seconds = time_str.split(':')
    return int(minutes) * 60 + float(seconds)