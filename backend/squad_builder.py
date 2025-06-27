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

class RandomSquadBuilder:
    def __init__(self, players, budget=100.0):
        self.players = players
        self.budget = budget
        self.positions = {pos: [] for pos in SQUAD_RULES["POSITIONS"].keys()}
        for p in self.players:
            pos_name = p.get('position_name')
            if pos_name in self.positions:
                self.positions[pos_name].append(p)

    def _is_valid(self, squad):
        """Checks if a squad is valid according to FPL rules."""
        if len(squad) != SQUAD_RULES["TOTAL_PLAYERS"]:
            return False

        if sum(p['now_cost'] / 10 for p in squad) > self.budget:
            return False

        team_counts = Counter(p['team'] for p in squad)
        if any(count > SQUAD_RULES["PLAYERS_PER_TEAM"] for count in team_counts.values()):
            return False

        position_counts = Counter(p['position_name'] for p in squad)
        for pos, count in SQUAD_RULES["POSITIONS"].items():
            if position_counts.get(pos, 0) != count:
                return False

        return True

    def build(self, attempts=2000):
        """
        Tries to build a random squad that is as close to the budget as possible.
        """
        best_squad = None
        best_cost = 0.0

        for _ in range(attempts):
            squad = []
            # This is a more robust way to build a squad respecting team limits from the start
            temp_positions = {pos: list(players) for pos, players in self.positions.items()}
            
            # Shuffle players within each position to ensure randomness
            for pos in temp_positions:
                random.shuffle(temp_positions[pos])

            # A bit of a greedy approach: try to pick more expensive players first
            for pos in temp_positions:
                temp_positions[pos].sort(key=lambda p: p['now_cost'], reverse=True)

            squad = self._generate_squad_from_positions(temp_positions)
            
            if squad and self._is_valid(squad):
                current_cost = sum(p['now_cost'] / 10 for p in squad)
                if current_cost > best_cost:
                    best_squad = squad
                    best_cost = current_cost
                    # If we hit the budget exactly or are very close, we can stop early.
                    if best_cost >= self.budget - 0.5:
                        break
        
        # If the greedy approach fails, fall back to a purely random one
        if not best_squad:
            for _ in range(attempts):
                squad = self._create_purely_random_squad()
                if self._is_valid(squad):
                    current_cost = sum(p['now_cost'] / 10 for p in squad)
                    if current_cost > best_cost:
                        best_squad = squad
                        best_cost = current_cost
                        if best_cost == self.budget:
                            break
        
        return best_squad

    def _generate_squad_from_positions(self, position_pool):
        squad = []
        team_counts = Counter()
        
        # Fill squad position by position
        for pos, count in SQUAD_RULES["POSITIONS"].items():
            added_in_pos = 0
            for player in position_pool[pos]:
                if added_in_pos == count:
                    break
                # Check if player is already in squad (shouldn't happen with good pools)
                # and if the team limit is not exceeded
                if player['id'] not in {p['id'] for p in squad} and \
                   team_counts[player['team']] < SQUAD_RULES["PLAYERS_PER_TEAM"]:
                    
                    squad.append(player)
                    team_counts[player['team']] += 1
                    added_in_pos += 1
            
            if added_in_pos < count:
                return None # Failed to form a valid squad
        
        return squad

    def _create_purely_random_squad(self):
        squad = []
        for pos, count in SQUAD_RULES["POSITIONS"].items():
            if len(self.positions[pos]) >= count:
                squad.extend(random.sample(self.positions[pos], count))
        return squad

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

        total_difficulty = sum(f.get('difficulty', 3) for f in next_n_fixtures)
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
        """
        The main entry point to run the genetic algorithm.
        Initializes a population and evolves it over a number of generations
        to find the best possible FPL squad.
        """
        # --- 1. Initialization ---
        population = []
        for _ in range(self.population_size):
            # Use the existing random squad creator and repair if needed
            squad = self._create_random_squad()
            if squad:
                population.append(squad)
        
        print(f"Initial population created with {len(population)} squads.")

        # --- 2. Evolution Loop ---
        for gen in range(self.generations):
            # Calculate fitness for the entire population
            fitness_scores = [self._calculate_fitness(squad) for squad in population]

            # --- 3. Selection ---
            # Combine population and scores for sorting
            pop_with_fitness = list(zip(population, fitness_scores))
            
            # Sort by fitness in descending order
            pop_with_fitness.sort(key=lambda x: x[1], reverse=True)
            
            # Elitism: Carry over the best squads to the next generation
            elites = [squad for squad, score in pop_with_fitness[:self.elite_size]]
            next_generation = elites

            # --- 4. Crossover & Mutation ---
            # Create the rest of the new generation through crossover
            num_offspring = self.population_size - self.elite_size
            
            # Select parents based on fitness (tournament selection could also work here)
            # For simplicity, we're using fitness-proportionate selection (roulette wheel)
            total_fitness = sum(fitness_scores)
            if total_fitness == 0: # Avoid division by zero if all fitnesses are 0
                selection_probs = None
            else:
                selection_probs = [score / total_fitness for score in fitness_scores]
            
            # Unzip population for random choices
            current_population = [squad for squad, score in pop_with_fitness]

            for _ in range(num_offspring):
                # Select two parents
                if selection_probs:
                    parent1, parent2 = random.choices(
                        current_population,
                        weights=selection_probs,
                        k=2
                    )
                else: # Fallback to random selection
                    parent1, parent2 = random.choices(current_population, k=2)

                # Crossover
                child = self._crossover(parent1, parent2)
                if not child: continue

                # Mutation
                if random.random() < self.mutation_rate:
                    child = self._mutate(child)
                
                # Repair if mutation or crossover made it invalid
                if not self._is_valid(child):
                    child = self._repair_squad(child)

                if child:
                    next_generation.append(child)
            
            population = next_generation
            
            # Optional: Print progress
            if (gen + 1) % 50 == 0:
                best_squad_so_far = pop_with_fitness[0][0]
                best_fitness = pop_with_fitness[0][1]
                squad_cost = sum(p['now_cost'] / 10 for p in best_squad_so_far)
                print(f"Generation {gen+1}/{self.generations} - Best Fitness: {best_fitness:.2f}, Squad Cost: £{squad_cost:.1f}m")

        # --- 5. Return Best Result ---
        final_fitness_scores = [self._calculate_fitness(squad) for squad in population]
        best_squad_index = max(range(len(final_fitness_scores)), key=final_fitness_scores.__getitem__)
        return population[best_squad_index]

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

        total_difficulty = sum(f.get('difficulty', 3) for f in next_n_fixtures)
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
        
    def _print_player_score_analysis(self, player: Dict[str, Any]):
        """
        Prints a detailed, formatted breakdown of a player's AI score calculation
        for debugging and transparency.
        """
        print(f"--- Analysis for {player.get('web_name', 'N/A')} ---")
        
        # Re-run calculation logic to print each step
        form_weight = 0.4
        ict_weight = 0.4
        difficulty_weight = 0.2

        form = float(player.get('form', 0))
        ict_index = float(player.get('ict_index', 0))
        
        normalized_form = (form / 10) * 10
        normalized_ict = (ict_index / 400) * 10 
        
        avg_difficulty = self._get_average_fixture_difficulty(player)
        difficulty_score = (5 - avg_difficulty) / 4
        
        base_score = (normalized_form * form_weight) + (normalized_ict * ict_weight)
        score_after_fixtures = base_score * (1 + (difficulty_score * difficulty_weight))
        
        minutes_bonus = (player.get('minutes', 0) / 3420) * 2
        final_score = score_after_fixtures + minutes_bonus

        print(f"  Base Stats       | Form: {form:.1f}, ICT Index: {ict_index:.1f}")
        print(f"  Fixture Analysis | Avg Difficulty: {avg_difficulty:.2f} -> Modifier: {1 + (difficulty_score * difficulty_weight):.3f}")
        print(f"  Calculated Score | Base: {base_score:.2f} | With Fixtures: {score_after_fixtures:.2f} | Bonus: +{minutes_bonus:.2f}")
        print(f"  >> Final AI Score: {final_score:.2f}")

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
                    
                    # --- DETAILED PRINT FOR COMPARISON ---
                    print("\n" + "="*80)
                    print(f"Found Potential Transfer: {player_out.get('web_name')} -> {player_in.get('web_name')} | Score Gain: +{score_gain:.2f}")
                    self._print_player_score_analysis(player_out)
                    self._print_player_score_analysis(player_in)
                    print("="*80)
                    # ---

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
        Suggests the best 2-for-2 transfer by identifying poor-value players and finding
        the optimal replacement pair that maximizes the entire squad's score.
        """
        print("\n--- Searching for Optimal Double Transfer ---")
        
        # --- 1. Identify players with poor value (low score for their cost) ---
        squad_with_value = []
        for p in self.user_squad:
            cost = p.get('now_cost', 1)
            score = p.get('ai_score', 0)
            value = score / (cost / 10) if cost > 0 else 0
            squad_with_value.append({**p, 'value': value})
        
        # Target the bottom 8 players by value for potential transfer
        poor_value_players = sorted(squad_with_value, key=lambda p: p['value'])[:8]
        print(f"Identifying poor-value players to transfer out: {[p['web_name'] for p in poor_value_players]}")

        best_double_transfer = None
        highest_gain = 0

        # --- 2. Iterate through pairs of poor-value players to find the best swap ---
        for p_out1, p_out2 in itertools.combinations(poor_value_players, 2):
            
            # --- 3. Determine the total budget freed up by selling these two players ---
            total_budget = p_out1['now_cost'] + p_out2['now_cost']
            
            # --- 4. Find the best possible individual replacements for each position ---
            # We search for the absolute best players we could afford for each slot
            # if we dedicated the entire budget to that one position.
            
            # Potential replacements for Player 1
            candidates1 = self._find_potential_replacements(p_out1, total_budget, self.squad_player_ids - {p_out2['id']})
            
            # Potential replacements for Player 2
            candidates2 = self._find_potential_replacements(p_out2, total_budget, self.squad_player_ids - {p_out1['id']})

            if not candidates1 or not candidates2:
                continue

            # --- 5. Find the optimal *pair* of replacements within the budget ---
            # This is the crucial step: instead of just finding one good player, we
            # find the best combination of two that fits the budget.
            
            for c1 in sorted(candidates1, key=lambda p: p['ai_score'], reverse=True)[:10]: # Top 10 candidates
                remaining_budget = total_budget - c1['now_cost']
                
                # Find the best partner for c1 from the second list of candidates
                best_partner = None
                for c2 in candidates2:
                    if c2['id'] != c1['id'] and c2['now_cost'] <= remaining_budget:
                        if best_partner is None or c2['ai_score'] > best_partner['ai_score']:
                            best_partner = c2
                
                if best_partner:
                    current_gain = (c1['ai_score'] + best_partner['ai_score']) - (p_out1['ai_score'] + p_out2['ai_score'])
                    
                    if current_gain > highest_gain:
                        highest_gain = current_gain
                        best_double_transfer = ([p_out1, p_out2], [c1, best_partner])
                        print(f"  New best pair found: ({p_out1['web_name']}, {p_out2['web_name']}) -> ({c1['web_name']}, {best_partner['web_name']}) | Gain: +{highest_gain:.2f}")

        if not best_double_transfer:
            print("--- No beneficial double transfer found. ---")
            return None

        # --- 6. Final processing and reasoning generation ---
        players_out, players_in = best_double_transfer
        
        # Attach fixture data for reasoning
        for p in players_out + players_in:
            p['upcoming_fixtures'] = self._get_upcoming_fixtures(p)

        print(f"\nOptimal Double Transfer Found: ({players_out[0]['web_name']}, {players_out[1]['web_name']}) -> ({players_in[0]['web_name']}, {players_in[1]['web_name']})")
        self._print_player_score_analysis(players_out[0])
        self._print_player_score_analysis(players_out[1])
        self._print_player_score_analysis(players_in[0])
        self._print_player_score_analysis(players_in[1])
        
        reason = None
        if reasoning_generator:
            reasoning_tasks = [
                reasoning_generator(p_out, p_in) 
                for p_out, p_in in zip(players_out, players_in)
            ]
            reasons = await asyncio.gather(*reasoning_tasks)
            reason = " & ".join(filter(None, reasons))
            
        return {
            "players_out": players_out,
            "players_in": players_in,
            "score_gain": round(highest_gain, 2),
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