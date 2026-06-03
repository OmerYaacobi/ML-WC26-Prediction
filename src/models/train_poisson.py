import pandas as pd
import numpy as np
from scipy.stats import poisson
from pathlib import Path

class WorldCupPredictor:
    def __init__(self):
        self.processed_dir = Path(__file__).resolve().parents[2] / "data" / "processed"
        self.features_path = self.processed_dir / "final_model_features.csv"
        
        if not self.features_path.exists():
            raise FileNotFoundError("Master feature matrix missing. Run engineering.py first.")
            
        # Load features and index by team name for instant lookup
        self.team_df = pd.read_csv(self.features_path).set_index("team")
        
        # The global baseline expected goals per team per match from our data
        self.GLOBAL_BASE_XG = 1.27

    def predict_match(self, team_a, team_b):
        """
        Calculates expected goals (Lambda) for both teams, generates a 
        probability score matrix, and extracts match outcomes.
        """
        if team_a not in self.team_df.index:
            print(f"❌ Error: '{team_a}' is not in your 48-team tournament universe.")
            return
        if team_b not in self.team_df.index:
            print(f"❌ Error: '{team_b}' is not in your 48-team tournament universe.")
            return

        # 1. Extract features from our processed database
        att_a = self.team_df.loc[team_a, "attack_strength"]
        def_a = self.team_df.loc[team_a, "defense_weakness"]
        squad_a = self.team_df.loc[team_a, "exact_squad_rating"]

        att_b = self.team_df.loc[team_b, "attack_strength"]
        def_b = self.team_df.loc[team_b, "defense_weakness"]
        squad_b = self.team_df.loc[team_b, "exact_squad_rating"]

        # 2. Compute the Live Squad Quality Multipliers
        squad_mod_a = squad_a / squad_b
        squad_mod_b = squad_b / squad_a

        # 3. Calculate Expected Goals (Lambda) for each team
        lambda_a = self.GLOBAL_BASE_XG * att_a * def_b * squad_mod_a
        lambda_b = self.GLOBAL_BASE_XG * att_b * def_a * squad_mod_b

        # 4. Generate the Joint Probability Score Matrix (up to 6 goals each)
        max_goals = 7
        score_matrix = np.zeros((max_goals, max_goals))
        
        best_score = (0, 0)
        max_score_prob = 0.0

        for g_a in range(max_goals):
            for g_b in range(max_goals):
                # Probability of Team A scoring g_a AND Team B scoring g_b
                prob = poisson.pmf(g_a, lambda_a) * poisson.pmf(g_b, lambda_b)
                score_matrix[g_a, g_b] = prob
                
                if prob > max_score_prob:
                    max_score_prob = prob
                    best_score = (g_a, g_b)

        # 5. Aggregate Matrix Quadrants into Clean Match Probabilities
        win_a_prob = np.sum(np.tril(score_matrix, -1))  # Below the diagonal axis
        draw_prob = np.sum(np.diag(score_matrix))       # The exact diagonal line
        win_b_prob = np.sum(np.triu(score_matrix, 1))   # Above the diagonal axis

        # 6. Display the Prediction Report
        print(f"\n{'='*55}")
        print(f"🏆 MATCH FORECAST: {team_a} vs {team_b}")
        print(f"{'='*55}")
        print(f"📊 Expected Goals (xG):")
        print(f"   ⚽ {team_a}: {lambda_a:.2f} xG")
        print(f"   ⚽ {team_b}: {lambda_b:.2f} xG\n")
        
        print(f"📈 Match Outcome Probabilities:")
        print(f"   🟢 {team_a} Win: {win_a_prob * 100:.1f}%")
        print(f"   🟡 Draw: {draw_prob * 100:.1f}%")
        print(f"   🔵 {team_b} Win: {win_b_prob * 100:.1f}%\n")
        
        print(f"🎯 MOST LIKELY EXACT SCORELINE:")
        print(f"   👉 {team_a} {best_score[0]} - {best_score[1]} {team_b} ({max_score_prob * 100:.1f}% confidence)")
        print(f"{'='*55}\n")
        
        return score_matrix

if __name__ == "__main__":
    predictor = WorldCupPredictor()
    
    # Test out group stage matchups or hypothetical dream fixtures from your universe!
    #predictor.predict_match("Argentina", "Algeria")
    #predictor.predict_match("United States", "England")
    predictor.predict_match("Brazil", "Morocco")