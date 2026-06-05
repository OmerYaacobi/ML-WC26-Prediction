import json
import numpy as np
import pandas as pd
from pathlib import Path

class TournamentSimulator:
    def __init__(self):
        self.processed_dir = Path(__file__).resolve().parents[2] / "data" / "processed"
        self.features_path = self.processed_dir / "final_model_features.csv"
        
        if not self.features_path.exists():
            raise FileNotFoundError("Master feature matrix missing. Run engineering.py first.")
            
        self.team_df = pd.read_csv(self.features_path).set_index("team")
        self.GLOBAL_BASE_XG = 1.27
        self.MATCH_PACE_BOOSTER = 1.0 

        # The Exact 2026 Group Alignments Provided by the User
        self.groups = {
            "Group A": ["Mexico", "South Africa", "South Korea", "Czechia"],
            "Group B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
            "Group C": ["Brazil", "Morocco", "Haiti", "Scotland"],
            "Group D": ["United States", "Paraguay", "Australia", "Turkey"],
            "Group E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
            "Group F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
            "Group G": ["Belgium", "Egypt", "Iran", "New Zealand"],
            "Group H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
            "Group I": ["France", "Senegal", "Iraq", "Norway"],
            "Group J": ["Argentina", "Algeria", "Austria", "Jordan"],
            "Group K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
            "Group L": ["England", "Croatia", "Ghana", "Panama"]
        }

    def simulate_match(self, team_a, team_b):
        """Simulates a match stochastically using its Poisson Lambda."""
        att_a = self.team_df.loc[team_a, "attack_strength"]
        def_a = self.team_df.loc[team_a, "defense_weakness"]
        squad_a = self.team_df.loc[team_a, "exact_squad_rating"]

        att_b = self.team_df.loc[team_b, "attack_strength"]
        def_b = self.team_df.loc[team_b, "defense_weakness"]
        squad_b = self.team_df.loc[team_b, "exact_squad_rating"]

        # Calculate Lambdas
        lambda_a = (self.GLOBAL_BASE_XG * att_a * def_b * (squad_a / squad_b)) * self.MATCH_PACE_BOOSTER
        lambda_b = (self.GLOBAL_BASE_XG * att_b * def_a * (squad_b / squad_a)) * self.MATCH_PACE_BOOSTER

        # Stochastic Sampling: Randomly pull a number out of the Poisson curve
        goals_a = np.random.poisson(lambda_a)
        goals_b = np.random.poisson(lambda_b)

        return goals_a, goals_b

    def simulate_single_group(self, group_name):
        """Simulates all 6 round-robin fixtures for a group and calculates standings."""
        teams = self.groups[group_name]
        
        # Initialize Table
        standings = {t: {"points": 0, "GF": 0, "GA": 0, "GD": 0} for t in teams}
        match_logs = []

        # Generate Round-Robin schedule (6 matches total)
        fixtures = [
            (teams[0], teams[1]), (teams[2], teams[3]),
            (teams[0], teams[2]), (teams[1], teams[3]),
            (teams[0], teams[3]), (teams[1], teams[2])
        ]

        for home, away in fixtures:
            gf, ga = self.simulate_match(home, away)
            match_logs.append(f"   ⚽ {home} {gf} - {ga} {away}")
            
            # Update goals
            standings[home]["GF"] += gf
            standings[home]["GA"] += ga
            standings[away]["GF"] += ga
            standings[away]["GA"] += gf
            
            # Allocate Points
            if gf > ga:
                standings[home]["points"] += 3
            elif ga > gf:
                standings[away]["points"] += 3
            else:
                standings[home]["points"] += 1
                standings[away]["points"] += 1

        # Calculate Goal Difference & Format DataFrame
        table_data = []
        for team, stats in standings.items():
            stats["GD"] = stats["GF"] - stats["GA"]
            table_data.append({"Team": team, **stats})
            
        df_table = pd.DataFrame(table_data)
        # Sort by Points, then Goal Difference, then Goals For (Standard FIFA Rules)
        df_table = df_table.sort_values(by=["points", "GD", "GF"], ascending=False).reset_index(drop=True)
        
        return match_logs, df_table

    def run_tournament_simulation(self, target_group=None):
        """Runs the entire tournament group stage simulation or focuses on one."""
        print(f"\n{'='*60}")
        print(f"🌍 2026 WORLD CUP MONTE CARLO SIMULATION")
        print(f"{'='*60}")
        
        groups_to_run = [target_group] if target_group else self.groups.keys()

        for g_name in groups_to_run:
            print(f"\n▶️ SIMULATING {g_name.upper()} FIXTURES:")
            logs, table = self.simulate_single_group(g_name)
            
            # Print match scores
            for log in logs:
                print(log)
                
            print(f"\n📊 FINAL STANDINGS {g_name.upper()}:")
            print(table.to_string(index=False))
            print(f"{'-'*60}")

if __name__ == "__main__":
    simulator = TournamentSimulator()
    
    # Leave empty to simulate all 12 groups, or type a specific group to test!
    simulator.run_tournament_simulation(target_group="Group A")
    #simulator.run_tournament_simulation(target_group="Group J")