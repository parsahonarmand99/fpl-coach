import requests

def get_team_strength_data():
    """
    Fetches the bootstrap-static data from the FPL API to get team strength ratings.
    """
    print("Fetching team strength data from FPL API...")
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    teams = data.get('teams', [])
    team_strength_map = {
        team['name']: {
            'strength_attack_home': team['strength_attack_home'],
            'strength_attack_away': team['strength_attack_away'],
            'strength_defence_home': team['strength_defence_home'],
            'strength_defence_away': team['strength_defence_away'],
            'strength_overall_home': team['strength_overall_home'],
            'strength_overall_away': team['strength_overall_away'],
        } for team in teams
    }
    print(f"Successfully fetched strength data for {len(team_strength_map)} teams.")
    return team_strength_map

def get_fixture_data():
    """
    Fetches the full fixture list from the PulseLive API.
    """
    print("Fetching full season fixture data from PulseLive API...")
    url = "https://footballapi.pulselive.com/football/fixtures?comps=1&page=0&pageSize=500&sort=asc&statuses=U,S"
    response = requests.get(url)
    response.raise_for_status()
    fixtures = response.json().get('content', [])
    print(f"Successfully fetched {len(fixtures)} fixtures.")
    return fixtures

def create_fixture_difficulty_map():
    """
    Creates a map of upcoming fixtures and their calculated difficulty for each team.
    """
    print("\n--- Creating Fixture Difficulty Map ---")
    team_strength = get_team_strength_data()
    fixtures = get_fixture_data()
    
    print("Mapping team names between FPL and PulseLive APIs...")
    # This is a placeholder for a proper team name mapping
    # The PulseLive API uses different team names than the FPL API
    team_name_map = {
        "Arsenal": "Arsenal",
        "Aston Villa": "Aston Villa",
        "Bournemouth": "Bournemouth",
        "Brentford": "Brentford",
        "Brighton & Hove Albion": "Brighton",
        "Chelsea": "Chelsea",
        "Crystal Palace": "Crystal Palace",
        "Everton": "Everton",
        "Fulham": "Fulham",
        "Ipswich Town": "Ipswich",
        "Leicester City": "Leicester",
        "Liverpool": "Liverpool",
        "Manchester City": "Man City",
        "Manchester United": "Man Utd",
        "Newcastle United": "Newcastle",
        "Nottingham Forest": "Nott'm Forest",
        "Southampton": "Southampton",
        "Tottenham Hotspur": "Spurs",
        "West Ham United": "West Ham",
        "Wolverhampton Wanderers": "Wolves"
    }

    fixture_map = {fpl_name: [] for fpl_name in team_name_map.values()}
    print("Processing fixtures and calculating difficulty scores...")

    for fixture in fixtures:
        gameweek = fixture.get('gameweek', {}).get('gameweek')
        home_team_name = fixture['teams'][0]['team']['name']
        away_team_name = fixture['teams'][1]['team']['name']

        if home_team_name in team_name_map and away_team_name in team_name_map:
            fpl_home_name = team_name_map[home_team_name]
            fpl_away_name = team_name_map[away_team_name]

            if fpl_home_name in team_strength and fpl_away_name in team_strength:
                home_strength = team_strength[fpl_home_name]
                away_strength = team_strength[fpl_away_name]

                # Difficulty is based on the opponent's overall strength
                home_difficulty = away_strength['strength_overall_home']
                away_difficulty = home_strength['strength_overall_away']

                fixture_map[fpl_home_name].append({
                    "gameweek": gameweek,
                    "opponent": fpl_away_name,
                    "difficulty": home_difficulty,
                    "location": "H"
                })
                fixture_map[fpl_away_name].append({
                    "gameweek": gameweek,
                    "opponent": fpl_home_name,
                    "difficulty": away_difficulty,
                    "location": "A"
                })
    
    print(f"Fixture difficulty map created successfully for {len(fixture_map)} teams.")
    print("--- Fixture Service Initialized ---\n")
    return fixture_map

if __name__ == "__main__":
    # For testing purposes
    fixtures = create_fixture_difficulty_map()
    import json
    print(json.dumps(fixtures, indent=2)) 