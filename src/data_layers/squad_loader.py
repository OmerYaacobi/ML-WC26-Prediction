import pandas as pd
from pathlib import Path

class SquadDataLoader:
    def __init__(self):
        self.processed_dir = Path(__file__).resolve().parents[2] / "data" / "processed"
        self.ratings_path = self.processed_dir / "exact_team_ratings.csv"

    def load_squad_ratings(self):
        """Loads processed live squad ratings and normalizes them against a global mean."""
        if not self.ratings_path.exists():
            print("⚠️ SquadDataLoader: exact_team_ratings.csv missing. Using defaults.")
            return pd.DataFrame(columns=["team", "squad_rating", "squad_metric"])
            
        df = pd.read_csv(self.ratings_path)
        
        # Ensure correct column naming convention
        if "exact_squad_rating" in df.columns:
            df = df.rename(columns={"exact_squad_rating": "squad_rating"})
            
        # Create a raw multiplier metric based around a typical standard tier rating of 75.0
        df["squad_metric"] = (df["squad_rating"] / 75.0).round(3)
        
        return df[["team", "squad_rating", "squad_metric"]]