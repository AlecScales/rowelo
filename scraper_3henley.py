'''
Scrapes Henley Royal Regatta Princess Elizabeth Challenge Cup data from hrr.co.uk.
'''

import asyncio
from requests_html import AsyncHTMLSession
import bs4
import json
import re


def main(year,datadir):
    file=datadir+"/"+str(year)+"3henley.json" # File path to save data, in the data folder, with the set year in the file name
    year += 1 # As PE happens in 2025, but in the 2024 academic year
    asyncio.run(scraper(year,file))

async def scraper(year,file):
    all_results = []
    session = AsyncHTMLSession()
    page_number = 1
    
    while True:
        #Uses Henley Royal Regatta's results page with filters for year and PE Cup
        url = f"https://www.hrr.co.uk/results/?result-page={page_number}&race-year={year}&trophy=the-princess-elizabeth-challenge-cup"
        try:
            r = await session.get(url)
            await r.html.arender()
            soup = bs4.BeautifulSoup(r.html.html, "html.parser")
            result_cards = soup.find_all("div", {"class": "results-card__wrapper"})
            if len(result_cards) < 20: # Last page check, as each full page has 20 results, so the last page will have less than 20
                if result_cards:
                    for card in result_cards:
                        all_results.append(extract_race_info(card))
                print(f"             Page {page_number}: {len(result_cards)} races")
                break
            for card in result_cards:
                all_results.append(extract_race_info(card))
            print(f"             Page {page_number}: {len(result_cards)} races")
            page_number += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"             Error on page {page_number}: {e}")
            break
    await session.close()

    with open(file, "w") as f: # Save results to JSON file
        json.dump(all_results, f, indent=2)
    print(f"             Complete: {len(all_results)} races from {page_number} pages")
    return True


def extract_race_info(card):
    try:
        # Find first occurances of html classes to extract data
        winner = card.find("div", {"class": "club--winning"}).get_text().strip()
        loser = card.find("div", {"class": "club--losing"}).get_text().strip()
        # Extract stage (e.g., Final, Semi-Final) from info list
        info_list = card.find("ul", {"class": "inline-details"})
        list_items = info_list.find_all("li") if info_list else []
        stage = list_items[1].get_text().strip() if len(list_items) > 1 else "N/A"
        # Extract date from event details
        event_details = card.find("div", {"class": "results-card__row event-details desktop-only"})
        date = "N/A"
        if event_details:
            event_text = event_details.get_text()
            date_match = re.search(r'(\w+)\s+(\d+)\s+(\w+)\s+(\d+)', event_text) # Looks for date pattern
            if date_match:
                day, date_num, month, year = date_match.groups()
                date = f"{date_num}-{month}-20{year}" # Convert to day-month-year format
        # Gets finish time from within finish element
        finish_elem = card.find("div", {"class": "record finish"})
        finish_time = finish_elem.find("div", {"class": "stat split"}).get_text().strip() if finish_elem else "N/A"
        # Gets lengths one by from within verdict element
        verdict_elem = card.find("div", {"class": "record verdict"})
        verdict = verdict_elem.find("div", {"class": "stat"}).get_text().strip() if verdict_elem else "N/A"
        
        return {
            "winner": winner,
            "loser": loser,
            "stage": stage,
            "date": date,
            "finish_time": finish_time,
            "verdict": verdict
        }
        
    except Exception:
        return {
            "winner": "N/A", "loser": "N/A", "stage": "N/A",
            "date": "N/A", "finish_time": "N/A", "verdict": "N/A"
        }