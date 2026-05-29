"""
Standard Motion Dataset Download Script
Downloads public biomechanics datasets for threshold calibration.

Datasets:
1. UI-PRMD (University of Idaho - Physical Rehabilitation Movement Data)
2. Kaggle Squat Exercise Pose Dataset
3. AddBiomechanics Dataset (optional, large ~70GB)

Usage:
    python scripts/download_datasets.py --dataset all
    python scripts/download_datasets.py --dataset ui-prmd
    python scripts/download_datasets.py --dataset kaggle-squat
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


# Dataset configurations
DATASETS = {
    "ui-prmd": {
        "name": "UI-PRMD Dataset",
        "description": "10 subjects, 10 rehabilitation movements, 10 repetitions each",
        "size": "~500MB",
        "format": "CSV (joint coordinates)",
        "url": "https://www.kaggle.com/datasets/liza5757/uiprmd",
        "download_cmd": "kaggle datasets download -d liza5757/uiprmd",
        "extract_to": "data/datasets/ui-prmd",
    },
    "kaggle-squat": {
        "name": "Squat Exercise Pose Dataset",
        "description": "Squat quality assessment with joint angles from MediaPipe",
        "size": "~100MB",
        "format": "CSV (angles, labels)",
        "url": "https://www.kaggle.com/datasets/thashmiladewmini/squat-exercise-pose-dataset",
        "download_cmd": "kaggle datasets download -d thashmiladewmini/squat-exercise-pose-dataset",
        "extract_to": "data/datasets/kaggle-squat",
    },
    "addbiomechanics": {
        "name": "AddBiomechanics Dataset",
        "description": "273 subjects, 70+ hours, optical motion capture + force plates",
        "size": "~70GB",
        "format": "C3D, OSIM (OpenSim)",
        "url": "http://archive.simtk.org/addbiomechanics/addbiomechanics.zip",
        "download_cmd": "curl -o data/datasets/addbiomechanics.zip http://archive.simtk.org/addbiomechanics/addbiomechanics.zip",
        "extract_to": "data/datasets/addbiomechanics",
    },
}


def check_kaggle_cli():
    """Check if Kaggle CLI is installed."""
    try:
        result = subprocess.run(
            ["kaggle", "--version"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def install_kaggle_cli():
    """Install Kaggle CLI."""
    print("Installing Kaggle CLI...")
    subprocess.run([sys.executable, "-m", "pip", "install", "kaggle"], check=True)
    print("Kaggle CLI installed successfully.")


def download_kaggle_dataset(dataset_key: str, config: dict):
    """Download a dataset from Kaggle."""
    extract_to = Path(config["extract_to"])

    # Check if already downloaded
    if extract_to.exists() and any(extract_to.iterdir()):
        print(f"[SKIP] {config['name']} already exists at {extract_to}")
        return True

    print(f"\nDownloading {config['name']}...")
    print(f"  Size: {config['size']}")
    print(f"  URL: {config['url']}")

    # Create directory
    extract_to.mkdir(parents=True, exist_ok=True)

    # Download
    try:
        cmd_parts = config["download_cmd"].split()
        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            cwd=str(extract_to),
        )

        if result.returncode != 0:
            print(f"[ERROR] Download failed: {result.stderr}")
            return False

        # Unzip
        zip_files = list(extract_to.glob("*.zip"))
        for zip_file in zip_files:
            subprocess.run(
                ["unzip", "-o", str(zip_file), "-d", str(extract_to)],
                check=True,
            )
            zip_file.unlink()  # Remove zip after extraction

        print(f"[OK] {config['name']} downloaded to {extract_to}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to download {config['name']}: {e}")
        return False


def download_addbiomechanics(config: dict):
    """Download AddBiomechanics dataset (large file)."""
    extract_to = Path(config["extract_to"])
    zip_path = Path("data/datasets/addbiomechanics.zip")

    # Check if already downloaded
    if extract_to.exists() and any(extract_to.iterdir()):
        print(f"[SKIP] {config['name']} already exists at {extract_to}")
        return True

    print(f"\nDownloading {config['name']}...")
    print(f"  WARNING: This dataset is ~70GB. Make sure you have enough disk space.")
    print(f"  URL: {config['url']}")

    confirm = input("Continue? (y/N): ")
    if confirm.lower() != 'y':
        print("Download cancelled.")
        return False

    # Create directory
    Path("data/datasets").mkdir(parents=True, exist_ok=True)

    try:
        # Download using curl
        print("Downloading... This may take a while.")
        subprocess.run(
            ["curl", "-o", str(zip_path), config["url"]],
            check=True,
        )

        # Extract
        print("Extracting...")
        extract_to.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["unzip", "-o", str(zip_path), "-d", str(extract_to)],
            check=True,
        )

        # Remove zip
        zip_path.unlink()

        print(f"[OK] {config['name']} downloaded to {extract_to}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to download {config['name']}: {e}")
        return False


def create_sample_dataset():
    """Create a sample dataset structure for testing."""
    sample_dir = Path("data/datasets/sample")
    sample_dir.mkdir(parents=True, exist_ok=True)

    # Create sample CSV
    sample_csv = sample_dir / "sample_squat_data.csv"
    sample_csv.write_text("""frame,knee_angle,hip_angle,trunk_tibia_diff,knee_valgus_ratio,heel_lift,label
1,175.2,172.1,2.3,0.95,0.02,good
2,165.4,160.3,3.1,0.93,0.03,good
3,145.8,140.2,4.2,0.91,0.04,good
4,125.3,118.5,5.1,0.88,0.05,good
5,108.2,102.4,6.3,0.85,0.06,good
6,95.1,88.3,7.2,0.82,0.07,good
7,92.3,85.2,8.1,0.78,0.12,knee_valgus
8,98.5,92.1,9.2,0.75,0.15,knee_valgus
9,112.4,108.3,5.4,0.83,0.08,good
10,135.2,130.1,4.1,0.89,0.05,good
""")

    print(f"[OK] Sample dataset created at {sample_dir}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Download standard motion datasets for threshold calibration"
    )
    parser.add_argument(
        "--dataset",
        choices=["all", "ui-prmd", "kaggle-squat", "addbiomechanics", "sample"],
        default="sample",
        help="Dataset to download (default: sample)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available datasets",
    )

    args = parser.parse_args()

    if args.list:
        print("\nAvailable datasets:")
        print("-" * 60)
        for key, config in DATASETS.items():
            print(f"\n  {key}:")
            print(f"    Name: {config['name']}")
            print(f"    Description: {config['description']}")
            print(f"    Size: {config['size']}")
            print(f"    Format: {config['format']}")
            print(f"    URL: {config['url']}")
        print(f"\n  sample:")
        print(f"    Name: Sample Dataset")
        print(f"    Description: Small sample dataset for testing")
        print(f"    Size: ~1KB")
        print(f"    Format: CSV")
        return

    # Check Kaggle CLI for Kaggle datasets
    if args.dataset in ["ui-prmd", "kaggle-squat", "all"]:
        if not check_kaggle_cli():
            print("Kaggle CLI not found.")
            install = input("Install Kaggle CLI? (y/N): ")
            if install.lower() == 'y':
                install_kaggle_cli()
            else:
                print("Cannot download Kaggle datasets without Kaggle CLI.")
                print("Install with: pip install kaggle")
                return

    # Download datasets
    success_count = 0
    total_count = 0

    if args.dataset == "sample":
        create_sample_dataset()
        success_count = 1
        total_count = 1
    elif args.dataset == "all":
        for key, config in DATASETS.items():
            total_count += 1
            if key == "addbiomechanics":
                if download_addbiomechanics(config):
                    success_count += 1
            else:
                if download_kaggle_dataset(key, config):
                    success_count += 1
    else:
        total_count = 1
        config = DATASETS[args.dataset]
        if args.dataset == "addbiomechanics":
            if download_addbiomechanics(config):
                success_count += 1
        else:
            if download_kaggle_dataset(args.dataset, config):
                success_count += 1

    print(f"\n{'='*60}")
    print(f"Download complete: {success_count}/{total_count} datasets")


if __name__ == "__main__":
    main()
