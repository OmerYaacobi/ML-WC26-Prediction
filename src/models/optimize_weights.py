
import json
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.optimize import minimize
from src.data_layers.history_loader import HistoryDataLoader
from src.data_layers.squad_loader import SquadDataLoader
from src.data_layers.market_loader import MarketOddsLoader

class HyperparameterOptimizer:
    def __init__(self):
        print("⚙️ Initializing Optimization Engine...")
        self.raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
        self.odds_file = self.raw_dir / "market_odds_group_stage.json"
        
        # Load Layer 1 Data Frames
        self.history_loader = HistoryDataLoader()
        self.squad_loader = SquadDataLoader()
        self.market_loader = MarketOddsLoader()
        
        self.df_hist = self.history_loader.load_historical_metrics()
        self.df_squad = self.squad_loader.load_squad_ratings()
        self.df_market = self.market_loader.fetch_live_odds()
        
        self.raw_features = self._prep_raw_features()
        self.match_targets = self._prep_match_targets()

    def normalize_series(self, series, invert=False):
        if series.max() == series.min():
            return series.apply(lambda x: 1.0)
        if invert:
            normalized = (series.max() - series) / (series.max() - series.min())
        else:
            normalized = (series - series.min()) / (series.max() - series.min())
        return 0.1 + (normalized * 1.4)

    def _prep_raw_features(self):
        """Pre-calculates all the normalized boundaries so the optimizer loop runs instantly."""
        master_df = self.df_squad.copy()
        if not self.df_hist.empty:
            master_df = master_df.merge(self.df_hist, on="team", how="left")
        else:
            master_df["hist_attack"] = 1.0
            master_df["hist_defense"] = 1.0

        master_df["hist_attack"] = master_df["hist_attack"].fillna(master_df["hist_attack"].mean())
        master_df["hist_defense"] = master_df["hist_defense"].fillna(master_df["hist_defense"].mean())

        master_df["norm_hist_att"] = self.normalize_series(master_df["hist_attack"])
        master_df["norm_hist_def"] = self.normalize_series(master_df["hist_defense"], invert=True)
        master_df["norm_squad"] = self.normalize_series(master_df["squad_rating"])
        
        features_dict = {}
        for _, row in master_df.iterrows():
            team = row["team"]
            market_act = self.df_market.loc[team, "market_active"] if team in self.df_market.index else 1.0
            features_dict[team] = {
                "norm_hist_att": row["norm_hist_att"],
                "norm_hist_def": row["norm_hist_def"],
                "norm_squad": row["norm_squad"],
                "squad_rating": row["squad_rating"],
                "market_active": market_act
            }
        return features_dict

    def decode_bet365_target(self, match_markets):
        cs_market = next((m for m in match_markets if m.get("name") == "Correct Score"), None)
        if not cs_market or not cs_market.get("odds"): return None, None

        raw_probs, parsed_scores = [], []
        for outcome in cs_market["odds"]:
            label = outcome.get("label", "")
            odds = float(outcome.get("odds", 999))
            if "-" in label:
                try:
                    hg, ag = map(int, label.split("-"))
                    raw_probs.append(1.0 / odds)
                    parsed_scores.append((hg, ag))
                except ValueError:
                    continue

        if not raw_probs: return None, None
        
        total_prob = sum(raw_probs)
        norm_probs = [p / total_prob for p in raw_probs]
        
        market_xg_home = sum(hg * p for (hg, ag), p in zip(parsed_scores, norm_probs))
        market_xg_away = sum(ag * p for (hg, ag), p in zip(parsed_scores, norm_probs))
        return market_xg_home, market_xg_away

    def _prep_match_targets(self):
        """Extracts the true expected goals from the bookmaker JSON for our test set."""
        with open(self.odds_file, "r") as f:
            raw_matches = json.load(f)

        targets = []
        for match in raw_matches:
            home = match.get("home")
            away = match.get("away")
            markets = match.get("bookmakers", {}).get("Bet365", [])
            
            if home in self.raw_features and away in self.raw_features:
                xg_h, xg_a = self.decode_bet365_target(markets)
                if xg_h is not None:
                    targets.append({"home": home, "away": away, "xg_h": xg_h, "xg_a": xg_a})
        return targets

    def objective_function(self, params):
        """
        The math engine evaluated thousands of times per second.
        params = [weight_history, weight_squad, market_power, base_xg]
        """
        w_hist, w_squad, w_market, base_xg = params
        
        # Dynamically balance history and squad weights
        total_w = w_hist + w_squad
        if total_w == 0: total_w = 0.001
        w_hist /= total_w
        w_squad /= total_w

        mae_list = []

        for match in self.match_targets:
            home, away = match["home"], match["away"]
            target_h, target_a = match["xg_h"], match["xg_a"]

            h_f = self.raw_features[home]
            a_f = self.raw_features[away]

            # Recalculate blended strengths using the experimental weights
            att_h = ((h_f["norm_hist_att"] * w_hist) + (h_f["norm_squad"] * w_squad)) * (h_f["market_active"] ** w_market)
            def_h = max(0.1, 1.5 - ((h_f["norm_hist_def"] * w_hist) + (h_f["norm_squad"] * w_squad)) + 0.1)

            att_a = ((a_f["norm_hist_att"] * w_hist) + (a_f["norm_squad"] * w_squad)) * (a_f["market_active"] ** w_market)
            def_a = max(0.1, 1.5 - ((a_f["norm_hist_def"] * w_hist) + (a_f["norm_squad"] * w_squad)) + 0.1)

            squad_mod_h = h_f["squad_rating"] / a_f["squad_rating"]
            squad_mod_a = a_f["squad_rating"] / h_f["squad_rating"]

            # Generate experimental Poisson Lambdas
            lambda_h = base_xg * att_h * def_a * squad_mod_h
            lambda_a = base_xg * att_a * def_h * squad_mod_a

            # Measure divergence
            mae_list.extend([abs(lambda_h - target_h), abs(lambda_a - target_a)])

        return np.mean(mae_list)

    def run_optimization(self):
        print("\n🚀 Commencing Hyperparameter Descent...")
        print(f"🎯 Ground Truth: {len(self.match_targets)} matches")
        
        # Initial guesses: [w_hist, w_squad, market_power, global_base_xg]
        initial_guess = [0.3, 0.4, 1.0, 1.32]
        
        # Logical boundaries to prevent the math from breaking
        bounds = [
            (0.01, 1.0),   # w_hist
            (0.01, 1.0),   # w_squad
            (0.1, 3.0),    # market_power
            (0.8, 2.0)     # global_base_xg
        ]

        result = minimize(
            self.objective_function, 
            initial_guess, 
            method="Nelder-Mead", 
            bounds=bounds,
            options={'disp': True, 'maxiter': 2000}
        )

        w_hist, w_squad, w_market, base_xg = result.x
        
        # Normalize the display weights
        total_w = w_hist + w_squad
        final_w_hist = w_hist / total_w
        final_w_squad = w_squad / total_w

        print("\n" + "="*50)
        print("🏆 OPTIMAL WEIGHTS DISCOVERED")
        print("="*50)
        print(f"📉 Initial Guessed MAE:  {self.objective_function(initial_guess):.4f}")
        print(f"📉 Minimized Final MAE:  {result.fun:.4f}\n")
        print("UPDATE pipeline.py & poisson_engine.py WITH THESE VALUES:")
        print(f"   👉 History Weight:  {final_w_hist:.3f}")
        print(f"   👉 Squad Weight:    {final_w_squad:.3f}")
        print(f"   👉 Market Power:    {w_market:.3f}")
        print(f"   👉 GLOBAL_BASE_XG:  {base_xg:.3f}")
        print("="*50 + "\n")

if __name__ == "__main__":
    opt = HyperparameterOptimizer()
    opt.run_optimization()