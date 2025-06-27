import re
import requests
from thefuzz import process

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

def _sanitize_team_name(name):
    """
    Sanitizes team names for more reliable fuzzy matching by removing common suffixes
    and standardizing the format.
    """
    name = name.lower()
    # Remove common suffixes like 'fc', 'afc', etc.
    name = re.sub(r'\s+(fc|afc|cf|sc|utd|united|hotspur)\b', '', name).strip()
    # Handle common name variations
    name_replacements = {
        "brighton & hove albion": "brighton",
        "wolverhampton wanderers": "wolves",
        "manchester city": "man city",
        "manchester united": "man utd",
        "nottingham forest": "nott'm forest",
        "tottenham hotspur": "spurs",
    }
    return name_replacements.get(name, name)

def _normalize_strength_to_difficulty(strength, min_strength, max_strength):
    """
    Normalizes a team's strength score (e.g., 1000-1350) to a 1-5 difficulty scale.
    """
    if max_strength == min_strength:
        return 3 # Avoid division by zero if all strengths are the same
    # Normalize the strength to a 0-1 range
    normalized = (strength - min_strength) / (max_strength - min_strength)
    # Scale to a 1-5 range and round to nearest integer
    difficulty = 1 + (normalized * 4)
    return round(difficulty)

def create_fixture_difficulty_map():
    """
    Creates a map of upcoming fixtures and their calculated difficulty for each team,
    using fuzzy matching for robust team name mapping.
    """
    print("\n--- Creating Fixture Difficulty Map ---")
    team_strength = get_team_strength_data()
    fixtures = get_fixture_data()
    
    # --- NEW: Normalize team strength to a 1-5 difficulty scale ---
    all_strengths = [s['strength_overall_home'] for s in team_strength.values()] + \
                    [s['strength_overall_away'] for s in team_strength.values()]
    min_strength = min(all_strengths)
    max_strength = max(all_strengths)
    print(f"Normalizing team strengths (Min: {min_strength}, Max: {max_strength}) to a 1-5 difficulty scale.")
    # ---

    print("Dynamically mapping team names using fuzzy matching...")
    
    fpl_team_names = list(team_strength.keys())
    pulse_team_names = list(set([team['team']['name'] for fixture in fixtures for team in fixture['teams']]))
    
    sanitized_fpl_names = {name: _sanitize_team_name(name) for name in fpl_team_names}
    sanitized_pulse_names = {name: _sanitize_team_name(name) for name in pulse_team_names}
    
    # Create a map from the original PulseLive name to the best-matching FPL name
    team_name_map = {}
    for pulse_name, sanitized_pulse_name in sanitized_pulse_names.items():
        # Find the best match from the sanitized FPL names
        best_match, score = process.extractOne(sanitized_pulse_name, sanitized_fpl_names.values())
        if score > 80: # Use a confidence threshold
            # Find the original FPL name that corresponds to the sanitized best match
            for original_fpl_name, sanitized_fpl_name in sanitized_fpl_names.items():
                if sanitized_fpl_name == best_match:
                    team_name_map[pulse_name] = original_fpl_name
                    break
    
    print(f"Successfully mapped {len(team_name_map)} out of {len(pulse_team_names)} teams.")

    fixture_map = {fpl_name: [] for fpl_name in fpl_team_names}
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

                # Difficulty is based on the opponent's overall strength, now normalized
                home_difficulty = _normalize_strength_to_difficulty(away_strength['strength_overall_home'], min_strength, max_strength)
                away_difficulty = _normalize_strength_to_difficulty(home_strength['strength_overall_away'], min_strength, max_strength)

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