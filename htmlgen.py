'''
Generates HTML pages for the website using data from the database.
'''

import config

page_header = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RowELO - British School Rowing Rankings</title>
    <link rel="stylesheet" href="styles.css">
    <script src="https://d3js.org/d3.v5.js"></script>
    <script src="https://mpld3.github.io/js/mpld3.v0.5.12.js"></script>
</head>
<body>
    <nav>
        <div class="nav-container">
            <a href="index.html" class="logo">RowELO</a>
            <div class="nav-links">
                <div class="dropdown" id="leagueDropdown">
                    <button class="dropbtn">
                        League Table
                        <span class="fa-caret-down">▼</span>
                    </button>
                    <div class="dropdown-content">
                        <a href="index.html">All Clubs</a>
                        <a href="ukonly.html">UK Only</a>
                    </div>
                </div>
                <a href="events.html">Events</a>
                <a href="about.html">About</a>
            </div>
        </div>
    </nav>

    <div class="container">
        <div id="home" class="page active">
            <div class="page-header">"""

page_footer = """
    </div>
    </body>
<script>
    function showPage(pageId) {
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        const target = document.getElementById(pageId);
        if(target) target.classList.add('active');
    }
    function showClubPage(clubId) { showPage(clubId); }
    document.addEventListener('DOMContentLoaded', () => showPage('home'));
</script>
</html>"""


def main(connection,year, end_year):
    cursor = connection.cursor()

    cursor.execute('''
    WITH latest_results AS (
        SELECT rr.club_id, rr.elo_after,
        ROW_NUMBER() OVER (PARTITION BY rr.club_id ORDER BY r.day_of_event DESC) as rn
        FROM race_results rr JOIN races r ON rr.race_id = r.race_id
    )
    SELECT RANK() OVER (ORDER BY COALESCE(lr.elo_after, 1500) DESC) as rank,
    c.club_name, c.club_id, COALESCE(lr.elo_after, 1500) as elo
    FROM clubs c LEFT JOIN latest_results lr ON c.club_id = lr.club_id AND lr.rn = 1
    ORDER BY rank;
    ''')
    results = cursor.fetchall()

    # Generate club pages HTML (to be reused)
    club_pages_html = generate_club_pages(cursor, results, year, end_year)
    
    # Generate index.html (All Clubs)
    html_index = page_header
    html_index += generate_league_table(results, True, year, end_year)
    html_index += club_pages_html
    html_index += page_footer
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_index)
    print("     1. index.html generated")
    
    # Generate ukonly.html (UK Only)
    html_ukonly = page_header
    html_ukonly += generate_league_table(results, False, year, end_year)
    html_ukonly += club_pages_html  # Add the same club pages
    html_ukonly += page_footer
    
    with open("ukonly.html", "w", encoding="utf-8") as f:
        f.write(html_ukonly)
    print("     2. ukonly.html generated")
    
    # Generate events.html
    html_events = generate_events_page(cursor)  # Events page doesn't need club pages
    
    with open("events.html", "w", encoding="utf-8") as f:
        f.write(html_events)
    print("     3. events.html generated")


def generate_club_pages(cursor, results, year, end_year):
    html = ""
    for rank, club_name, club_id, elo in results:
        cursor.execute(f'''
            SELECT e.event_name, r.day_of_event, rr.position, rr.gmt_percentage, r.race_id, r.race_round, rr.time_seconds
            FROM race_results rr
            JOIN races r ON rr.race_id = r.race_id
            JOIN events e ON r.event_id = e.event_id
            WHERE rr.club_id = {club_id} AND r.day_of_event > '{year}-08-01' AND r.day_of_event < '{end_year}-07-31' 
            ORDER BY r.day_of_event DESC, field(r.race_round, 'Final D Re-row', 'Final C Re-row', 'Final B Re-row', 'Final A Re-row', 'Final D', 'Final C', 'Final B', 'Final A', 'Repechage 4', 'Repechage 3', 'Repechage 2', 'Repechage 1', 'Heats', 'Time Trial') ASC;
        ''')
        clubresults = cursor.fetchall()
        
        wins = sum(1 for row in clubresults if row[2] == 1)
        gmt_total = 0
        gmt_len = 0
        for row in clubresults:
            if not(row[3] == 0.00 or row[3] is None):
                gmt_total += row[3]
                gmt_len += 1
        avg_gmt = gmt_total / gmt_len if gmt_len > 0 else 0.00
        
        html += f"""
        <div id="{club_id}" class="page">
            <div class="club-header">
                <h1>{club_name}</h1>
                <p>Current ELO: <strong>{elo}</strong> (Rank: {rank})</p>
                <a href="#" class="back-button" onclick="showPage('home')">← Back to League Table</a>
            </div>
            <div class="club-stats">
                <div class="stat-card"><div class="stat-value">{len(clubresults)}</div><div class="stat-label">Races</div></div>
                <div class="stat-card"><div class="stat-value">{wins}</div><div class="stat-label">Wins</div></div>
                <div class="stat-card"><div class="stat-value">{avg_gmt:.1f}%</div><div class="stat-label">Avg GMT%</div></div>
            </div>
            <div class="graph-container">
                <h3>ELO Rating Over Time</h3>
                <div class="graph">"""
        
        cursor.execute(f"SELECT r.day_of_event, rr.elo_after FROM race_results rr JOIN races r ON rr.race_id = r.race_id WHERE rr.club_id = {club_id} AND r.day_of_event > '{year}-08-01' AND r.day_of_event < '{end_year}-07-31' ORDER BY r.day_of_event, field(r.race_round, 'Final D Re-row', 'Final C Re-row', 'Final B Re-row', 'Final A Re-row', 'Final D', 'Final C', 'Final B', 'Final A', 'Repechage 4', 'Repechage 3', 'Repechage 2', 'Repechage 1', 'Heats', 'Time Trial') DESC")
        graph_data = cursor.fetchall()
        html += graphgen(graph_data)
        
        html += """</div></div>
            <div class="performance-table">
                <div class="performance-header">
                    <div>Event</div><div>Date</div><div>Round</div><div>Pos</div><div>Time</div><div>GMT%</div>
                </div>"""

        for event_name, event_date, position, gmt, race_id, race_round, time_seconds in clubresults:
            pos_display = "Invalid" if position == 0 else position
            if gmt == 0.00 or gmt is None:
                gmt_display = "N/A"
            else:
                gmt_display = f"{gmt:.1f}%"
            time_string = seconds_to_time(time_seconds)
            html += f"""
                <div class="performance-row">
                    <div>{event_name}</div><div>{event_date}</div><div>{race_round}</div><div>{pos_display}</div><div>{time_string}</div><div>{gmt_display}</div>
                </div>"""
        
        html += "</div></div>"
    
    return html


def graphgen(data):
    import matplotlib.pyplot as plt
    import mpld3
    from mpld3 import plugins

    dates = [date for (date, elo) in data]
    elos = [elo for (date, elo) in data]

    fig, ax = plt.subplots(figsize=(12, 6))
    line = ax.plot(dates, elos, marker='o')[0]
    ax.set_xlabel('Date')
    ax.set_ylabel('ELO Rating')
    ax.grid(True, alpha=0.3)
    
    tooltip = plugins.PointHTMLTooltip(line, labels=[f'Date: {date}<br/>ELO: {elo}' for date, elo in data])
    plugins.connect(fig, tooltip)
    
    plt.tight_layout()
    
    html = mpld3.fig_to_html(fig)
    plt.close(fig)
    
    return html


def seconds_to_time(seconds):
    if seconds is None or seconds == 0.00:
        return "N/A"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}:{secs:04.1f}"


def generate_league_table(results, show_international, year, end_year):
    if end_year - year == 1:
        html = f"<h1>British School Rowing League ({year}/{year + 1})</h1>"
    else:
        html = f"<h1>British School Rowing League ({year}/{year + 1}) - ({end_year - 1}/{end_year})</h1>"
    
    if not show_international:
        html += """<p>Includes only UK clubs</p>"""
    else:
        html += """<p>Includes international clubs</p>"""
    
    html += """<p>ELO-based rankings for J18 Boys Eights</p>
            </div>
            <div class="league-table">
                <div class="table-header">
                    <div>Rank</div><div>Club</div><div>ELO</div>
                </div>"""
    
    if not show_international:
        reduced_results = []
        for i, row in enumerate(results):
            if not any(tag in row[1] for tag in config.CLUB_NAME_INTERNATIONAL_TAGS):
                row = list(row)
                row[0] = len(reduced_results) + 1
                reduced_results.append(row)
        results = reduced_results

    for rank, club_name, club_id, elo in results:
        html += f"""
            <div class="table-row">
                <div class="rank">{rank}</div>
                <div><span class="club-name" onclick="showClubPage('{club_id}')">{club_name}</span></div>
                <div class="elo-rating">{elo}</div>
            </div>"""
    
    html += """        </div>
    </div>"""
    return html


def generate_events_page(cursor):
    html = page_header
    html += """
    <div class="events-page">
        <div class="page-header">
            <h1>Rowing Events</h1>
            <p>Click on an event to expand, then click on a race to view results</p>
        </div>
    """
    
    # Get summary stats
    cursor.execute('''
        SELECT 
            COUNT(DISTINCT e.event_id) as total_events,
            COUNT(DISTINCT r.race_id) as total_races,
            COUNT(DISTINCT rr.club_id) as total_clubs
        FROM events e
        LEFT JOIN races r ON e.event_id = r.event_id
        LEFT JOIN race_results rr ON r.race_id = rr.race_id
    ''')
    total_events, total_races, total_clubs = cursor.fetchone()
    
    html += f"""
    <div class="stats-summary">
        <div class="stat-card">
            <div class="stat-value">{total_events}</div>
            <div class="stat-label">Total Events</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{total_races}</div>
            <div class="stat-label">Total Races</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{total_clubs}</div>
            <div class="stat-label">Participating Clubs</div>
        </div>
    </div>
    """
    
    # Get all events
    cursor.execute('''
        SELECT 
            e.event_id,
            e.event_name,
            e.event_type,
            e.course_distance,
            MIN(r.day_of_event) as first_date,
            COUNT(DISTINCT r.race_id) as race_count
        FROM events e
        LEFT JOIN races r ON e.event_id = r.event_id
        GROUP BY e.event_id, e.event_name, e.event_type, e.course_distance
        ORDER BY e.event_id DESC
    ''')
    events = cursor.fetchall()
    
    # Generate collapsible sections for each event
    for event in events:
        event_id, event_name, event_type, course_distance, first_date, race_count = event
        date = first_date.strftime("%d %B %Y").lstrip("0") if first_date else "TBA"
        html += f'''
        <div class="event-collapsible">
            <div class="event-header" onclick="toggleEvent({event_id})">
                <div class="event-title">
                    <span class="event-toggle-icon" id="eventToggleIcon_{event_id}">▶</span>
                    <h3>{event_name + " " + str(first_date.year)}</h3>
                </div>
                <div class="event-meta">
                    <span class="event-type-badge">{event_type}</span>
                    {f'<span class="event-distance-badge">{course_distance}m</span>' if course_distance else ''}
                    <span class="event-date-badge">📅 {date}</span>
                    <span class="event-race-count">{race_count} {("race" if race_count == 1 else "races")}</span>
                </div>
            </div>
            <div class="event-content" id="eventContent_{event_id}" style="display: none;">
        '''
        
        # Get all races for this event
        cursor.execute('''
            SELECT 
                r.race_id,
                r.race_round,
                r.day_of_event,
                COUNT(rr.result_id) as num_entries
            FROM races r
            LEFT JOIN race_results rr ON r.race_id = rr.race_id
            WHERE r.event_id = %s
            GROUP BY r.race_id, r.race_round, r.day_of_event
            ORDER BY r.day_of_event DESC, FIELD(r.race_round, 'Final', 'Final A', 'Final B', 'Final C', 'Final D', 
                          'Semi-Final', 'Semi-Final 1', 'Semi-Final 2', 'Quarter-Final', 'Repechage', 'Repechage 1', 'Repechage 2', 'Heat', 'Heats' , 'Time Trial')
        ''', (event_id,))
        races = cursor.fetchall()
        
        # Generate collapsible sections for each race
        for race in races:
            race_id, race_round, day_of_event, num_entries = race
            if sum(x.count(race_round) for x in races) > 1:
                cursor.execute(f'''SELECT club_name FROM race_results rr JOIN clubs c ON rr.club_id = c.club_id WHERE rr.race_id = {race_id}''')
                clubs_in_heat = cursor.fetchall()
                race_round_str = str.join(" ", [race_round, "-", clubs_in_heat[0][0], "vs", clubs_in_heat[1][0]])
            else:
                race_round_str = race_round
            html += f'''
                <div class="race-collapsible">
                    <div class="race-header" onclick="toggleRace({event_id}, {race_id})">
                        <div class="race-title">
                            <span class="race-toggle-icon" id="raceToggleIcon_{event_id}_{race_id}">▶</span>
                            <h4>{race_round_str}</h4>
                        </div>
                        <div class="race-meta">
                            <span class="race-date">{day_of_event if day_of_event else "TBA"}</span>
                            <span class="race-entry-count">{num_entries} entries</span>
                        </div>
                    </div>
                    <div class="race-content" id="raceContent_{event_id}_{race_id}" style="display: none;">
            '''
            
            # Get results for this race
            cursor.execute('''
                SELECT c.club_name, rr.position, rr.time_seconds, rr.gmt_percentage
                FROM race_results rr
                JOIN clubs c ON rr.club_id = c.club_id
                WHERE rr.race_id = %s
                ORDER BY rr.position ASC
            ''', (race_id,))
            results = cursor.fetchall()
            
            if results:
                html += '''
                        <div class="results-table-wrapper">
                            <div class="results-table">
                                <div class="results-header">
                                    <div>Pos</div>
                                    <div>Club</div>
                                    <div>Time</div>
                                    <div>GMT%</div>
                                </div>
                '''
                
                for club_name, position, time_seconds, gmt in results:
                    time_str = seconds_to_time(time_seconds) if time_seconds else "N/A"
                    gmt_str = f"{gmt:.1f}%" if gmt else "N/A"
                    html += f'''
                                <div class="results-row">
                                    <div>{position}</div>
                                    <div>{club_name}</div>
                                    <div>{time_str}</div>
                                    <div>{gmt_str}</div>
                                </div>
                    '''
                
                html += '''
                            </div>
                        </div>
                '''
            else:
                html += '<div class="no-results">No results available for this race</div>'
            
            html += '''
                    </div>
                </div>
            '''
        
        html += '''
            </div>
        </div>
        '''
    
    # Add JavaScript for collapsible functionality
    html += '''
    </div>
    
    <script>
        function toggleEvent(eventId) {
            const content = document.getElementById(`eventContent_${eventId}`);
            const icon = document.getElementById(`eventToggleIcon_${eventId}`);
            
            if (content.style.display === 'none') {
                content.style.display = 'block';
                icon.textContent = '▼';
            } else {
                content.style.display = 'none';
                icon.textContent = '▶';
            }
        }
        
        function toggleRace(eventId, raceId) {
            const content = document.getElementById(`raceContent_${eventId}_${raceId}`);
            const icon = document.getElementById(`raceToggleIcon_${eventId}_${raceId}`);
            
            if (content.style.display === 'none') {
                content.style.display = 'block';
                icon.textContent = '▼';
            } else {
                content.style.display = 'none';
                icon.textContent = '▶';
            }
        }
    </script>
    '''
    
    html += page_footer
    return html


if __name__ == '__main__':
    main()