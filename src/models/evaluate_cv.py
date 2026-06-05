import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import KFold
from src.models.poisson_engine import PoissonPredictionEngine

class MarketCrossValidator:
    def __init__(self):
        self.raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
        self.processed_dir = Path(__file__).resolve().parents[2] / "data" / "processed"
        
        self.odds_file = self.raw_dir / "market_odds_group_stage.json"
        self.features_file = self.processed_dir / "blended_model_features.csv"
        
        self.poisson = PoissonPredictionEngine()
        
        if not self.odds_file.exists() or not self.features_file.exists():
            raise FileNotFoundError("Missing required data files. Ensure Layer 1 & 2 are completed.")
            
        self.team_features = pd.read_csv(self.features_file).set_index("team")

    def decode_bet365_target(self, match_markets):
        """Extracts the true Expected Goals (xG) from Bet365 Correct Score odds."""
        cs_market = next((m for m in match_markets if m.get("name") == "Correct Score"), None)
        if not cs_market or not cs_market.get("odds"):
            return None, None

        raw_probs = []
        parsed_scores = []

        # Step 1: Calculate raw probabilities
        for outcome in cs_market["odds"]:
            label = outcome.get("label", "")
            odds = float(outcome.get("odds", 999))
            
            if "-" in label:
                try:
                    hg, ag = map(int, label.split("-"))
                    prob = 1.0 / odds
                    raw_probs.append(prob)
                    parsed_scores.append((hg, ag))
                except ValueError:
                    continue

        if not raw_probs:
            return None, None

        # Step 2: Normalize to remove the bookmaker margin (Vig)
        total_prob = sum(raw_probs)
        norm_probs = [p / total_prob for p in raw_probs]

        # Step 3: Calculate the weighted average expected score
        market_xg_home = sum(hg * p for (hg, ag), p in zip(parsed_scores, norm_probs))
        market_xg_away = sum(ag * p for (hg, ag), p in zip(parsed_scores, norm_probs))

        return market_xg_home, market_xg_away

    def run_6_fold_cv(self):
        print("\n" + "="*60)
        print("🎯 RUNNING 6-FOLD MARKET CROSS-VALIDATION")
        print("="*60)

        with open(self.odds_file, "r") as f:
            raw_matches = json.load(f)

        valid_matches = []
        for match in raw_matches:
            home = match.get("home")
            away = match.get("away")
            markets = match.get("bookmakers", {}).get("Bet365", [])
            
            if home in self.team_features.index and away in self.team_features.index:
                bookie_xg_h, bookie_xg_a = self.decode_bet365_target(markets)
                if bookie_xg_h is not None:
                    valid_matches.append({
                        "home": home,
                        "away": away,
                        "bookie_xg_h": bookie_xg_h,
                        "bookie_xg_a": bookie_xg_a
                    })

        match_df = pd.DataFrame(valid_matches)
        
        # Initialize K-Fold (6 groups)
        kf = KFold(n_splits=6, shuffle=True, random_state=42)
        
        fold_errors = []
        
        for fold, (train_idx, test_idx) in enumerate(kf.split(match_df), 1):
            test_batch = match_df.iloc[test_idx]
            batch_error = []
            
            for _, row in test_batch.iterrows():
                h_stats = self.team_features.loc[row["home"]].to_dict()
                h_stats["squad_rating"] = self.team_features.loc[row["home"], "squad_rating"]
                
                a_stats = self.team_features.loc[row["away"]].to_dict()
                a_stats["squad_rating"] = self.team_features.loc[row["away"], "squad_rating"]

                # Run our mathematical model
                our_result = self.poisson.calculate_match_probabilities(h_stats, a_stats)
                our_xg_h, our_xg_a = our_result["lambdas"]

                # Calculate absolute divergence from the market
                error_h = abs(our_xg_h - row["bookie_xg_h"])
                error_a = abs(our_xg_a - row["bookie_xg_a"])
                
                batch_error.extend([error_h, error_a])

            # Calculate Mean Absolute Error (MAE) for this fold
            fold_mae = np.mean(batch_error)
            fold_errors.append(fold_mae)
            
            print(f"📂 Fold {fold}/6 | Tested {len(test_batch)} matches | MAE (xG Divergence): {fold_mae:.3f} goals")

        final_mae = np.mean(fold_errors)
        print("-" * 60)
        print(f"✅ CROSS-VALIDATION COMPLETE")
        print(f"📊 Global Model Divergence vs Bet365: ±{final_mae:.3f} Goals per Team")
        
        if final_mae < 0.25:
            print("🔥 Assessment: ELITE. Your model is highly calibrated to global market consensus.")
        elif final_mae < 0.45:
            print("👍 Assessment: STRONG. The math is tracking closely with professional oddsmakers.")
        else:
            print("⚠️ Assessment: HIGH VARIANCE. Consider tuning the weights in your Feature Pipeline.")
        print("="*60 + "\n")

if __name__ == "__main__":
    cv_engine = MarketCrossValidator()
    cv_engine.run_6_fold_cv()