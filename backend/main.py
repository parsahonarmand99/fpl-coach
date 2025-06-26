import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
import requests
from dotenv import load_dotenv
from unidecode import unidecode
from squad_builder import GeneticSquadBuilder, SquadAnalyzer
from pydantic import BaseModel
from typing import List

load_dotenv()

app = FastAPI()

SPORTMONKS_API_KEY = os.getenv("SPORTMONKS_API_KEY")
SPORTMONKS_API_URL = "https://api.sportmonks.com/v3/football"
PREMIER_LEAGUE_ID = 8 # Found via SportMonks documentation

class Player(BaseModel):
    id: int
    web_name: str
    now_cost: int
    team: int
    team_name: str
    team_short_name: str
    position_name: str
    ai_score: float

class Squad(BaseModel):
    squad: List[Player]

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
        player['team_short_name'] = teams.get(player['team'], {}).get('short_name')
        player['position_name'] = positions.get(player['element_type'])
        player['upcoming_fixtures'] = team_fixtures.get(player['team'], [])

    return players

@app.get("/api/ai-squad")
def get_ai_squad():
    try:
        players = get_players_data()
        
        # Filter out players with status 'u' (unavailable) or low chance of playing
        available_players = [
            p for p in players 
            if p.get('status') != 'u' and (p.get('chance_of_playing_next_round') is None or p.get('chance_of_playing_next_round') > 50)
        ]

        builder = GeneticSquadBuilder(
            players=available_players,
            population_size=200, # Increased for better exploration
            generations=100,     # Increased for deeper evolution
            mutation_rate=0.2
        )
        best_squad = builder.run()
        
        # Properly select starting 11 following FPL rules
        # Group players by position
        position_groups = {'GKP': [], 'DEF': [], 'MID': [], 'FWD': []}
        for player in best_squad:
            pos = player.get('position_name')
            if pos in position_groups:
                position_groups[pos].append(player)
        
        # Sort each position group by AI score
        for pos in position_groups:
            position_groups[pos].sort(key=lambda p: p.get('ai_score', 0), reverse=True)
        
        # Select starting 11: 1 GKP + best formation from remaining positions
        starting_11 = []
        bench = []
        
        # Always start the best goalkeeper
        if position_groups['GKP']:
            starting_11.append(position_groups['GKP'][0])
            bench.extend(position_groups['GKP'][1:])
        
        # For outfield players, try different valid formations and pick the best
        valid_formations = [
            {'DEF': 4, 'MID': 4, 'FWD': 2},  # 4-4-2
            {'DEF': 3, 'MID': 5, 'FWD': 2},  # 3-5-2
            {'DEF': 3, 'MID': 4, 'FWD': 3},  # 3-4-3
            {'DEF': 4, 'MID': 3, 'FWD': 3},  # 4-3-3
            {'DEF': 4, 'MID': 5, 'FWD': 1},  # 4-5-1
            {'DEF': 5, 'MID': 4, 'FWD': 1},  # 5-4-1
            {'DEF': 5, 'MID': 3, 'FWD': 2},  # 5-3-2
        ]
        
        best_formation_score = 0
        best_formation_players = []
        
        for formation in valid_formations:
            formation_players = []
            formation_score = 0
            
            # Check if we have enough players for this formation
            can_form = True
            for pos, count in formation.items():
                if len(position_groups[pos]) < count:
                    can_form = False
                    break
            
            if can_form:
                # Select best players for this formation
                for pos, count in formation.items():
                    selected = position_groups[pos][:count]
                    formation_players.extend(selected)
                    formation_score += sum(p.get('ai_score', 0) for p in selected)
                
                if formation_score > best_formation_score:
                    best_formation_score = formation_score
                    best_formation_players = formation_players
        
        # Add the best formation players to starting 11
        starting_11.extend(best_formation_players)
        
        # Add remaining players to bench
        for pos in ['DEF', 'MID', 'FWD']:
            selected_ids = {p['id'] for p in best_formation_players if p.get('position_name') == pos}
            remaining = [p for p in position_groups[pos] if p['id'] not in selected_ids]
            bench.extend(remaining)
        
        # Calculate squad statistics
        total_cost = sum(p.get('now_cost', 0) / 10 for p in best_squad)  # Convert from tenths to millions
        remaining_budget = 100.0 - total_cost
        total_ai_score = sum(p.get('ai_score', 0) for p in starting_11)
        
        # Determine the formation name
        formation_counts = {}
        for player in best_formation_players:
            pos = player.get('position_name')
            formation_counts[pos] = formation_counts.get(pos, 0) + 1
        
        formation_name = f"{formation_counts.get('DEF', 0)}-{formation_counts.get('MID', 0)}-{formation_counts.get('FWD', 0)}"
        
        return {
            "starting_11": starting_11,
            "bench": bench,
            "formation": formation_name,
            "squad_value": round(total_cost, 1),
            "remaining_budget": round(remaining_budget, 1),
            "total_ai_score": round(total_ai_score, 1)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/random-squad")
async def get_random_squad():
    """
    Generates and returns a single, valid, randomized FPL squad.
    """
    try:
        all_players = get_players_data()
        builder = GeneticSquadBuilder(players=all_players)
        squad = builder.create_random_squad()
        if squad is None:
            raise HTTPException(status_code=500, detail="Failed to generate a random squad after several attempts.")
        return squad
    except Exception as e:
        print(f"An unexpected error occurred in /api/random-squad: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred while generating a random squad.")

@app.post("/api/analyze-squad")
def analyze_squad_endpoint(squad_data: Squad):
    try:
        all_players = get_players_data()
        user_squad_list = [p.dict() for p in squad_data.squad]

        analyzer = SquadAnalyzer(
            user_squad=user_squad_list,
            all_players=all_players
        )
        
        captain = analyzer.suggest_captain()
        transfers = analyzer.suggest_transfers()
        double_transfer = analyzer.suggest_double_transfers()
        
        return {
            "captain_suggestion": captain,
            "suggested_transfers": transfers,
            "double_transfer_suggestion": double_transfer
        }
    except Exception as e:
        # Log the exception for debugging
        print(f"Error in squad analysis: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during analysis.")

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