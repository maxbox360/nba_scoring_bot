def get_next_players(next_name):
    next_players = next_name.split(', ')
    if len(next_players) >= 3:
        return ', '.join(next_players[:-1]) + ", and " + next_players[-1]
    if len(next_players) == 2:
        return " and ".join(next_players)
    return next_players[0]


def compose_post(post_data):
    next_players = get_next_players(post_data['next_name'])
    passed_names = [player[0] for player in post_data['players_passed_info']]
    if len(passed_names) > 2:
        passed = ', '.join(passed_names[:-1]) + f", and {passed_names[-1]}"
    elif len(passed_names) == 2:
        passed = f"{passed_names[0]} and {passed_names[1]}"
    else:
        passed = passed_names[0]

    post = (
        f"{post_data['player_name']} has become the {post_data['current_rank']}{post_data['ordinal_suffix']} ranked scorer in NBA history. "
        f"He has scored {post_data['points']:,} points in his career, passing: {passed}. \n\n"
        f"He needs {post_data['difference_to_next']} points to pass {next_players} "
        f"for {post_data['next_player_rank']}{post_data['next_ordinal_suffix']} all time."
    )

    if len(post) > 280 and len(post_data['players_passed_info']) > 2:
        return (
            f"{post_data['player_name']} has become the {post_data['current_rank']}{post_data['ordinal_suffix']} ranked scorer in NBA history. "
            f"He has scored {post_data['points']:,} points in his career, passing: {post_data['players_passed_info'][0][0]} and others. \n\n"
            f"He needs {post_data['difference_to_next']} points to pass {post_data['next_name']} "
            f"for {post_data['next_player_rank']}{post_data['next_ordinal_suffix']} all time."
        )
    return post
