"""
Generate the parking lots data (mostly fixed values).

Refer to the description of the parking lots in the requirements.

Things to consider: 
- can you add coordinates for each parking space for visualization?
"""
from __future__ import annotations

import argparse
from pathlib import Path
from datetime import datetime

import pandas as pd

# number of parkings lots from 1 to 47
NUM_PARKING_SPACES = 38

# truck loading spaces (only 2 parking spaces)
# instead of using a list, let's use a set
TRUCK_LOADING_SPACES_IDS = {9, 24}


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
    return project_root / "data" / "parking_lots.csv"


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
    parser = argparse.ArgumentParser(description="Generate parking lots CSV.")
    parser.add_argument(
        "--output",
        type=str,
        default=str(_default_output_path()),
        help="Output CSV path (default: data/parking_lots.csv).",
    )
    if argv is None and _running_in_notebook():
        argv = []
    args = parser.parse_args(argv)

    # generate the parking lots data
    # parking lots ids from 1 to 48 (as requested)
    parking_lots = list(range(1, NUM_PARKING_SPACES + 1))
    # another way of creating list: use list comprehension
    # parking_lots = [i for i in range(1, NUM_PARKING_SPACES + 1)]

    # for now, all parking spaces are available for cars to park
    space_car_availability = [True] * NUM_PARKING_SPACES

    # add a list showing whether each parking space is available for trucks
    space_truck_availability = [False] * NUM_PARKING_SPACES
    for truck_id in TRUCK_LOADING_SPACES_IDS:
        # parking_space_id is 1-indexed; list index is 0-indexed
        idx = truck_id - 1
        if 0 <= idx < NUM_PARKING_SPACES:
            space_truck_availability[idx] = True

    # store the results as csv file
    df = pd.DataFrame({
        "parking_space_id": parking_lots,
        "car_enabled": space_car_availability,
        "truck_enabled": space_truck_availability
    })

    # describe parking lots are occupied or not 
    # (for Pandas dataframe, directly assign a column with a value)
    df["occupied"] = False
    _safe_write_csv(df, Path(args.output))


# this is the entry point of the program if you want to run this python file
# in terminal, use command to run from here: python s1_gen_lots.py
if __name__ == "__main__":
    main()

