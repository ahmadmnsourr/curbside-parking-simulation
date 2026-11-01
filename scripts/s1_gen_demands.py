"""
Generate demands for the curbside parking drivers.

All numbers are generated using simulation.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np


def _running_in_notebook() -> bool:
    try:
        from IPython import get_ipython  # type: ignore

        ip = get_ipython()
        if ip is None:
            return False
        return ip.__class__.__name__ == "ZMQInteractiveShell"
    except Exception:
        return False


def sample_arrivals(num_drivers, start_time, arrival_rate):
    """
    Generate arrivals for drivers between start_time    
    - num_drivers: number of drivers
    - start_time: hour of the day
    - arrival_rate: number of arrivals per hour
    """
    # arrival of drivers follow a Poisson process
    arrivals = np.random.exponential(1 / arrival_rate, num_drivers)
    arrivals = np.cumsum(arrivals)
    arrivals = arrivals + start_time
    # round results to 3 decimal places
    arrivals = np.round(arrivals, 3)
    return arrivals


def sample_durations(num_drivers, min_duration, max_duration):
    """
    Generate durations for drivers
    - num_drivers: number of drivers
    - min_duration: minimum duration
    - max_duration: maximum duration
    """
    durations = np.random.uniform(min_duration, max_duration, num_drivers)
    # round results to 3 decimal places
    durations = np.round(durations, 3)
    return durations


def sample_car_drivers(driver_settings, sim_settings):
    # make some aliases
    ds = driver_settings
    ss = sim_settings

    # generate the drivers
    driver_type = ["car"] * ds["num_drivers"]
    arrivals = sample_arrivals(ds["num_drivers"], ss["start_time"], ds["arrival_rate"])
    durations = sample_durations(ds["num_drivers"], ds["min_duration"], ds["max_duration"])
    waiting_times = [ds["wait_time"]] * ds["num_drivers"]
    # convert to a dataframe (table)
    df = pd.DataFrame(
        {
            "type": driver_type,
            "arrival_time": arrivals,
            "duration": durations,
            "waiting_time": waiting_times,
        }
    )
    # function return the dataframe
    return df


def sample_truck_drivers(driver_settings, sim_settings):
    # make some aliases
    ds = driver_settings
    ss = sim_settings

    # generate the drivers
    driver_type = ["truck"] * ds["num_drivers"]
    arrivals = sample_arrivals(ds["num_drivers"], ss["start_time"], ds["arrival_rate"])
    waiting_times = [0] * ds["num_drivers"]
    durations = [ds["duration"]] * ds["num_drivers"]

    # convert to a dataframe (table)
    df = pd.DataFrame(
        {
            "type": driver_type,
            "arrival_time": arrivals,
            "duration": durations,
            "waiting_time": waiting_times,
        }
    )
    # function return the dataframe
    return df


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Generate curbside parking demand CSV.")
    default_output = Path(__file__).resolve().parent.parent / "data" / "drivers.csv"
    parser.add_argument(
        "--output",
        type=str,
        default=str(default_output),
        help="Output CSV path (default: data/drivers.csv).",
    )
    if argv is None and _running_in_notebook():
        argv = []
    args = parser.parse_args(argv)

    # use three dictionaries to define the
    # hyper-parameters of the simulation sampling process
    sim_settings = {
        "num_simulations": 1,
        "start_time": 8,  # hour of the day
    }
    
    car_settings = {
        "num_drivers": 200,
        "arrival_rate": 25,  # number of arrivals per hour
        "min_duration": 1.0,  # mean hours to stay
        "max_duration": 2.0,  # standard deviation of duration
        "wait_time": 15,
    }

    truck_settings = {
        "num_drivers": 16,
        "arrival_rate": 2,
        "wait_time": 1,  # truck won't wait for empty spot but will double park
        "duration": 0.5,  # duration of parking in hours (a fixed value)
    }

    # set a random seed so that results are reproducible
    # comment this out will generate different results for each run
    np.random.seed(1234)

    # generate the drivers
    car_drivers = sample_car_drivers(car_settings, sim_settings)
    truck_drivers = sample_truck_drivers(truck_settings, sim_settings)

    # let's add a new type column
    car_drivers["type"] = "car"
    truck_drivers["type"] = "truck"
    
    # instead of storing two separate csv files,
    # we can store them in one csv file by concatenating two dataframes 
    # (because type have the same column definitions)
    drivers = pd.concat([car_drivers, truck_drivers], axis=0)

    # let's also order the dataframe by arrival_time
    drivers = drivers.sort_values(by="arrival_time")

    # finally, let's assign an id to each "vehicle" or "park demand" in order
    # note that here the id starts from 0
    drivers["id"] = range(len(drivers))

    # we would like to put the "id" column as the first column
    other_cols = [col for col in drivers.columns if col != "id"]
    new_cols = ["id"] + other_cols
    drivers = drivers[new_cols]
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        drivers.to_csv(output_path, index=False)
    except PermissionError:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback = output_path.with_name(f"{output_path.stem}_generated_{ts}{output_path.suffix}")
        drivers.to_csv(fallback, index=False)
        print(
            f"Warning: could not write to '{output_path}' (file may be locked). "
            f"Wrote to '{fallback}' instead."
        )


# run the file (the entrance point of the program)
if __name__ == "__main__":
    main()
