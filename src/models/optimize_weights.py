import json
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.optimize import minimize
from sklearn.model_selection import KFold
from src.data_layers.history_loader import HistoryDataLoader
from src.data_layers.squad_loader import SquadDataLoader
from src.data_layers.market_loader import MarketOddsLoader

# Keep in sync with pipeline.py and poisson_engine.py defaults
DEFAULT_W_HIST = 0.200
DEFAULT_W_SQUAD = 0.430
DEFAULT_W_MARKET = 0.330
DEFAULT_BASE_XG = 2.240


class HyperparameterOptimizer:
    def __init__(self):
        print("⚙️ Initializing Optimization Engine...")
        self.raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
        self.odds_file = self.raw_dir / "market_odds_group_stage.json"

        self.history_loader = HistoryDataLoader()
        self.squad_loader = SquadDataLoader()
        self.market_loader = MarketOddsLoader()

        self.df_hist = self.history_loader.load_historical_metrics()
        self.df_squad = self.squad_loader.load_squad_ratings()
        self.df_market = self.market_loader.fetch_live_odds()

        self.master_df = self._prep_master_df()
        self.match_targets = self._prep_match_targets()

    def normalize_series(self, series, invert=False):
        if series.max() == series.min():
            return series.apply(lambda x: 1.0)
        if invert:
            normalized = (series.max() - series) / (series.max() - series.min())
        else:
            normalized = (series - series.min()) / (series.max() - series.min())
        return 0.1 + (normalized * 1.4)

    def _prep_master_df(self):
        master_df = self.df_squad.copy()
        if not self.df_hist.empty:
            master_df = master_df.merge(self.df_hist, on="team", how="left")
        else:
            master_df["hist_attack"] = 1.0
            master_df["hist_defense"] = 1.0

        master_df["hist_attack"] = master_df["hist_attack"].fillna(
            master_df["hist_attack"].mean() if not self.df_hist.empty else 1.0
        )
        master_df["hist_defense"] = master_df["hist_defense"].fillna(
            master_df["hist_defense"].mean() if not self.df_hist.empty else 1.0
        )

        master_df["norm_hist_att"] = self.normalize_series(master_df["hist_attack"])
        master_df["norm_hist_def"] = self.normalize_series(master_df["hist_defense"], invert=True)
        master_df["norm_squad"] = self.normalize_series(master_df["squad_rating"])
        return master_df

    def _blend_team_row(self, row, w_hist, w_squad, w_market):
        """Mirrors pipeline.py exactly: raw weights, rounded attack/defense."""
        team_name = row["team"]
        market_multiplier = 1.0
        if team_name in self.df_market.index:
            market_multiplier = self.df_market.loc[team_name, "market_active"]

        final_attack = (
            (row["norm_hist_att"] * w_hist) + (row["norm_squad"] * w_squad)
        ) * (market_multiplier ** w_market)

        final_defense = (row["norm_hist_def"] * w_hist) + (row["norm_squad"] * w_squad)
        final_defense_weakness = round(1.5 - final_defense + 0.1, 3)

        return {
            "attack_strength": round(final_attack, 3),
            "defense_weakness": max(0.1, final_defense_weakness),
            "squad_rating": row["squad_rating"],
        }

    def build_blended_features(self, w_hist, w_squad, w_market):
        return {
            row["team"]: self._blend_team_row(row, w_hist, w_squad, w_market)
            for _, row in self.master_df.iterrows()
        }

    @staticmethod
    def predict_lambdas(home_stats, away_stats, base_xg):
        """Mirrors poisson_engine.py lambda calculation."""
        squad_mod_h = home_stats["squad_rating"] / away_stats["squad_rating"]
        squad_mod_a = away_stats["squad_rating"] / home_stats["squad_rating"]

        lambda_h = base_xg * home_stats["attack_strength"] * away_stats["defense_weakness"] * squad_mod_h
        lambda_a = base_xg * away_stats["attack_strength"] * home_stats["defense_weakness"] * squad_mod_a
        return lambda_h, lambda_a

    def decode_bet365_target(self, match_markets):
        cs_market = next((m for m in match_markets if m.get("name") == "Correct Score"), None)
        if not cs_market or not cs_market.get("odds"):
            return None, None

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

        if not raw_probs:
            return None, None

        total_prob = sum(raw_probs)
        norm_probs = [p / total_prob for p in raw_probs]

        market_xg_home = sum(hg * p for (hg, ag), p in zip(parsed_scores, norm_probs))
        market_xg_away = sum(ag * p for (hg, ag), p in zip(parsed_scores, norm_probs))
        return market_xg_home, market_xg_away

    def _prep_match_targets(self):
        with open(self.odds_file, "r") as f:
            raw_matches = json.load(f)

        team_names = set(self.master_df["team"])
        targets = []
        for match in raw_matches:
            home = match.get("home")
            away = match.get("away")
            markets = match.get("bookmakers", {}).get("Bet365", [])

            if home in team_names and away in team_names:
                xg_h, xg_a = self.decode_bet365_target(markets)
                if xg_h is not None:
                    targets.append({"home": home, "away": away, "xg_h": xg_h, "xg_a": xg_a})
        return targets

    def _match_errors(self, blended_features, base_xg, matches):
        errors = []
        for match in matches:
            home_stats = blended_features[match["home"]]
            away_stats = blended_features[match["away"]]
            lambda_h, lambda_a = self.predict_lambdas(home_stats, away_stats, base_xg)
            errors.extend([
                abs(lambda_h - match["xg_h"]),
                abs(lambda_a - match["xg_a"]),
            ])
        return errors

    def full_mae(self, params):
        w_hist, w_squad, w_market, base_xg = params
        blended = self.build_blended_features(w_hist, w_squad, w_market)
        return np.mean(self._match_errors(blended, base_xg, self.match_targets))

    def cv_mae(self, params):
        """Same 6-fold CV metric reported by evaluate_cv.py."""
        w_hist, w_squad, w_market, base_xg = params
        blended = self.build_blended_features(w_hist, w_squad, w_market)
        match_df = pd.DataFrame(self.match_targets)
        kf = KFold(n_splits=6, shuffle=True, random_state=42)

        fold_errors = []
        for _, test_idx in kf.split(match_df):
            test_matches = match_df.iloc[test_idx].to_dict("records")
            fold_errors.append(np.mean(self._match_errors(blended, base_xg, test_matches)))

        return np.mean(fold_errors)

    def objective_function(self, params):
        return self.full_mae(params)

    def run_optimization(self):
        print("\n🚀 Commencing Hyperparameter Descent...")
        print(f"🎯 Ground Truth: {len(self.match_targets)} matches")
        print("📐 Using pipeline.py blending + poisson_engine.py lambdas (matches evaluate_cv)")

        initial_guess = [DEFAULT_W_HIST, DEFAULT_W_SQUAD, DEFAULT_W_MARKET, DEFAULT_BASE_XG]

        bounds = [
            (0.05, 0.80),   # w_hist   — raw pipeline weight
            (0.20, 0.90),   # w_squad  — raw pipeline weight
            (0.05, 0.80),   # w_market — market exponent
            (1.50, 3.00),   # global_base_xg
        ]

        print(f"\n📉 Baseline full-set MAE: {self.full_mae(initial_guess):.4f}")
        print(f"📉 Baseline 6-fold CV MAE: {self.cv_mae(initial_guess):.4f}  ← compare with evaluate_cv")

        result = minimize(
            self.objective_function,
            initial_guess,
            method="Nelder-Mead",
            bounds=bounds,
            options={"disp": True, "maxiter": 2000},
        )

        w_hist, w_squad, w_market, base_xg = result.x

        print("\n" + "=" * 50)
        print("🏆 OPTIMAL WEIGHTS DISCOVERED")
        print("=" * 50)
        print(f"📉 Optimized full-set MAE: {result.fun:.4f}")
        print(f"📉 Optimized 6-fold CV MAE: {self.cv_mae(result.x):.4f}  ← compare with evaluate_cv\n")
        print("UPDATE pipeline.py & poisson_engine.py WITH THESE VALUES:")
        print(f"   👉 History Weight:  {w_hist:.3f}")
        print(f"   👉 Squad Weight:    {w_squad:.3f}")
        print(f"   👉 Market Power:    {w_market:.3f}")
        print(f"   👉 GLOBAL_BASE_XG:  {base_xg:.3f}")
        print("=" * 50 + "\n")


if __name__ == "__main__":
    opt = HyperparameterOptimizer()
    opt.run_optimization()
