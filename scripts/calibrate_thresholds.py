"""
Threshold Calibration Tool

Compares system output with ground truth data from standard datasets
to calibrate movement_rules.json thresholds.

Supported dataset formats:
    - Standard: frame, knee_angle, hip_angle, trunk_tibia_diff, knee_valgus_ratio, heel_lift, label
    - Kaggle Squat: left_knee_angle, right_knee_angle, left_hip_angle, right_hip_angle, torso_lean,
                    left_knee_lateral, right_knee_lateral, ankle_angles, label (auto-detected)

Usage:
    python scripts/calibrate_thresholds.py --data data/datasets/kaggle-squat/squat_dataset/squat_features_augmented.csv
    python scripts/calibrate_thresholds.py --data data/datasets/ui-prmd/ --analyze
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Label mapping for Kaggle Squat dataset
KAGGLE_LABEL_MAP = {
    0: "correct",
    1: "shallow_squat",
    2: "forward_lean",
    3: "knee_valgus",
    4: "heel_lift",
    5: "asymmetric",
}


def adapt_kaggle_squat(df):
    """Adapt Kaggle Squat dataset columns to standard format.

    Kaggle uses a complementary angle convention for knee/hip angles:
      - Kaggle: standing ~170-180°, deep squat ~50-70° (acute bend angle)
      - Our system: standing ~170-180°, deep squat ~70-115° (hip-knee-ankle angle)
    Conversion: our_angle = 180 - kaggle_angle

    Kaggle columns: left_knee_angle, right_knee_angle, left_hip_angle, right_hip_angle,
                    left_ankle_angle, right_ankle_angle, spine_angle, torso_lean,
                    left_knee_lateral, right_knee_lateral, symmetry_score, hip_depth,
                    video_file, frame, label
    """
    adapted = pd.DataFrame()
    adapted["frame"] = df["frame"]
    # Convert Kaggle's acute bend angles to our hip-knee-ankle convention
    adapted["knee_angle"] = 180 - (df["left_knee_angle"] + df["right_knee_angle"]) / 2
    adapted["hip_angle"] = 180 - (df["left_hip_angle"] + df["right_hip_angle"]) / 2
    adapted["trunk_tibia_diff"] = df["torso_lean"]
    adapted["knee_valgus_ratio"] = (df["left_knee_lateral"] + df["right_knee_lateral"]) / 2
    # Derive heel lift from ankle angle
    ankle_avg = (df["left_ankle_angle"] + df["right_ankle_angle"]) / 2
    adapted["heel_lift"] = np.clip((80 - ankle_avg) / 80, 0, 1)
    adapted["label"] = df["label"].map(KAGGLE_LABEL_MAP)
    return adapted


def detect_and_adapt(csv_path: str):
    """Detect dataset format and adapt to standard columns."""
    df = pd.read_csv(csv_path)

    # Check if it's Kaggle Squat format
    kaggle_cols = {"left_knee_angle", "right_knee_angle", "torso_lean", "left_knee_lateral"}
    if kaggle_cols.issubset(set(df.columns)):
        print(f"  [INFO] Detected Kaggle Squat format, adapting {len(df)} rows...")
        return adapt_kaggle_squat(df)

    # Check if it's already standard format
    required_cols = {"frame", "knee_angle", "label"}
    if required_cols.issubset(set(df.columns)):
        return df

    raise ValueError(f"Unknown dataset format. Columns: {list(df.columns)}")


def load_ground_truth(csv_path: str) -> Dict[str, np.ndarray]:
    """Load ground truth data from CSV file.

    Auto-detects Kaggle Squat format and adapts columns.
    Expected standard format:
        frame, knee_angle, hip_angle, trunk_tibia_diff, knee_valgus_ratio, heel_lift, label
    """
    df = detect_and_adapt(csv_path)

    return {
        "frames": df["frame"].values,
        "knee_angles": df["knee_angle"].values,
        "hip_angles": df["hip_angle"].values if "hip_angle" in df.columns else None,
        "trunk_tibia_diffs": df["trunk_tibia_diff"].values if "trunk_tibia_diff" in df.columns else None,
        "knee_valgus_ratios": df["knee_valgus_ratio"].values if "knee_valgus_ratio" in df.columns else None,
        "heel_lifts": df["heel_lift"].values if "heel_lift" in df.columns else None,
        "labels": df["label"].values,
    }


def load_current_thresholds(config_path: str = "configs/movement_rules.json") -> Dict:
    """Load current thresholds from config file."""
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config["movements"]["squat"]


def analyze_angle_distribution(angles: np.ndarray, label: str) -> Dict:
    """Analyze angle distribution for a specific label."""
    mask = ~np.isnan(angles)
    valid_angles = angles[mask]

    if len(valid_angles) == 0:
        return {}

    return {
        "label": label,
        "count": len(valid_angles),
        "mean": float(np.mean(valid_angles)),
        "std": float(np.std(valid_angles)),
        "min": float(np.min(valid_angles)),
        "max": float(np.max(valid_angles)),
        "percentile_5": float(np.percentile(valid_angles, 5)),
        "percentile_25": float(np.percentile(valid_angles, 25)),
        "percentile_50": float(np.percentile(valid_angles, 50)),
        "percentile_75": float(np.percentile(valid_angles, 75)),
        "percentile_95": float(np.percentile(valid_angles, 95)),
    }


def compare_with_thresholds(
    ground_truth: Dict,
    current_thresholds: Dict,
) -> Dict:
    """Compare ground truth data with current thresholds.

    Filters for squatting frames (knee_angle < 140°) to analyze bottom position
    thresholds, since datasets contain full movement sequences.
    """
    results = {
        "knee_angle": {},
        "knee_valgus": {},
        "heel_lift": {},
        "recommendations": [],
    }

    labels = ground_truth["labels"]
    knee_angles = ground_truth["knee_angles"]

    # Filter for squatting frames only (exclude near-standing frames)
    squatting_mask = knee_angles < 140

    # Analyze knee angles per label (squatting frames only)
    if knee_angles is not None:
        unique_labels = np.unique(labels)
        for label in unique_labels:
            mask = (labels == label) & squatting_mask
            angles = knee_angles[mask]
            stats = analyze_angle_distribution(angles, label)
            results["knee_angle"][label] = stats

    # Compare with current thresholds
    bottom_config = current_thresholds["states"]["bottom"]
    error_config = current_thresholds["error_thresholds"]

    # Check knee angle thresholds (support both "good" and "correct" labels)
    good_label = "good" if "good" in results["knee_angle"] else "correct"
    if good_label in results["knee_angle"]:
        good_stats = results["knee_angle"][good_label]
        current_min = bottom_config["knee_angle_min"]
        current_max = bottom_config["knee_angle_max"]

        # Use percentiles of squatting frames for bottom range
        if good_stats["percentile_5"] < current_min:
            results["recommendations"].append({
                "type": "knee_angle_min",
                "current": current_min,
                "suggested": max(good_stats["percentile_5"] - 5, 30),
                "reason": (
                    f"5% of correct squatting frames have knee angle < {good_stats['percentile_5']:.1f}°"
                ),
            })

        if good_stats["percentile_95"] > current_max:
            results["recommendations"].append({
                "type": "knee_angle_max",
                "current": current_max,
                "suggested": good_stats["percentile_95"] + 5,
                "reason": (
                    f"95% of correct squatting frames have knee angle < {good_stats['percentile_95']:.1f}°"
                ),
            })

    # Shallow squat threshold: find the angle that best separates correct from shallow
    if "shallow_squat" in results["knee_angle"] and good_label in results["knee_angle"]:
        shallow_stats = results["knee_angle"]["shallow_squat"]
        good_stats = results["knee_angle"][good_label]
        # Shallow squats have higher knee angles (less deep)
        suggested_shallow = (good_stats["mean"] + shallow_stats["mean"]) / 2
        current_shallow = error_config.get("shallow_squat_angle", 130)
        if abs(suggested_shallow - current_shallow) > 10:
            results["recommendations"].append({
                "type": "shallow_squat_angle",
                "current": current_shallow,
                "suggested": float(suggested_shallow),
                "reason": (
                    f"Correct squats mean depth: {good_stats['mean']:.1f}°, "
                    f"Shallow squats mean: {shallow_stats['mean']:.1f}°"
                ),
            })

    # Check knee valgus threshold
    if ground_truth["knee_valgus_ratios"] is not None:
        good_mask = np.isin(ground_truth["labels"], ["good", "correct"])
        bad_mask = np.isin(ground_truth["labels"], ["knee_valgus"])

        if np.any(good_mask) and np.any(bad_mask):
            good_ratios = ground_truth["knee_valgus_ratios"][good_mask]
            bad_ratios = ground_truth["knee_valgus_ratios"][bad_mask]

            current_threshold = error_config["knee_valgus_ratio"]

            # Find optimal threshold
            good_mean = np.mean(good_ratios)
            bad_mean = np.mean(bad_ratios)
            suggested = (good_mean + bad_mean) / 2

            results["knee_valgus"] = {
                "good_mean": float(good_mean),
                "bad_mean": float(bad_mean),
                "current_threshold": current_threshold,
                "suggested_threshold": float(suggested),
            }

            if abs(current_threshold - suggested) > 0.05:
                results["recommendations"].append({
                    "type": "knee_valgus_ratio",
                    "current": current_threshold,
                    "suggested": float(suggested),
                    "reason": f"Good squats avg: {good_mean:.2f}, Bad squats avg: {bad_mean:.2f}",
                })

    return results


def generate_calibration_report(results: Dict, output_path: str = "reports/calibration_report.json"):
    """Generate calibration report."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    report = {
        "timestamp": str(np.datetime64('now')),
        "analysis": results,
        "summary": {
            "total_recommendations": len(results["recommendations"]),
            "recommendations": results["recommendations"],
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n[INFO] Calibration report saved to: {output_path}")
    return report


def print_analysis(results: Dict):
    """Print analysis results to console."""
    print("\n" + "=" * 60)
    print("  Threshold Calibration Analysis")
    print("=" * 60)

    # Knee angle analysis
    print("\n[Knee Angle Distribution]")
    for label, stats in results["knee_angle"].items():
        print(f"\n  {label.upper()}:")
        print(f"    Count: {stats['count']}")
        print(f"    Mean: {stats['mean']:.1f}°")
        print(f"    Std: {stats['std']:.1f}°")
        print(f"    Range: [{stats['min']:.1f}°, {stats['max']:.1f}°]")
        print(f"    Percentiles: 5%={stats['percentile_5']:.1f}°, 50%={stats['percentile_50']:.1f}°, 95%={stats['percentile_95']:.1f}°")

    # Knee valgus analysis
    if results["knee_valgus"]:
        print("\n[Knee Valgus Ratio]")
        kv = results["knee_valgus"]
        print(f"  Good squats mean: {kv['good_mean']:.2f}")
        print(f"  Bad squats mean: {kv['bad_mean']:.2f}")
        print(f"  Current threshold: {kv['current_threshold']}")
        print(f"  Suggested threshold: {kv['suggested_threshold']:.2f}")

    # Recommendations
    print("\n[Recommendations]")
    if not results["recommendations"]:
        print("  No recommendations. Current thresholds look good!")
    else:
        for i, rec in enumerate(results["recommendations"], 1):
            print(f"\n  {i}. {rec['type']}:")
            print(f"     Current: {rec['current']}")
            print(f"     Suggested: {rec['suggested']}")
            print(f"     Reason: {rec['reason']}")


def apply_recommendations(
    config_path: str,
    recommendations: List[Dict],
    dry_run: bool = True,
):
    """Apply calibration recommendations to config file."""
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    squat_config = config["movements"]["squat"]

    changes_made = []

    for rec in recommendations:
        rec_type = rec["type"]
        suggested = rec["suggested"]

        if rec_type == "knee_angle_min":
            old_val = squat_config["states"]["bottom"]["knee_angle_min"]
            squat_config["states"]["bottom"]["knee_angle_min"] = suggested
            changes_made.append(f"bottom.knee_angle_min: {old_val} -> {suggested}")

        elif rec_type == "knee_angle_max":
            old_val = squat_config["states"]["bottom"]["knee_angle_max"]
            squat_config["states"]["bottom"]["knee_angle_max"] = suggested
            changes_made.append(f"bottom.knee_angle_max: {old_val} -> {suggested}")

        elif rec_type == "knee_valgus_ratio":
            old_val = squat_config["error_thresholds"]["knee_valgus_ratio"]
            squat_config["error_thresholds"]["knee_valgus_ratio"] = suggested
            changes_made.append(f"error_thresholds.knee_valgus_ratio: {old_val} -> {suggested}")

        elif rec_type == "shallow_squat_angle":
            old_val = squat_config["error_thresholds"]["shallow_squat_angle"]
            squat_config["error_thresholds"]["shallow_squat_angle"] = suggested
            changes_made.append(f"error_thresholds.shallow_squat_angle: {old_val} -> {suggested}")

    if dry_run:
        print("\n[DRY RUN] Changes that would be made:")
        for change in changes_made:
            print(f"  - {change}")
        print("\nUse --apply to actually apply changes.")
    else:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"\n[APPLIED] Changes saved to {config_path}")
        for change in changes_made:
            print(f"  - {change}")


def main():
    parser = argparse.ArgumentParser(
        description="Calibrate movement detection thresholds using ground truth data"
    )
    parser.add_argument(
        "--data",
        required=True,
        help="Path to ground truth CSV file or directory",
    )
    parser.add_argument(
        "--config",
        default="configs/movement_rules.json",
        help="Path to movement rules config file",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze data without applying changes",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply recommended changes to config",
    )
    parser.add_argument(
        "--report",
        default="reports/calibration_report.json",
        help="Path to save calibration report",
    )

    args = parser.parse_args()

    # Load ground truth data
    data_path = Path(args.data)
    if data_path.is_file():
        csv_files = [data_path]
    elif data_path.is_dir():
        csv_files = list(data_path.glob("**/*.csv"))
        if not csv_files:
            print(f"[ERROR] No CSV files found in {data_path}")
            return
    else:
        print(f"[ERROR] Data path not found: {data_path}")
        return

    # Process each CSV file
    all_results = []
    for csv_file in csv_files:
        print(f"\nProcessing: {csv_file}")
        try:
            ground_truth = load_ground_truth(str(csv_file))
            current_thresholds = load_current_thresholds(args.config)
            results = compare_with_thresholds(ground_truth, current_thresholds)
            all_results.append(results)
            print_analysis(results)
        except Exception as e:
            print(f"[ERROR] Failed to process {csv_file}: {e}")

    # Generate report
    if all_results:
        # Merge results from all files
        merged_results = {
            "knee_angle": {},
            "knee_valgus": {},
            "heel_lift": {},
            "recommendations": [],
        }

        for result in all_results:
            merged_results["recommendations"].extend(result["recommendations"])

        report = generate_calibration_report(merged_results, args.report)

        # Apply recommendations if requested
        if args.apply and merged_results["recommendations"]:
            apply_recommendations(
                args.config,
                merged_results["recommendations"],
                dry_run=False,
            )
        elif merged_results["recommendations"]:
            apply_recommendations(
                args.config,
                merged_results["recommendations"],
                dry_run=True,
            )


if __name__ == "__main__":
    main()
