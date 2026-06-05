import numpy as np
from src.models.train_poisson import WorldCupPredictor

class BettingValidator:
    def __init__(self):
        self.predictor = WorldCupPredictor()

    def validate_against_market(self, team_a, team_b, odds_a, odds_draw, odds_b):
        """
        Converts bookmaker decimal odds into true implied probabilities 
        by removing the overround (juice), then compares them to our model.
        """
        # 1. Calculate raw implied probabilities from odds (Prob = 1 / Odds)
        raw_prob_a = 1 / odds_a
        raw_prob_draw = 1 / odds_draw
        raw_prob_b = 1 / odds_b
        
        # The sum of raw betting percentages always exceeds 100% (this is the bookie's profit margin)
        total_market_margin = raw_prob_a + raw_prob_draw + raw_prob_b
        overround = (total_market_margin - 1.0) * 100
        
        # 2. Strip the juice to get the market's TRUE belief
        market_prob_a = raw_prob_a / total_market_margin
        market_prob_draw = raw_prob_draw / total_market_margin
        market_prob_b = raw_prob_b / total_market_margin

        # 3. Fetch our Poisson model's predictions
        score_matrix = self.predictor.predict_match(team_a, team_b)
        if score_matrix is None:
            return

        model_prob_a = np.sum(np.tril(score_matrix, -1))
        model_prob_draw = np.sum(np.diag(score_matrix))
        model_prob_b = np.sum(np.triu(score_matrix, 1))

        # 4. Print Comparison Report
        print(f"📊 MARKET VALIDATION REPORT: {team_a} vs {team_b}")
        print(f"   Bookmaker Margin (Juice): {overround:.2f}%")
        print(f"{'-'*55}")
        print(f"   Outcome      | Market True Prob | Our Model Prob | Edge / Value")
        print(f"{'-'*55}")
        
        for outcome, m_prob, model_prob, market_odds in [
            (f"{team_a} Win", market_prob_a, model_prob_a, odds_a),
            ("Draw      ", market_prob_draw, model_prob_draw, odds_draw),
            (f"{team_b} Win", market_prob_b, model_prob_b, odds_b)
        ]:
            # Value exists if our model says an event is MORE likely than the bookmaker thinks
            edge = model_prob - m_prob
            value_status = f"🟢 +{edge*100:.1f}% VALUE!" if edge > 0.03 else "🔴 No Value"
            print(f"   {outcome} | {m_prob*100:15.1f}% | {model_prob*100:13.1f}% | {value_status}")
        print(f"{'='*55}\n")

if __name__ == "__main__":
    validator = BettingValidator()
    
    # Example Test Case: 
    # Go to a betting site, grab real odds for a hypothetical match, and plug them in:
    # Let's pretend the bookie gives: Argentina (1.50), Draw (4.20), Algeria (6.50)
    #validator.validate_against_market("Argentina", "Algeria", odds_a=1.50, odds_draw=4.20, odds_b=6.50)
    
    # Let's test United States vs England with real-world style odds
    validator.validate_against_market("Mexico", "South Africa", odds_a=4/9, odds_draw=10/3, odds_b=6)