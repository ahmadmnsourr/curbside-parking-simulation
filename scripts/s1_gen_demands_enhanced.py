"""
Generate demand for the improved Task 2 curbside management system.

This enhanced scenario is kept separate from the baseline by writing to
data/drivers_enhanced.csv by default.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


def _running_in_notebook() -> bool:
    try:
        from IPython import get_ipython  # type: ignore
        ip = get_ipython()
        if ip is None:
            return False
        return ip.__class__.__name__ == "ZMQInteractiveShell"
    except Exception:
        return False


def sample_arrivals(num_drivers: int, start_time: float, arrival_rate: float):
    """
    Generate arrival times using a Poisson process.

    Parameters
    ----------
    num_drivers : int
        Number of drivers.
    start_time : float
        Start hour of the day.
    arrival_rate : float
        Average arrivals per hour.
    """
    arrivals = np.random.exponential(1 / arrival_rate, num_drivers)
    arrivals = np.cumsum(arrivals)
    arrivals = arrivals + start_time
    return np.round(arrivals, 3)


def sample_durations(num_drivers: int, min_duration: float, max_duration: float):
    """
    Generate parking durations from a uniform distribution.
    """
    durations = np.random.uniform(min_duration, max_duration, num_drivers)
    return np.round(durations, 3)


def sample_car_drivers(driver_settings: dict, sim_settings: dict) -> pd.DataFrame:
    ds = driver_settings
    ss = sim_settings
    return pd.DataFrame(
        {
            "type": ["car"] * ds["num_drivers"],
            "arrival_time": sample_arrivals(ds["num_drivers"], ss["start_time"], ds["arrival_rate"]),
            "duration": sample_durations(ds["num_drivers"], ds["min_duration"], ds["max_duration"]),
            "waiting_time": [ds["wait_time"]] * ds["num_drivers"],
        }
    )


def sample_truck_drivers(driver_settings: dict, sim_settings: dict) -> pd.DataFrame:
    ds = driver_settings
    ss = sim_settings
    return pd.DataFrame(
        {
            "type": ["truck"] * ds["num_drivers"],
            "arrival_time": sample_arrivals(ds["num_drivers"], ss["start_time"], ds["arrival_rate"]),
            "duration": [ds["duration"]] * ds["num_drivers"],
            "waiting_time": [0] * ds["num_drivers"],
        }
    )


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Generate enhanced curbside parking demand CSV."
    )
    default_output = Path(__file__).resolve().parent.parent / "data" / "drivers_enhanced.csv"
    parser.add_argument(
        "--output",
        type=str,
        default=str(default_output),
        help="Output CSV path (default: data/drivers_enhanced.csv).",
    )

    if argv is None and _running_in_notebook():
        argv = []
    args = parser.parse_args(argv)

    # Shared simulation settings
    sim_settings = {
        "num_simulations": 1,
        "start_time": 8,  # hour of the day
    }

    # Enhanced policy:
    # - same total car demand for fair comparison
    # - short-stay parking to improve turnover
    # - reduced car search tolerance to represent better guidance/signage
    car_settings = {
        "num_drivers": 200,
        "arrival_rate": 25,
        "min_duration": 0.75,
        "max_duration": 1.25,
        "wait_time": 10,
    }

    # Keep truck demand unchanged for a fair comparison
    truck_settings = {
        "num_drivers": 16,
        "arrival_rate": 2,
        "wait_time": 1,   # trucks double park if no legal loading bay is open
        "duration": 0.5,  # hours
    }

    np.random.seed(1234)

    car_drivers = sample_car_drivers(car_settings, sim_settings)
    truck_drivers = sample_truck_drivers(truck_settings, sim_settings)

    drivers = pd.concat([car_drivers, truck_drivers], axis=0)
    drivers = drivers.sort_values(by="arrival_time").reset_index(drop=True)
    drivers["id"] = range(len(drivers))

    other_cols = [col for col in drivers.columns if col != "id"]
    drivers = drivers[["id"] + other_cols]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        drivers.to_csv(output_path, index=False)
        print(f"Enhanced demand file written to: {output_path}")
    except PermissionError:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback = output_path.with_name(f"{output_path.stem}_generated_{ts}{output_path.suffix}")
        drivers.to_csv(fallback, index=False)
        print(
            f"Warning: could not write to '{output_path}' (file may be locked). "
            f"Wrote to '{fallback}' instead."
        )


if __name__ == "__main__":
    main()
