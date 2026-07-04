"""
Scrapes National Schools' Regatta Open 8+ data from regatta.time-team.nl.
"""

from requests_html import AsyncHTMLSession
import bs4
import json
import re
import asyncio


async def scrape_open_8_data(base_url, year):
    session = AsyncHTMLSession()
    events_page_url = f"{base_url}/events.php"
    try:
        # Fetch and render the events page
        print("             Fetching events page...")
        r = await session.get(events_page_url)
        # Parse HTML content
        soup = bs4.BeautifulSoup(r.html.html, 'html.parser')
        # Find the Open 8+ event URL (needed as event page urls differ every year)
        open_8_url = find_open_8_url(soup, base_url)
        if not open_8_url:
            print("             Open 8+ event not found")
            await session.close()
            return None
        # Find the date for the Open 8+ event
        open_8_date = find_open_8_date(soup, year)
        # Scrape the Open 8+ event page
        print("             Scraping Open 8+ event page...")
        open_8_data = await scrape_event_page(session, open_8_url, open_8_date)
        await session.close()
        return open_8_data
    except Exception as e:
        print(f"            Error scraping Open 8+ data: {e}")
        await session.close()
        return None

def find_open_8_url(soup, base_url): # Find the URL for the Open 8+ event of a certain year
    # Look for "Ch 8+ (Open)" in all tables
    tables = soup.find_all('table', {'class': 'timeteam'})
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            # Look for the anchor tag that contains "Ch 8+ (Open)"
            link = row.find('a', string=lambda text: text and ('Ch 8+' in text and 'G' not in text and 'NonCh' not in text))
            if link:
                href = link.get('href')
                href = base_url + "/" + href
                return href    
    return None

def find_open_8_date(soup, year):
    # Find all date headers and their following tables
    current_date = None
    for element in soup.find_all(['h3', 'h4', 'table']): # NSR uses h4 for dates
        if element.name == 'h4':
            date_text = element.get_text().strip()
            date_match = re.search(r'(\d+)\s+(\w+)', date_text) # Looks for date pattern
            if date_match:
                day, month = date_match.groups()
                current_date = f"{day}-{month}-{year}"
        elif element.name == 'table' and 'timeteam' in element.get('class', []):
            # Check if this table contains Open 8+, as National Schools runs over multiple days
            if current_date and element.find('a', string=lambda text: text and ('Ch 8+' in text and 'G' not in text and 'NonCh' not in text)):
                return current_date

async def scrape_event_page(session, event_url, date):
    try:
        r = await session.get(event_url)
        await r.html.arender()
        soup = bs4.BeautifulSoup(r.html.html, 'html.parser')
        # Extract all sections (Time Trial, FA Final, FB Final, etc.)
        sections, results_found = extract_all_sections(soup)
        print(f"             Found {results_found} results")
        # Add date to the event data
        dict = {'date': date}
        for section in sections:
            dict[section['event_name']] = section['crews']
        return dict
    except Exception as e:
        print(f"        Error scraping event page {event_url}: {e}")
        return None

def extract_all_sections(soup):
    sections = []
    results_found = 0
    # Find all tables and their preceding headers to identify sections
    current_section = "Time Trial"  # Default section
    # Get all elements that might indicate sections
    all_elements = soup.find_all(['h2','table'])
    for element in all_elements:
        if element.name in ['h2']:
            header_text = element.get_text().strip()
            # Check if this header indicates a new section by seeing if it matches known event round types
            if any(section_type in header_text for section_type in ['Final', 'Semi-Final', 'Heat', 'Repechage','Semifinal']):
                current_section = header_text             
        elif 'timeteam' in element.get('class', []):
            # Extract data from this table and assign to current section
            crews, results_found_section = extract_crews_data_from_table(element, current_section)
            results_found += results_found_section
            sections.append({
                'event_name': current_section,
                'crews': crews
            })
    return sections, results_found

def extract_crews_data_from_table(table, section_name):
    crews = []
    results_found = 0
    # Find all tbody elements (each represents a crew)
    tbody_elements = table.find_all('tbody')
    for tbody in tbody_elements:
        # Find the main row (first tr with position data)
        main_row = tbody.find('tr', class_=lambda x: x and 'smallrow' not in x)
        if not main_row:
            continue # Skip if no main row found   
        # Extract position
        position_cell = main_row.find('td')
        position = position_cell.get_text().strip().replace('.', '') if position_cell else "N/A"
        # Extract crew data
        cells = main_row.find_all('td')
        if len(cells) >= 3:
            crew_name = cells[2].get_text().strip() if cells[2] else "N/A"
            # Extract finish time - SPECIAL FIX FOR FINALS
            finish_time = extract_finish_time(cells, section_name, table)
            results_found += 1
            crews.append({
                'position': position,
                'crew_name': crew_name,
                'finish_time': finish_time
            })
    
    return crews, results_found

def extract_finish_time(cells, section_name, table):
    # First, collect all time values in this row
    time_values = []
    for i, cell in enumerate(cells):
        cell_text = cell.get_text().strip()
        if re.match(r'\d+:\d+\.\d+', cell_text):
            time_values.append((i, cell_text))
    # For Time Trial sections
    if 'Time Trial' in section_name:
        if time_values:
            return time_values[0][1]  # Return the first (and usually only) time
    # For Finals and other sections
    if time_values:
        # Sort by column index and return the LAST one (finish time)
        time_values.sort(key=lambda x: x[0])
        return time_values[-1][1]

def main(year,datadir):
    file =  datadir+"/"+str(year)+"2nsr.json"
    year += 1 # As NSR happens in 2025, but in the 2024 academic year
    base_url = f"https://regatta.time-team.nl/nsr/{year}/results"
    open_8_data = asyncio.run(scrape_open_8_data(base_url, year))
    if open_8_data:
        # Output to JSON file
        with open(file, 'w') as f:
            json.dump(open_8_data, f, indent=2)       
    else:
        print("         Failed to scrape Open 8+ data")
    return True