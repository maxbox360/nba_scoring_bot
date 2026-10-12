def get_ordinal_suffix(number):
    if 10 <= number % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th')
    return suffix


def get_passed_player(players_passed_names, points, current_table):
    passed_players_info = []

    for passed_player_name in players_passed_names:
        passed_player = current_table.loc[current_table['PLAYER_NAME'] == passed_player_name]
        passed_rank = passed_player['PTS_RANK'].values[0]
        passed_points = passed_player['PTS'].values[0]
        points_difference = points - passed_points
        passed_players_info.append((passed_player_name, passed_rank, points_difference))

    return passed_players_info


def get_next_player(current_rank, points, current_table):
    next_rank = current_rank - 1
    while next_rank > 0:
        next_players = current_table.loc[current_table['PTS_RANK'] == next_rank]

        if not next_players.empty:
            next_names = ", ".join(next_players['PLAYER_NAME'].values)  # Join names with commas
            next_player_rank = next_rank
            next_player_pts = next_players['PTS'].values[0]  # Points are the same for tied players
            difference_to_next = f"{(next_player_pts - points + 1):,}"
            return next_names, next_player_rank, difference_to_next

        next_rank -= 1
