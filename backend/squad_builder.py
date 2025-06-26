import random
from collections import Counter
from typing import List, Dict, Any

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

    def _calculate_fitness(self, squad):
        """
        Calculates a squad's fitness based on a combination of the players'
        AI scores and the average difficulty of their upcoming fixtures.
        """
        if not squad:
            return 0
        
        best_formation_score = 0
        
        # For a given 15-player squad, find the best possible starting 11
        # by testing all valid formations.
        for formation in VALID_FORMATIONS:
            starters = []
            
            # Select the best players for the current formation
            for pos, count in formation.items():
                pos_players = sorted(
                    [p for p in squad if p.get('position_name') == pos],
                    key=lambda x: x.get('ai_score', 0),
                    reverse=True
                )
                starters.extend(pos_players[:count])
            
            # --- Calculate score for this formation's starters ---
            base_fitness = sum(p.get('ai_score', 0) for p in starters)
            
            total_difficulty = 0
            fixture_count = 0
            for p in starters:
                for f in p.get('upcoming_fixtures', []):
                    total_difficulty += f.get('difficulty', 3)
                    fixture_count += 1
            
            avg_difficulty = (total_difficulty / fixture_count) if fixture_count > 0 else 3
            difficulty_modifier = 1 - ((avg_difficulty - 1) / 4) * 0.2
            
            current_formation_score = base_fitness * difficulty_modifier
            # --- End score calculation ---

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
    def __init__(self, user_squad: List[Dict[str, Any]], all_players: List[Dict[str, Any]]):
        self.user_squad = user_squad
        self.user_squad_ids = {p['id'] for p in user_squad}
        self.all_players = [p for p in all_players if p['id'] not in self.user_squad_ids]
        self.squad_cost = sum(p['now_cost'] for p in user_squad)
        self.budget = 1000 # Use the total budget (100.0m * 10)

    def suggest_captain(self):
        """Suggests the player with the highest AI score as captain."""
        return max(self.user_squad, key=lambda p: p.get('ai_score', 0))

    def suggest_transfers(self, num_suggestions=5):
        """Finds the best unique single transfers to improve the squad's AI score."""
        potential_transfers = []

        for player_out in self.user_squad:
            # Calculate the budget we would have for a replacement
            new_budget = self.budget - (self.squad_cost - player_out['now_cost'])
            
            for player_in in self.all_players:
                # Basic checks: same position, affordable
                if player_in['position_name'] != player_out['position_name']:
                    continue
                if player_in['now_cost'] > new_budget:
                    continue

                # Check team constraint: can't have more than 3 from the same team
                team_counts = {}
                for p in self.user_squad:
                    if p['id'] != player_out['id']:
                      team_counts[p['team']] = team_counts.get(p['team'], 0) + 1
                
                team_counts[player_in['team']] = team_counts.get(player_in['team'], 0) + 1
                if team_counts[player_in['team']] > 3:
                    continue

                # This is a valid transfer, calculate the benefit
                score_gain = player_in.get('ai_score', 0) - player_out.get('ai_score', 0)
                if score_gain > 0:
                    potential_transfers.append({
                        "player_out": player_out,
                        "player_in": player_in,
                        "score_gain": score_gain,
                    })
        
        # Sort by the highest score gain
        potential_transfers.sort(key=lambda x: x['score_gain'], reverse=True)
        
        # Filter to get unique 1-to-1 suggestions
        final_suggestions = []
        used_player_ids = set()

        for transfer in potential_transfers:
            player_out_id = transfer['player_out']['id']
            player_in_id = transfer['player_in']['id']

            if player_out_id not in used_player_ids and player_in_id not in used_player_ids:
                final_suggestions.append(transfer)
                used_player_ids.add(player_out_id)
                used_player_ids.add(player_in_id)
            
            if len(final_suggestions) >= num_suggestions:
                break
        
        return final_suggestions 