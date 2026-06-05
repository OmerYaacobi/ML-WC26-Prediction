import argparse
import pandas as pd
from pathlib import Path
from src.features.pipeline import FeaturePipeline
from src.models.poisson_engine import PoissonPredictionEngine

def main():
    parser = argparse.ArgumentParser(description="World Cup 2026 Core Predictor Engine Portal")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild the feature matrix using live API")
    parser.add_argument("--teamA", type=str, default="Brazil", help="Home Team Name")
    parser.add_argument("--teamB", type=str, default="France", help="Away Team Name")
    args = parser.parse_args()

    features_path = Path(__file__).resolve().parent / "data" / "processed" / "blended_model_features.csv"
    
    # Trigger feature build if matrix doesn't exist or --rebuild flag is provided
    if not features_path.exists() or args.rebuild:
        pipeline = FeaturePipeline()
        feature_df = pipeline.run_blender_pipeline()
    else:
        feature_df = pd.read_csv(features_path)

    feature_df = feature_df.set_index("team")
    
    # Check bounds
    if args.teamA not in feature_df.index or args.teamB not in feature_df.index:
        print(f"❌ Error: Either '{args.teamA}' or '{args.teamB}' is missing from the team definitions matrix.")
        return

    team_a_data = feature_df.loc[args.teamA].to_dict()
    team_a_data["squad_rating"] = feature_df.loc[args.teamA, "squad_rating"]
    
    team_b_data = feature_df.loc[args.teamB].to_dict()
    team_b_data["squad_rating"] = feature_df.loc[args.teamB, "squad_rating"]

    # Run Prediction Core Engine
    engine = PoissonPredictionEngine()
    result = engine.calculate_match_probabilities(team_a_data, team_b_data)

    # Print Clean, Pro Output Summary
    print(f"\n{'='*55}")
    print(f"🏆 MATCH PREDICTION ENGINE: {args.teamA} vs {args.teamB}")
    print(f"{'='*55}")
    print(f"📊 Calculated Expected Goals (xG):")
    print(f"   ⚽ {args.teamA}: {result['lambdas'][0]:.2f} xG")
    print(f"   ⚽ {args.teamB}: {result['lambdas'][1]:.2f} xG\n")
    
    print(f"📈 Match Outcome Distribution:")
    print(f"   🟢 {args.teamA} Win: {result['probabilities'][0] * 100:.1f}%")
    print(f"   🟡 Draw: {result['probabilities'][1] * 100:.1f}%")
    print(f"   🔵 {args.teamB} Win: {result['probabilities'][2] * 100:.1f}%\n")
    
    print(f"🎯 MOST LIKELY EXACT SCORELINE RESULT:")
    print(f"   👉 {args.teamA} {result['most_likely_score'][0]} - {result['most_likely_score'][1]} {args.teamB} ({result['score_confidence'] * 100:.1f}% confidence)")
    print(f"{'='*55}\n")

if __name__ == "__main__":
    main()