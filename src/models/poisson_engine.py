import numpy as np
from scipy.stats import poisson

class PoissonPredictionEngine:
    def __init__(self):
        # High accuracy base target expectation per team 
        self.GLOBAL_BASE_XG = 2.236

    def calculate_match_probabilities(self, team_a_stats, team_b_stats):
        """
        Pure math function that takes team metrics dictionaries and
        returns a joint probability score matrix alongside outcome distributions.
        """
        att_a = team_a_stats["attack_strength"]
        def_a = team_a_stats["defense_weakness"]
        squad_a = team_a_stats["squad_rating"]

        att_b = team_b_stats["attack_strength"]
        def_b = team_b_stats["defense_weakness"]
        squad_b = team_b_stats["squad_rating"]

        # Calculate squad modifier scaling safely
        squad_mod_a = squad_a / squad_b
        squad_mod_b = squad_b / squad_a

        # Unified Lambdas
        lambda_a = self.GLOBAL_BASE_XG * att_a * def_b * squad_mod_a
        lambda_b = self.GLOBAL_BASE_XG * att_b * def_a * squad_mod_b

        # Build joint goal scoring distribution grid (0–9 goals; tail renormalized below)
        max_goals = 10
        score_matrix = np.zeros((max_goals, max_goals))
        
        best_score = (0, 0)
        max_score_prob = 0.0

        for g_a in range(max_goals):
            for g_b in range(max_goals):
                prob = poisson.pmf(g_a, lambda_a) * poisson.pmf(g_b, lambda_b)
                score_matrix[g_a, g_b] = prob
                
                if prob > max_score_prob:
                    max_score_prob = prob
                    best_score = (g_a, g_b)

        # Vectorized outcome summation
        win_a_prob = np.sum(np.tril(score_matrix, -1))
        draw_prob = np.sum(np.diag(score_matrix))
        win_b_prob = np.sum(np.triu(score_matrix, 1))

        total_prob = win_a_prob + draw_prob + win_b_prob
        if total_prob > 0:
            win_a_prob /= total_prob
            draw_prob /= total_prob
            win_b_prob /= total_prob

        return {
            "lambdas": (lambda_a, lambda_b),
            "probabilities": (win_a_prob, draw_prob, win_b_prob),
            "most_likely_score": best_score,
            "score_confidence": max_score_prob
        }