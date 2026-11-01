"""
Generate the parking lots data for the improved Task 2 system.

This enhanced scenario is kept separate from the baseline by writing to
data/parking_lots_enhanced.csv by default.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

NUM_PARKING_SPACES = 38

# Enhanced policy:
# Expand designated truck loading capacity from 2 spaces to 4 spaces.
# These spaces are protected as truck-only loading bays.
TRUCK_LOADING_SPACES_IDS = {9, 10, 24, 25}


def _running_in_notebook() -> bool:
    try:
        from IPython import get_ipython  # type: ignore
        ip = get_ipython()
        if ip is None:
            return False
        return ip.__class__.__name__ == "ZMQInteractiveShell"
    except Exception:
        return False


def _default_output_path() -> Path:
    project_root = Path(__file__).resolve().parent.parent
    return project_root / "data" / "parking_lots_enhanced.csv"


def _safe_write_csv(df: pd.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_csv(output_path, index=False)
        return output_path
    except PermissionError:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback = output_path.with_name(f"{output_path.stem}_generated_{ts}{output_path.suffix}")
        df.to_csv(fallback, index=False)
        print(
            f"Warning: could not write to '{output_path}' (file may be locked). "
            f"Wrote to '{fallback}' instead."
        )
        return fallback


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Generate enhanced parking lots CSV.")
    parser.add_argument(
        "--output",
        type=str,
        default=str(_default_output_path()),
        help="Output CSV path (default: data/parking_lots_enhanced.csv).",
    )

    if argv is None and _running_in_notebook():
        argv = []
    args = parser.parse_args(argv)

    parking_lots = list(range(1, NUM_PARKING_SPACES + 1))

    # Default all spaces to car-only first
    space_car_availability = [True] * NUM_PARKING_SPACES
    space_truck_availability = [False] * NUM_PARKING_SPACES

    # Convert selected spaces to protected truck-only bays
    for truck_id in TRUCK_LOADING_SPACES_IDS:
        idx = truck_id - 1
        if 0 <= idx < NUM_PARKING_SPACES:
            space_truck_availability[idx] = True
            space_car_availability[idx] = False

    df = pd.DataFrame(
        {
            "parking_space_id": parking_lots,
            "car_enabled": space_car_availability,
            "truck_enabled": space_truck_availability,
            "occupied": False,
        }
    )

    written_path = _safe_write_csv(df, Path(args.output))
    print(f"Enhanced parking lots file written to: {written_path}")


if __name__ == "__main__":
    main()
