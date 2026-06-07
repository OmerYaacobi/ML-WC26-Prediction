import pandas as pd
from pathlib import Path
from src.data_layers.history_loader import HistoryDataLoader
from src.data_layers.squad_loader import SquadDataLoader
from src.data_layers.market_loader import MarketOddsLoader

class FeaturePipeline:
    def __init__(self):
        self.processed_dir = Path(__file__).resolve().parents[2] / "data" / "processed"
        self.output_path = self.processed_dir / "blended_model_features.csv"
        
        self.history_loader = HistoryDataLoader()
        self.squad_loader = SquadDataLoader()
        self.market_loader = MarketOddsLoader()

    def normalize_series(self, series, invert=False):
        if series.max() == series.min():
            return series.apply(lambda x: 1.0)
        
        if invert:
            normalized = (series.max() - series) / (series.max() - series.min())
        else:
            normalized = (series - series.min()) / (series.max() - series.min())
            
        return 0.1 + (normalized * 1.4)

    def run_blender_pipeline(self):
        print("\n--- Running Layer 2 Feature Pipeline: Blending Data Matrix ---")
        
        df_hist = self.history_loader.load_historical_metrics()
        df_squad = self.squad_loader.load_squad_ratings()
        df_market = self.market_loader.fetch_live_odds() # Our upgraded dataframe!

        if df_squad.empty:
            raise ValueError("Pipeline Aborted: Master squad configuration matrix is empty.")
            
        master_df = df_squad.copy()

        if not df_hist.empty:
            master_df = master_df.merge(df_hist, on="team", how="left")
        else:
            master_df["hist_attack"] = 1.0
            master_df["hist_defense"] = 1.0

        master_df["hist_attack"] = master_df["hist_attack"].fillna(master_df["hist_attack"].mean() if not df_hist.empty else 1.0)
        master_df["hist_defense"] = master_df["hist_defense"].fillna(master_df["hist_defense"].mean() if not df_hist.empty else 1.0)

        master_df["norm_hist_att"] = self.normalize_series(master_df["hist_attack"])
        master_df["norm_hist_def"] = self.normalize_series(master_df["hist_defense"], invert=True)
        master_df["norm_squad"] = self.normalize_series(master_df["squad_rating"])

        records = []
        for idx, row in master_df.iterrows():
            team_name = row["team"]
            
            # Safe defaults in case a team isn't on the bookies' boards yet
            market_multiplier = 1.0
            market_win_prob = 0.33
            market_proj_gf = 1.0
            market_proj_ga = 1.0
            market_btts_prob = 0.5
            market_ou_prob = 0.5

            # Extract the advanced metrics
            if team_name in df_market.index:
                market_multiplier = df_market.loc[team_name, "market_active"]
                market_win_prob = df_market.loc[team_name, "market_win_prob"]
                market_proj_gf = df_market.loc[team_name, "market_proj_gf"]
                market_proj_ga = df_market.loc[team_name, "market_proj_ga"]
                market_btts_prob = df_market.loc[team_name, "market_btts_prob"]
                market_ou_prob = df_market.loc[team_name, "market_over_25_prob"]
            
            # --- NEW OPTIMIZED WEIGHTS ---
            w_hist = 0.205
            w_squad = 0.432
            w_market = 0.334
            
            # Blended Calculations using the optimal formula
            # Note: We use the exponent (**) for the market power as discovered by the optimizer
            final_attack = ((row["norm_hist_att"] * w_hist) + (row["norm_squad"] * w_squad)) * (market_multiplier ** w_market)
            
            # Defense remains a combination of history and squad floor
            final_defense = (row["norm_hist_def"] * w_hist) + (row["norm_squad"] * w_squad) 
            final_defense_weakness = round(1.5 - final_defense + 0.1, 3)

            # Append EVERYTHING to the final CSV
            records.append({
                "team": team_name,
                "attack_strength": round(final_attack, 3),
                "defense_weakness": max(0.1, final_defense_weakness),
                "squad_rating": row["squad_rating"],
                "market_win_prob": market_win_prob,
                "market_proj_gf": market_proj_gf,
                "market_proj_ga": market_proj_ga,
                "market_btts_prob": market_btts_prob,
                "market_over_25_prob": market_ou_prob
            })

        blended_df = pd.DataFrame(records)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        blended_df.to_csv(self.output_path, index=False)
        
        print(f"✅ Pipeline complete. Clean, non-repetitive feature matrix saved to: {self.output_path}")
        return blended_df

if __name__ == "__main__":
    pipeline = FeaturePipeline()
    pipeline.run_blender_pipeline()