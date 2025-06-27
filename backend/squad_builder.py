import random
import itertools
import asyncio
from collections import Counter
from typing import List, Dict, Any
from pydantic import BaseModel
from fixture_service import create_fixture_difficulty_map

SQUAD_RULES = {
    "TOTAL_PLAYERS": 15,
    "BUDGET": 100.0,
    "PLAYERS_PER_TEAM": 3,
    "POSITIONS": {
        "GKP": 2,
        "DEF": 5,
        "MID": 5,
        "FWD": 3
    }
}

VALID_FORMATIONS = [
    {'GKP': 1, 'DEF': 3, 'MID': 5, 'FWD': 2},
    {'GKP': 1, 'DEF': 3, 'MID': 4, 'FWD': 3},
    {'GKP': 1, 'DEF': 4, 'MID': 4, 'FWD': 2},
    {'GKP': 1, 'DEF': 4, 'MID': 5, 'FWD': 1},
    {'GKP': 1, 'DEF': 5, 'MID': 3, 'FWD': 2},
    {'GKP': 1, 'DEF': 5, 'MID': 4, 'FWD': 1},
]

class GeneticSquadBuilder:
    def __init__(self, players, budget=100.0, population_size=1000, generations=500, mutation_rate=0.2, elitism_pct=0.1):
        """
        Initializes the Genetic Algorithm Squad Builder.
        - players: A list of all available players.
        - budget: The total budget for the squad.
        - population_size: The number of squads in each generation.
        - generations: The number of generations to evolve.
        - mutation_rate: The probability of a squad undergoing mutation.
        - elitism_pct: The percentage of the best squads to carry over to the next generation.
        """
        self.players = players
        self.budget = budget
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.elite_size = int(population_size * elitism_pct)
        
        # --- NEW: Fixture-aware AI Score Calculation ---
        print("Initializing Genetic Squad Builder...")
        self.fixture_difficulty_map = create_fixture_difficulty_map()
        for player in self.players:
            player['ai_score'] = self._calculate_ai_score(player)
        print("AI scores calculated for all players.")
        # ---
        
        # Pre-categorize players by position for easier selection
        self.positions = {pos: [] for pos in SQUAD_RULES["POSITIONS"].keys()}
        for p in self.players:
            pos_name = p.get('position_name')
            if pos_name in self.positions:
                self.positions[pos_name].append(p)

    def _is_valid(self, squad):
        """Checks if a squad is valid according to FPL rules."""
        if len(squad) != SQUAD_RULES["TOTAL_PLAYERS"]:
            return False
        
        # Check budget
        if sum(p['now_cost'] / 10 for p in squad) > self.budget:
            return False
        
        # Check team limits
        team_counts = Counter(p['team'] for p in squad)
        if any(count > SQUAD_RULES["PLAYERS_PER_TEAM"] for count in team_counts.values()):
            return False
            
        # Check position limits (usually guaranteed by generation method, but good for safety)
        position_counts = Counter(p['position_name'] for p in squad)
        for pos, count in SQUAD_RULES["POSITIONS"].items():
            if position_counts.get(pos, 0) != count:
                return False

        return True

    def _repair_squad(self, squad):
        """
        Attempts to repair an invalid squad, primarily by fixing budget issues.
        It swaps the player with the worst value (ai_score/cost) for a cheaper one.
        """
        while sum(p['now_cost'] / 10 for p in squad) > self.budget:
            # Find the player with the worst value for money to replace
            squad.sort(key=lambda p: p.get('ai_score', 0) / p.get('now_cost', 1), reverse=False)
            player_to_replace = squad[0]
            
            # Find a cheaper replacement of the same position
            replacement_options = [
                p for p in self.positions[player_to_replace['position_name']]
                if p['now_cost'] < player_to_replace['now_cost'] and p['id'] not in [sq_p['id'] for sq_p in squad]
            ]
            
            if not replacement_options:
                return None # Cannot repair

            new_player = random.choice(replacement_options)
            squad[0] = new_player

        return squad

    def _create_random_squad(self):
        """Creates a single, valid, random squad."""
        attempts = 0
        while attempts < 1000: # Add a limit to prevent infinite loops
            squad = []
            # Start by picking players for each position
            for pos, count in SQUAD_RULES["POSITIONS"].items():
                # Ensure there are enough players to choose from
                if len(self.positions[pos]) >= count:
                    squad.extend(random.sample(self.positions[pos], count))

            if len(squad) == SQUAD_RULES["TOTAL_PLAYERS"] and self._is_valid(squad):
                return squad
            attempts += 1
        return None # Return None if we failed to create a valid squad

    def create_random_squad(self):
        """Public method to create a single, valid, random squad."""
        return self._create_random_squad()

    def _get_average_fixture_difficulty(self, player, num_games=5):
        """
        Calculates the average fixture difficulty for a player over the next N games.
        """
        team_name = player.get('team_name')
        if not team_name or team_name not in self.fixture_difficulty_map:
            return 3 # Return a neutral default difficulty if no data

        upcoming_fixtures = sorted(
            [f for f in self.fixture_difficulty_map[team_name] if f.get('gameweek')],
            key=lambda x: x['gameweek']
        )
        
        next_n_fixtures = upcoming_fixtures[:num_games]
        
        if not next_n_fixtures:
            return 3 

        total_difficulty = sum(f['difficulty'] for f in next_n_fixtures)
        return total_difficulty / len(next_n_fixtures)

    def _calculate_ai_score(self, player: Dict[str, Any]) -> float:
        """
        Calculates a player's AI score based on a weighted combination of their
        recent form, underlying stats (ICT index), and upcoming fixture difficulty.
        """
        # --- Weights for different factors ---
        form_weight = 0.4
        ict_weight = 0.4
        difficulty_weight = 0.2
        # ---

        form = float(player.get('form', 0))
        ict_index = float(player.get('ict_index', 0))
        
        # Normalize form and ICT to be on a similar scale (e.g., 0-10)
        # These max values are approximate and might need tuning.
        normalized_form = (form / 10) * 10
        normalized_ict = (ict_index / 400) * 10 
        
        # --- Fixture Difficulty Calculation ---
        # Lower difficulty is better, so we invert the logic.
        # A score of 1 is easiest, 5 is hardest. We want to reward easier fixtures.
        avg_difficulty = self._get_average_fixture_difficulty(player)
        
        # Scale from 1-5 to 0-1, where 1 is best (easiest fixtures)
        difficulty_score = (5 - avg_difficulty) / 4
        # ---
        
        # --- Final Weighted Score ---
        base_score = (normalized_form * form_weight) + (normalized_ict * ict_weight)
        final_score = base_score * (1 + (difficulty_score * difficulty_weight))
        # ---

        # Add a small bonus for players who play more minutes
        minutes_bonus = (player.get('minutes', 0) / 3420) * 2 # Max minutes ~3420
        final_score += minutes_bonus

        return round(final_score, 2)

    def _calculate_fitness(self, squad):
        """
        Calculates a squad's fitness based on the total AI score of the
        best possible 11-player starting lineup from the 15-player squad.
        """
        if not squad:
            return 0
        
        best_formation_score = 0
        
        # For a given 15-player squad, find the best possible starting 11
        # by testing all valid formations.
        for formation in VALID_FORMATIONS:
            starters = []
            
            # Select the best players for the current formation based on their pre-calculated AI score
            for pos, count in formation.items():
                pos_players = sorted(
                    [p for p in squad if p.get('position_name') == pos],
                    key=lambda x: x.get('ai_score', 0),
                    reverse=True
                )
                starters.extend(pos_players[:count])
            
            # The score for this formation is the sum of the starters' AI scores.
            current_formation_score = sum(p.get('ai_score', 0) for p in starters)

            if current_formation_score > best_formation_score:
                best_formation_score = current_formation_score
        
        return best_formation_score

    def _crossover(self, parent1, parent2):
        """
        Performs a positional crossover between two parent squads.
        For each position, it combines the players from both parents and randomly selects
        the required number of players for the child's squad. This ensures the child
        always has the correct number of players in each position.
        """
        child = []
        for pos, count in SQUAD_RULES["POSITIONS"].items():
            p1_pos = [p for p in parent1 if p['position_name'] == pos]
            p2_pos = [p for p in parent2 if p['position_name'] == pos]
            
            # Combine genes from both parents using player IDs to ensure uniqueness
            unique_players = {p['id']: p for p in p1_pos + p2_pos}
            combined_genes = list(unique_players.values())
            
            if len(combined_genes) >= count:
                child.extend(random.sample(combined_genes, count))
            else:
                # If not enough unique players, take what we have and fill randomly
                child.extend(combined_genes)
                needed = count - len(combined_genes)
                available = [p for p in self.positions[pos] if p not in child]
                if len(available) >= needed:
                    child.extend(random.sample(available, needed))
                else: # Failsafe
                    return None
        return child
        
    def _mutate(self, squad):
        """
        Mutates a squad by swapping out one of its weaker players
        for a new random player of the same position.
        """
        if not squad or len(squad) == 0:
            return squad

        # Bias mutation towards replacing weaker players
        squad.sort(key=lambda p: p.get('ai_score', 0))
        # Pick one of the bottom 5 players to replace
        idx_to_mutate = random.randint(0, min(4, len(squad) - 1))
        
        player_to_replace = squad[idx_to_mutate]
        position = player_to_replace['position_name']
        
        # Find a new player of the same position
        max_attempts = 100
        for _ in range(max_attempts):
            new_player = random.choice(self.positions[position])
            if new_player['id'] not in [p['id'] for p in squad]:
                squad[idx_to_mutate] = new_player
                return squad
        return squad # Return original if no replacement is found

    def run(self):
        """Runs the genetic algorithm to find the best possible squad."""
        # 1. Create the initial population
        population = []
        while len(population) < self.population_size:
            squad = self._create_random_squad()
            if squad:
                population.append(squad)

        if not population:
            raise Exception("Could not generate a valid initial population.")

        for _ in range(self.generations):
            # 2. Score the population
            fitness_scores = [(self._calculate_fitness(squad), squad) for squad in population]
            fitness_scores.sort(key=lambda x: x[0], reverse=True)
            
            next_generation = []
            
            # 3. Elitism: Carry over the best squads
            elites = [squad for _, squad in fitness_scores[:self.elite_size]]
            next_generation.extend(elites)
            
            # 4. Create the rest of the new generation through crossover and mutation
            mating_pool = [squad for _, squad in fitness_scores[:self.population_size // 2]]
            
            while len(next_generation) < self.population_size:
                parent1, parent2 = random.choices(mating_pool, k=2)
                child = self._crossover(parent1, parent2)
                
                if not child: continue

                # Mutate the child
                if random.random() < self.mutation_rate:
                    child = self._mutate(child)
                
                # If the child is invalid, try to repair it. If it can't be repaired, discard.
                if not self._is_valid(child):
                    child = self._repair_squad(child)
                    if not child:
                        continue

                next_generation.append(child)
            
            population = next_generation

        # Return the best squad from the final generation
        final_fitness_scores = [(self._calculate_fitness(squad), squad) for squad in population if squad]
        final_fitness_scores.sort(key=lambda x: x[0], reverse=True)
        
        return final_fitness_scores[0][1]

class SquadAnalyzer:
    """
    Analyzes a user's squad and suggests improvements.
    """
    def __init__(self, user_squad: List[Dict[str, Any]], all_players: List[Dict[str, Any]]):
        self.user_squad = user_squad
        self.all_players = all_players
        self.squad_player_ids = {p['id'] for p in user_squad}
        self.budget = sum(p['now_cost'] / 10 for p in user_squad)
        self.fixture_difficulty_map = create_fixture_difficulty_map()
        self.team_counts = Counter(p['team'] for p in user_squad)

        # Pre-calculate AI scores for all players
        for player in self.all_players:
            player['ai_score'] = self._calculate_ai_score(player)

        # Pre-calculate AI scores for the user's squad
        for player in self.user_squad:
            player['ai_score'] = self._calculate_ai_score(player)
            
    def _get_average_fixture_difficulty(self, player, num_games=5):
        """
        Calculates the average fixture difficulty for a player over the next N games.
        """
        team_name = player.get('team_name')
        if not team_name or team_name not in self.fixture_difficulty_map:
            return 3 # Return a neutral default difficulty if no data

        upcoming_fixtures = sorted(
            [f for f in self.fixture_difficulty_map[team_name] if f.get('gameweek')],
            key=lambda x: x['gameweek']
        )
        
        next_n_fixtures = upcoming_fixtures[:num_games]
        
        if not next_n_fixtures:
            return 3 

        total_difficulty = sum(f['difficulty'] for f in next_n_fixtures)
        return total_difficulty / len(next_n_fixtures)

    def _calculate_ai_score(self, player: Dict[str, Any]) -> float:
        """
        Calculates a player's AI score based on a weighted combination of their
        recent form, underlying stats (ICT index), and upcoming fixture difficulty.
        """
        # --- Weights for different factors ---
        form_weight = 0.4
        ict_weight = 0.4
        difficulty_weight = 0.2
        # ---

        form = float(player.get('form', 0))
        ict_index = float(player.get('ict_index', 0))
        
        # Normalize form and ICT to be on a similar scale (e.g., 0-10)
        # These max values are approximate and might need tuning.
        normalized_form = (form / 10) * 10
        normalized_ict = (ict_index / 400) * 10 
        
        # --- Fixture Difficulty Calculation ---
        # Lower difficulty is better, so we invert the logic.
        # A score of 1 is easiest, 5 is hardest. We want to reward easier fixtures.
        avg_difficulty = self._get_average_fixture_difficulty(player)
        
        # Scale from 1-5 to 0-1, where 1 is best (easiest fixtures)
        difficulty_score = (5 - avg_difficulty) / 4
        # ---
        
        # --- Final Weighted Score ---
        base_score = (normalized_form * form_weight) + (normalized_ict * ict_weight)
        final_score = base_score * (1 + (difficulty_score * difficulty_weight))
        # ---

        # Add a small bonus for players who play more minutes
        minutes_bonus = (player.get('minutes', 0) / 3420) * 2 # Max minutes ~3420
        final_score += minutes_bonus

        return round(final_score, 2)
        
    def _get_upcoming_fixtures(self, player, num_games=5):
        """
        Retrieves the next N upcoming fixtures for a player.
        """
        team_name = player.get('team_name')
        if not team_name or team_name not in self.fixture_difficulty_map:
            return []

        upcoming_fixtures = sorted(
            [f for f in self.fixture_difficulty_map[team_name] if f.get('gameweek')],
            key=lambda x: x['gameweek']
        )
        
        return upcoming_fixtures[:num_games]

    def suggest_captain(self):
        """Suggests the best captain and vice-captain for the upcoming gameweek."""
        sorted_squad = sorted(self.user_squad, key=lambda p: self._calculate_ai_score(p), reverse=True)
        
        captain = sorted_squad[0] if sorted_squad else None
        vice_captain = sorted_squad[1] if len(sorted_squad) > 1 else None
        
        return captain, vice_captain

    def _find_potential_replacements(self, player_out: Dict[str, Any], budget: float, excluded_ids: set) -> List[Dict[str, Any]]:
        """
        Finds all valid replacement players for a given player, respecting budget,
        team limits, and position constraints.
        """
        replacements = []
        position_to_fill = player_out['position_name']
        
        for player_in in self.all_players:
            # Basic checks: not the same player, correct position, not already in squad
            if player_in['id'] == player_out['id'] or player_in['id'] in excluded_ids:
                continue
            if player_in['position_name'] != position_to_fill:
                continue

            # Budget check
            if player_in['now_cost'] > budget:
                continue
            
            # Team limit check
            current_team_count = self.team_counts.get(player_in['team'], 0)
            if player_in['team'] == player_out['team']:
                if current_team_count > SQUAD_RULES['PLAYERS_PER_TEAM']:
                    continue
            elif current_team_count >= SQUAD_RULES['PLAYERS_PER_TEAM']:
                continue

            replacements.append(player_in)
            
        return replacements

    async def suggest_transfers(self, num_suggestions=5, reasoning_generator=None):
        """
        Suggests the top N single-player transfers based on the biggest AI score improvement.
        """
        # --- 1. Find the top N transfer candidates for each player in the user's squad ---
        all_potential_transfers = []
        for player_out in self.user_squad:
            # Re-calculate score in case it has been affected by other logic
            player_out['ai_score'] = self._calculate_ai_score(player_out)
            
            # Find potential replacements for this player
            potential_replacements = self._find_potential_replacements(player_out, player_out['now_cost'], self.squad_player_ids)
            
            for player_in in potential_replacements:
                # Re-calculate score for incoming player
                player_in['ai_score'] = self._calculate_ai_score(player_in)

                score_gain = player_in['ai_score'] - player_out['ai_score']
                if score_gain > 0:
                    # --- Attach fixture data for reasoning ---
                    player_out['upcoming_fixtures'] = self._get_upcoming_fixtures(player_out)
                    player_in['upcoming_fixtures'] = self._get_upcoming_fixtures(player_in)
                    # ---
                    all_potential_transfers.append({
                        "player_out": player_out,
                        "player_in": player_in,
                        "score_gain": score_gain
                    })

        # --- 2. Sort all possible transfers by score gain and get the top N ---
        sorted_transfers = sorted(all_potential_transfers, key=lambda x: x['score_gain'], reverse=True)
        
        # --- 3. Filter out transfers that would result in an invalid squad ---
        # This logic is simplified; a full validation would check all rules.
        # Here we just ensure we don't suggest swapping for a player already involved
        # in another, better transfer.
        final_suggestions = []
        used_player_ids = set()

        for transfer in sorted_transfers:
            if len(final_suggestions) >= num_suggestions:
                break
            
            p_out_id = transfer['player_out']['id']
            p_in_id = transfer['player_in']['id']

            if p_out_id not in used_player_ids and p_in_id not in used_player_ids:
                final_suggestions.append(transfer)
                used_player_ids.add(p_out_id)
                used_player_ids.add(p_in_id)

        # --- 4. Generate AI reasoning for the top suggestions ---
        if reasoning_generator:
            reasoning_tasks = [
                reasoning_generator(suggestion['player_out'], suggestion['player_in'])
                for suggestion in final_suggestions
            ]
            reasons = await asyncio.gather(*reasoning_tasks)
            for i, reason in enumerate(reasons):
                final_suggestions[i]['reason'] = reason
                
        return final_suggestions

    async def suggest_double_transfers(self, reasoning_generator=None):
        """
        Suggests the single best 2-for-2 transfer to maximize squad score.
        This is computationally expensive, so it's heavily optimized.
        """
        # --- 1. Identify the two weakest players in each position as candidates for transfer ---
        weakest_players = sorted(self.user_squad, key=lambda p: self._calculate_ai_score(p))[:8]

        best_double_transfer = None
        highest_score_gain = 0

        # Iterate through every possible pair of weak players to transfer out
        for p_out1, p_out2 in itertools.combinations(weakest_players, 2):
            
            squad_positions = self._get_squad_positions()
            if p_out1['position_name'] == p_out2['position_name'] and squad_positions[p_out1['position_name']] <= SQUAD_RULES['POSITIONS'][p_out1['position_name']] - 1:
                 continue

            # --- 2. Find the best replacements for this pair ---
            budget_for_replacements = (p_out1['now_cost'] + p_out2['now_cost'])

            # Find candidates for each player being transferred out
            candidates1 = self._find_potential_replacements(p_out1, budget_for_replacements, self.squad_player_ids - {p_out2['id']})
            
            # If we find a good replacement for p_out1, find a partner for p_out2
            if candidates1:
                # Take the top 5 candidates for the first player
                for p_in1 in sorted(candidates1, key=lambda p: self._calculate_ai_score(p), reverse=True)[:5]:
                    
                    remaining_budget = budget_for_replacements - p_in1['now_cost']
                    
                    # Now find the best partner for p_out2 with the remaining budget
                    candidates2 = self._find_potential_replacements(p_out2, remaining_budget, self.squad_player_ids - {p_out1['id'], p_in1['id']})
                    
                    if candidates2:
                        p_in2 = max(candidates2, key=lambda p: self._calculate_ai_score(p))
                        
                        # Calculate the net gain from this double transfer
                        original_score = self._calculate_ai_score(p_out1) + self._calculate_ai_score(p_out2)
                        new_score = self._calculate_ai_score(p_in1) + self._calculate_ai_score(p_in2)
                        score_gain = new_score - original_score

                        if score_gain > highest_score_gain:
                            highest_score_gain = score_gain
                            # --- Attach fixture data for reasoning ---
                            p_out1['upcoming_fixtures'] = self._get_upcoming_fixtures(p_out1)
                            p_out2['upcoming_fixtures'] = self._get_upcoming_fixtures(p_out2)
                            p_in1['upcoming_fixtures'] = self._get_upcoming_fixtures(p_in1)
                            p_in2['upcoming_fixtures'] = self._get_upcoming_fixtures(p_in2)
                            # ---
                            best_double_transfer = ([p_out1, p_out2], [p_in1, p_in2])

        if not best_double_transfer:
            return None

        players_out, players_in = best_double_transfer
        
        reason = None
        if reasoning_generator:
            # Generate a combined reason for the double transfer
            reasoning_tasks = [
                reasoning_generator(p_out, p_in) 
                for p_out, p_in in zip(players_out, players_in)
            ]
            reasons = await asyncio.gather(*reasoning_tasks)
            reason = " & ".join(filter(None, reasons))
            
        return {
            "players_out": players_out,
            "players_in": players_in,
            "score_gain": round(highest_score_gain, 2),
            "reason": reason
        }

    def _get_squad_positions(self) -> Dict[str, int]:
        """Counts the number of players in each position in the squad."""
        return Counter(p['position_name'] for p in self.user_squad)

    def _get_squad_teams(self) -> Dict[int, int]:
        """Counts the number of players from each team in the squad."""
        return Counter(p['team'] for p in self.user_squad)

class FPLData(BaseModel):
    """Pydantic model for validating the basic FPL data structure."""
    events: List[Any]
    teams: List[Any]
    elements: List[Any]
    element_types: List[Any] 