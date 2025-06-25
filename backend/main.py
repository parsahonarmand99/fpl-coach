import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
import requests
from dotenv import load_dotenv
from unidecode import unidecode

load_dotenv()

app = FastAPI()

SPORTMONKS_API_KEY = os.getenv("SPORTMONKS_API_KEY")
SPORTMONKS_API_URL = "https://api.sportmonks.com/v3/football"
PREMIER_LEAGUE_ID = 8 # Found via SportMonks documentation

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/api/bootstrap")
def get_bootstrap_data():
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    response = requests.get(url)
    return response.json()

@app.get("/api/players")
def get_players_data():
    bootstrap_url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    fixtures_url = "https://fantasy.premierleague.com/api/fixtures/"

    try:
        bootstrap_res = requests.get(bootstrap_url)
        fixtures_res = requests.get(fixtures_url)
        bootstrap_res.raise_for_status()
        fixtures_res.raise_for_status()
        
        bootstrap_data = bootstrap_res.json()
        fixtures_data = fixtures_res.json()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching FPL data: {e}")

    players = bootstrap_data['elements']
    teams = {team['id']: team for team in bootstrap_data['teams']}
    positions = {pos['id']: pos['singular_name_short'] for pos in bootstrap_data['element_types']}
    
    # --- AI Score Calculation ---
    
    # 1. Convert relevant stats to float for calculation
    for p in players:
        p['form'] = float(p.get('form', 0))
        p['ict_index'] = float(p.get('ict_index', 0))
        p['points_per_game'] = float(p.get('points_per_game', 0))

    # 2. Normalize metrics to a 0-1 scale
    def normalize(players, key):
        min_val = min(p[key] for p in players)
        max_val = max(p[key] for p in players)
        range_val = max_val - min_val
        if range_val == 0:
            return
        for p in players:
            p[f"{key}_normalized"] = (p[key] - min_val) / range_val

    normalize(players, 'form')
    normalize(players, 'ict_index')
    normalize(players, 'points_per_game')

    # 3. Calculate weighted AI score
    weights = {
        "form": 0.4,
        "ict": 0.3,
        "ppg": 0.3
    }

    for p in players:
        form_score = p.get('form_normalized', 0) * weights['form']
        ict_score = p.get('ict_index_normalized', 0) * weights['ict']
        ppg_score = p.get('points_per_game_normalized', 0) * weights['ppg']
        p['ai_score'] = round((form_score + ict_score + ppg_score) * 100, 2)

    # --- End AI Score Calculation ---

    # Get current gameweek
    current_gameweek = next((event['id'] for event in bootstrap_data['events'] if event['is_next']), None)

    # Process fixtures
    team_fixtures = {team_id: [] for team_id in teams.keys()}
    if current_gameweek:
        upcoming_fixtures = [f for f in fixtures_data if f.get('event') and f['event'] >= current_gameweek]
        
        for team_id in teams.keys():
            # Get next 5 fixtures for the team
            next_5_fixtures = [f for f in upcoming_fixtures if f['team_h'] == team_id or f['team_a'] == team_id][:5]
            for fixture in next_5_fixtures:
                is_home = fixture['team_h'] == team_id
                opponent_id = fixture['team_a'] if is_home else fixture['team_h']
                opponent_name = teams.get(opponent_id, {}).get('short_name', 'N/A')
                difficulty = fixture['team_h_difficulty'] if is_home else fixture['team_a_difficulty']
                
                team_fixtures[team_id].append({
                    "opponent": opponent_name,
                    "difficulty": difficulty,
                    "is_home": is_home
                })

    for player in players:
        player['team_name'] = teams.get(player['team'], {}).get('name')
        player['position_name'] = positions.get(player['element_type'])
        player['upcoming_fixtures'] = team_fixtures.get(player['team'], [])

    return players

@app.get("/api/player/{player_id}")
def get_player_details(player_id: int):
    # This is a placeholder for matching FPL player IDs to SportMonks player IDs.
    # In a real application, you would need a more robust matching system.
    fpl_player_data = next((p for p in get_players_data() if p['id'] == player_id), None)
    if not fpl_player_data:
        raise HTTPException(status_code=404, detail="Player not found in FPL data")

    player_full_name = f"{fpl_player_data['first_name']} {fpl_player_data['second_name']}"

    # Search for the player on SportMonks by name
    search_url = f"{SPORTMONKS_API_URL}/players/search/{player_full_name}?api_token={SPORTMONKS_API_KEY}&include=teams.team"
    search_response = requests.get(search_url)
    
    if search_response.status_code != 200:
        raise HTTPException(status_code=search_response.status_code, detail="Error searching for player on SportMonks")

    search_data = search_response.json()
    if not search_data.get('data'):
        raise HTTPException(status_code=404, detail=f"Player '{player_full_name}' not found on SportMonks")

    # --- Robust Name Matching Logic ---
    def sanitize_name(name):
        return unidecode(name.lower()) if name else ""

    fpl_names = {
        sanitize_name(fpl_player_data.get('web_name')),
        sanitize_name(fpl_player_data.get('first_name')),
        sanitize_name(fpl_player_data.get('second_name')),
        sanitize_name(player_full_name)
    }
    fpl_names.discard('')

    matched_player = None
    for sm_player in search_data.get('data', []):
        sm_names = {
            sanitize_name(sm_player.get('common_name')),
            sanitize_name(sm_player.get('firstname')),
            sanitize_name(sm_player.get('lastname')),
            sanitize_name(sm_player.get('name')),
            sanitize_name(sm_player.get('display_name'))
        }
        sm_names.discard('')
        
        if fpl_names.intersection(sm_names):
            matched_player = sm_player
            break
            
    if not matched_player:
        raise HTTPException(status_code=404, detail=f"Could not find a unique player match for '{player_full_name}' on SportMonks")

    sportmonks_player_id = matched_player['id']

    # --- Fetch Last 5 Games (Form) from FPL API ---
    form_stats = []
    try:
        fpl_bootstrap_data = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/").json()
        all_events = fpl_bootstrap_data.get('events', [])
        teams_map = {team['id']: team['short_name'] for team in fpl_bootstrap_data.get('teams', [])}

        finished_gameweeks = sorted(
            [gw for gw in all_events if gw.get('finished', False)],
            key=lambda gw: gw['id'],
            reverse=True
        )
        
        last_5_gameweeks = finished_gameweeks[:5]
        player_team_id = fpl_player_data.get('team')

        for gw in last_5_gameweeks:
            gw_id = gw.get('id')
            fixtures_response = requests.get(f"https://fantasy.premierleague.com/api/fixtures/?event={gw_id}")
            fixtures_data = fixtures_response.json()
            
            live_response = requests.get(f"https://fantasy.premierleague.com/api/event/{gw_id}/live/")
            live_data = live_response.json()
            
            player_live_stats = next((elem for elem in live_data.get('elements', []) if elem.get('id') == player_id), None)

            if player_live_stats and player_live_stats['stats']['minutes'] > 0:
                player_fixture_id = player_live_stats['explain'][0]['fixture']
                player_fixture = next((fix for fix in fixtures_data if fix.get('id') == player_fixture_id), None)
                
                if player_fixture:
                    opponent_id = player_fixture['team_a'] if player_fixture['team_h'] == player_team_id else player_fixture['team_h']
                    opponent_name = teams_map.get(opponent_id, 'N/A')
                    
                    stats = player_live_stats['stats']
                    game_stats = {
                        'fixture_id': player_fixture['id'],
                        'fixture_name': opponent_name,
                        'date': player_fixture.get('kickoff_time'),
                        'minutes_played': stats.get('minutes', 0),
                        'goals': stats.get('goals_scored', 0),
                        'assists': stats.get('assists', 0),
                        'clean_sheets': stats.get('clean_sheets', 0),
                        'goals_conceded': stats.get('goals_conceded', 0),
                        'own_goals': stats.get('own_goals', 0),
                        'penalties_saved': stats.get('penalties_saved', 0),
                        'penalties_missed': stats.get('penalties_missed', 0),
                        'yellow_cards': stats.get('yellow_cards', 0),
                        'red_cards': stats.get('red_cards', 0),
                        'saves': stats.get('saves', 0),
                        'bonus': stats.get('bonus', 0),
                        'bps': stats.get('bps', 0),
                        'influence': stats.get('influence', '0.0'),
                        'creativity': stats.get('creativity', '0.0'),
                        'threat': stats.get('threat', '0.0'),
                        'ict_index': stats.get('ict_index', '0.0'),
                        'expected_goals': stats.get('expected_goals', '0.00'),
                        'expected_assists': stats.get('expected_assists', '0.00'),
                        'expected_goal_involvements': stats.get('expected_goal_involvements', '0.00'),
                        'expected_goals_conceded': stats.get('expected_goals_conceded', '0.00'),
                        'total_points': stats.get('total_points', 0)
                    }
                    form_stats.append(game_stats)
    except requests.exceptions.RequestException as e:
        print(f"Could not fetch FPL form data: {e}")

    # --- End Fetch Form ---

    # Fetch all seasons for the Premier League to find the last two
    seasons_url = f"{SPORTMONKS_API_URL}/leagues/{PREMIER_LEAGUE_ID}?api_token={SPORTMONKS_API_KEY}&include=seasons"
    seasons_response = requests.get(seasons_url)
    if seasons_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Could not fetch seasons from SportMonks")
    
    league_data = seasons_response.json().get('data', {})
    all_seasons = league_data.get('seasons', [])

    if not all_seasons:
        raise HTTPException(status_code=404, detail="No seasons found for Premier League")

    all_seasons.sort(key=lambda s: s.get('name', ''), reverse=True)
    last_two_season_ids = [s['id'] for s in all_seasons[:2]]
    
    if not last_two_season_ids:
        player_data_url = f"{SPORTMONKS_API_URL}/players/{sportmonks_player_id}?api_token={SPORTMONKS_API_KEY}"
        player_data_response = requests.get(player_data_url)
        player_data = player_data_response.json()
        player_data['data']['statistics'] = []
        player_data['data']['form_stats'] = form_stats
        return player_data

    season_ids_str = ",".join(map(str, last_two_season_ids))

    # Fetch detailed stats for the player from SportMonks, filtered by the last two seasons
    includes = "statistics.details.type;statistics.season.league"
    filters = f"playerStatisticSeasons:{season_ids_str}"
    stats_url = f"{SPORTMONKS_API_URL}/players/{sportmonks_player_id}?api_token={SPORTMONKS_API_KEY}&include={includes}&filters={filters}"
    stats_response = requests.get(stats_url)

    if stats_response.status_code != 200:
        raise HTTPException(status_code=stats_response.status_code, detail="Error fetching player stats from SportMonks")

    player_data = stats_response.json()

    if player_data.get('data'):
        player_data['data']['position_name'] = fpl_player_data.get('position_name')
        player_data['data']['form_stats'] = form_stats
        if player_data.get('data').get('statistics'):
            # Sort the results from the API just in case they aren't ordered
            player_data['data']['statistics'].sort(key=lambda s: s.get('season', {}).get('name', ''), reverse=True)

    return player_data 