import os
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
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    response = requests.get(url)
    data = response.json()

    players = data['elements']
    teams = {team['id']: team['name'] for team in data['teams']}
    positions = {pos['id']: pos['singular_name_short'] for pos in data['element_types']}

    for player in players:
        player['team_name'] = teams.get(player['team'])
        player['position_name'] = positions.get(player['element_type'])

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
    search_url = f"{SPORTMONKS_API_URL}/players/search/{player_full_name}?api_token={SPORTMONKS_API_KEY}"
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
        # No seasons to filter by, so return empty stats
        # This part might need adjustment based on desired behavior
        player_data_url = f"{SPORTMONKS_API_URL}/players/{sportmonks_player_id}?api_token={SPORTMONKS_API_KEY}"
        player_data_response = requests.get(player_data_url)
        player_data = player_data_response.json()
        player_data['data']['statistics'] = []
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
        if player_data.get('data').get('statistics'):
            # Sort the results from the API just in case they aren't ordered
            player_data['data']['statistics'].sort(key=lambda s: s.get('season', {}).get('name', ''), reverse=True)

    return player_data 