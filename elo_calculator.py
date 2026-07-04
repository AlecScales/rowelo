"""
Handles ELO calculations for RowELO.
"""

import config


def get_club_elo(cursor, club_id):
    cursor.execute(
        "SELECT elo_after FROM race_results WHERE club_id = %s AND elo_after IS NOT NULL ORDER BY result_id DESC LIMIT 1",
        (club_id,)
    )
    result = cursor.fetchone()
    return result[0] if result else config.DEFAULT_ELO


def calculate_elo_for_club(cursor, race_id, target_club_id):
    # Get all clubs in the race with their positions
    cursor.execute(
        "SELECT club_id, position FROM race_results WHERE race_id = %s",
        (race_id,)
    )
    results = cursor.fetchall()
    if len(results) < 2: # If there is only one club in the race, return its current ELO as there are no opponents to compare against
        return get_club_elo(cursor, target_club_id)
    # Get target club's current ELO and position
    target_elo = None
    target_position = None
    for club_id, position in results:
        if club_id == target_club_id:
            target_elo = get_club_elo(cursor, club_id)
            target_position = position
            break
    # Pairwise comparison against all other clubs
    total_expected = 0
    total_actual = 0
    for club_id, position in results:
        if club_id != target_club_id and target_position != 0 and position != 0:
            opponent_elo = get_club_elo(cursor, club_id)
            # Calculate expected score
            expected = 1 / (1 + 10 ** ((opponent_elo - target_elo) / 400))
            total_expected += expected
            # Calculate actual score (1 = win, 0.5 = tie, 0 = loss)
            if target_position < position:
                total_actual += 1
            elif target_position > position:
                total_actual += 0
            else:
                total_actual += 0.5
    # Calculate new ELO
    new_elo = target_elo + round(config.K_FACTOR * (total_actual - total_expected))
    
    return new_elo