from __future__ import annotations
from copy import deepcopy
import argparse
from pathlib import Path
import random
import pandas as pd
try:
    from .s2_api import Vehicle, ParkingSpace, VehicleStatus
except ImportError:
    from s2_api import Vehicle, ParkingSpace, VehicleStatus


class SimTracker:
    def __init__(self, vehicles: list[Vehicle], spaces: list[ParkingSpace]):
        self.future_vehicles = deepcopy(vehicles)
        self.input_drivers_path: Path | None = None
        self.input_lots_path: Path | None = None

        self.arrived_vehicles = []
        self.parked_vehicles = []
        self.double_parked_vehicles = []
        self.departed_vehicles = []
        self.failed_vehicles = []

        self.empty_spaces = deepcopy(spaces)
        self.occupied_spaces = []

    def update_future_to_arrived(self, t: int):
        for veh in self.future_vehicles[:]:
            if veh.has_arrived(t):
                veh.status = VehicleStatus.ARRIVED
                self.arrived_vehicles.append(veh)
                self.future_vehicles.remove(veh)

    def update_arrived_to_failed(self):
        for veh in self.arrived_vehicles[:]:
            if veh.waited_time > veh.max_wait_time:
                veh.status = VehicleStatus.FAILED
                self.failed_vehicles.append(veh)
                self.arrived_vehicles.remove(veh)

    def update_arrived_to_parked(self):
        if len(self.arrived_vehicles) == 0:
            return

        random.shuffle(self.arrived_vehicles)

        new_parked_vehicles = []
        new_double_parked_vehicles = []

        for veh in self.arrived_vehicles:
            open_spaces_car = self._get_open_spaces(self.empty_spaces, "car")
            open_spaces_truck = self._get_open_spaces(self.empty_spaces, "truck")

            if veh.type == "car":
                if len(open_spaces_car) == 0:
                    continue
                space = open_spaces_car.pop()
                space.occupied = True
                veh.assigned_lot = space
                veh.status = VehicleStatus.PARKED
                new_parked_vehicles.append(veh)
                self.occupied_spaces.append(space)
                self.empty_spaces.remove(space)

            elif veh.type == "truck":
                if len(open_spaces_truck) > 0:
                    space = open_spaces_truck.pop()
                    space.occupied = True
                    veh.assigned_lot = space
                    veh.status = VehicleStatus.PARKED
                    new_parked_vehicles.append(veh)
                    self.occupied_spaces.append(space)
                    self.empty_spaces.remove(space)
                else:
                    veh.assigned_lot = None
                    veh.status = VehicleStatus.DOUBLE_PARKED
                    veh.was_double_parked = True
                    new_double_parked_vehicles.append(veh)

        self.arrived_vehicles = [
            veh for veh in self.arrived_vehicles
            if veh not in new_parked_vehicles and veh not in new_double_parked_vehicles
        ]
        self.parked_vehicles.extend(new_parked_vehicles)
        self.double_parked_vehicles.extend(new_double_parked_vehicles)

    def update_parked_to_departed(self):
        for veh in self.parked_vehicles[:]:
            if veh.parked_time >= veh.park_len:
                veh.status = VehicleStatus.DEPARTED
                self.departed_vehicles.append(veh)
                self.parked_vehicles.remove(veh)

                space = veh.assigned_lot
                self.empty_spaces.append(space)
                self.occupied_spaces.remove(space)
                space.occupied = False

    def update_double_parked_to_departed(self):
        for veh in self.double_parked_vehicles[:]:
            if veh.parked_time >= veh.park_len:
                veh.status = VehicleStatus.DEPARTED
                self.departed_vehicles.append(veh)
                self.double_parked_vehicles.remove(veh)

    def update_all_vehicle_status(self):
        for veh in self.future_vehicles:
            veh.status = VehicleStatus.NOT_ARRIVED
        for veh in self.arrived_vehicles:
            veh.status = VehicleStatus.ARRIVED
        for veh in self.parked_vehicles:
            veh.status = VehicleStatus.PARKED
        for veh in self.double_parked_vehicles:
            veh.status = VehicleStatus.DOUBLE_PARKED
        for veh in self.departed_vehicles:
            veh.status = VehicleStatus.DEPARTED
        for veh in self.failed_vehicles:
            veh.status = VehicleStatus.FAILED

    def update_all_parking_space_status(self):
        for space in self.empty_spaces:
            space.occupied = False
        for space in self.occupied_spaces:
            space.occupied = True

    def _get_open_spaces(self, empty_spaces: list[ParkingSpace], type: str):
        if type == "car":
            return [space for space in empty_spaces if space.car_enabled]
        elif type == "truck":
            return [space for space in empty_spaces if space.truck_enabled]
        else:
            raise ValueError(f"Invalid vehicle type: {type}")

    def update_status_by_delta_t(self, delta_t: int):
        for veh in self.arrived_vehicles:
            veh.update_status_by_delta_t(delta_t)
        for veh in self.parked_vehicles:
            veh.update_status_by_delta_t(delta_t)
        for veh in self.double_parked_vehicles:
            veh.update_status_by_delta_t(delta_t)

    def get_summary_info(self):
        num_future = len(self.future_vehicles)
        num_arrived = len(self.arrived_vehicles)
        num_parked = len(self.parked_vehicles)
        num_double_parked = len(self.double_parked_vehicles)
        num_departed = len(self.departed_vehicles)
        num_failed = len(self.failed_vehicles)
        num_empty = len(self.empty_spaces)
        num_occupied = len(self.occupied_spaces)

        return (
            num_future,
            num_arrived,
            num_parked,
            num_double_parked,
            num_departed,
            num_failed,
            num_empty,
            num_occupied,
        )


class Observer:
    def __init__(self):
        self.info_lst = []

    def observe_at_time_t(self, t: int, sim_tracker: SimTracker):
        info = sim_tracker.get_summary_info()
        info = [t] + list(info)
        self.info_lst.append(info)

    def get_summary_info(self):
        cols = [
            "t",
            "num_future",
            "num_arrived",
            "num_parked",
            "num_double_parked",
            "num_departed",
            "num_failed",
            "num_empty",
            "num_occupied",
        ]
        return pd.DataFrame(self.info_lst, columns=cols)


class SimRunner:
    def __init__(self, sim_tracker: SimTracker, observer: Observer, t_start: int):
        self.tracker = sim_tracker
        self.observer = observer
        self.t = t_start

    def run_simulation(self):
        t = self.t
        while t < 1440 and not self.all_vehicles_finished():
            if t % 10 == 0:
                print(".", end="", flush=True)
            self.run_simulation_one_unit(t)
            t += 1
        self._auto_export_results()

    def _auto_export_results(self):
        drivers_path = getattr(self.tracker, "input_drivers_path", None)
        lots_path = getattr(self.tracker, "input_lots_path", None)
        if drivers_path is None or lots_path is None:
            return
        _export_results(
            tracker=self.tracker,
            observer=self.observer,
            drivers_path=Path(drivers_path),
            lots_path=Path(lots_path),
        )

    def all_vehicles_finished(self):
        num_future = len(self.tracker.future_vehicles)
        num_arrived = len(self.tracker.arrived_vehicles)
        num_parked = len(self.tracker.parked_vehicles)
        num_double_parked = len(self.tracker.double_parked_vehicles)

        return (
            num_future == 0
            and num_arrived == 0
            and num_parked == 0
            and num_double_parked == 0
        )

    def run_simulation_one_unit(self, t: int):
        self.tracker.update_all_vehicle_status()
        self.tracker.update_all_parking_space_status()

        self.tracker.update_future_to_arrived(t)
        self.tracker.update_arrived_to_failed()
        self.tracker.update_arrived_to_parked()
        self.tracker.update_parked_to_departed()
        self.tracker.update_double_parked_to_departed()

        self.tracker.update_all_vehicle_status()
        self.tracker.update_all_parking_space_status()

        self.observer.observe_at_time_t(t, self.tracker)
        self.tracker.update_status_by_delta_t(1)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_drivers_path() -> Path:
    return _project_root() / "data" / "drivers.csv"


def _default_lots_path() -> Path:
    return _project_root() / "data" / "parking_lots.csv"


def _results_dir() -> Path:
    return _project_root() / "results"


def _is_enhanced_run(drivers_path: Path, lots_path: Path) -> bool:
    drivers_str = str(drivers_path).lower()
    lots_str = str(lots_path).lower()
    return "_enhanced" in drivers_str or "_enhanced" in lots_str


def _build_vehicle_results_df(tracker: SimTracker) -> pd.DataFrame:
    all_vehicles = (
        tracker.future_vehicles
        + tracker.arrived_vehicles
        + tracker.parked_vehicles
        + tracker.double_parked_vehicles
        + tracker.departed_vehicles
        + tracker.failed_vehicles
    )
    rows = []
    for veh in all_vehicles:
        status_name = veh.status.name.lower()
        assigned_space_id = veh.assigned_lot.id if veh.assigned_lot is not None else None
        departure_time = None
        if veh.status == VehicleStatus.DEPARTED:
            departure_time = veh.arrive_time + veh.waited_time + veh.parked_time
        rows.append(
            {
                "vehicle_id": veh.id,
                "vehicle_type": veh.type,
                "final_status": status_name,
                "arrival_time": veh.arrive_time,
                "departure_time": departure_time,
                "assigned_parking_space_id": assigned_space_id,
                "waited_time_minutes": veh.waited_time,
                "parked_time_minutes": veh.parked_time,
                "max_wait_time_minutes": veh.max_wait_time,
                "planned_parking_duration_minutes": veh.park_len,
                "was_double_parked": bool(getattr(veh, "was_double_parked", False)),
            }
        )
    return pd.DataFrame(rows).sort_values("vehicle_id").reset_index(drop=True)


def _build_aggregate_summary_df(df_vehicle_results: pd.DataFrame) -> pd.DataFrame:
    total_vehicles = int(len(df_vehicle_results))
    parked_vehicles = int((df_vehicle_results["assigned_parking_space_id"].notna()).sum())
    double_parked_vehicles = int(df_vehicle_results["was_double_parked"].sum())
    failed_vehicles = int((df_vehicle_results["final_status"] == "failed").sum())
    departed_vehicles = int((df_vehicle_results["final_status"] == "departed").sum())
    avg_waited_time = float(df_vehicle_results["waited_time_minutes"].mean()) if total_vehicles else 0.0

    return pd.DataFrame(
        [
            {
                "total_vehicles": total_vehicles,
                "parked_vehicles": parked_vehicles,
                "double_parked_vehicles": double_parked_vehicles,
                "failed_vehicles": failed_vehicles,
                "departed_vehicles": departed_vehicles,
                "avg_waited_time_minutes": round(avg_waited_time, 3),
            }
        ]
    )


def _export_results(
    tracker: SimTracker,
    observer: Observer,
    drivers_path: Path,
    lots_path: Path,
) -> tuple[Path, Path]:
    results_dir = _results_dir()
    results_dir.mkdir(parents=True, exist_ok=True)

    enhanced = _is_enhanced_run(drivers_path=drivers_path, lots_path=lots_path)
    if enhanced:
        vehicle_results_path = results_dir / "simulation_results_enhanced.csv"
        summary_results_path = results_dir / "simulation_summary_enhanced.csv"
    else:
        vehicle_results_path = results_dir / "simulation_results.csv"
        summary_results_path = results_dir / "simulation_summary.csv"

    df_vehicle_results = _build_vehicle_results_df(tracker)
    df_aggregate_summary = _build_aggregate_summary_df(df_vehicle_results)

    # keep observer summary available in memory for notebook analysis, while exporting
    # the requested aggregate summary table to CSV.
    _ = observer.get_summary_info()

    df_vehicle_results.to_csv(vehicle_results_path, index=False)
    df_aggregate_summary.to_csv(summary_results_path, index=False)
    return vehicle_results_path, summary_results_path


def run_from_files(
    drivers_path: str | Path,
    lots_path: str | Path,
    t_start: int = 8 * 60,
) -> pd.DataFrame:
    try:
        from . import s2_api as api
    except ImportError:
        import s2_api as api

    drivers_path = Path(drivers_path)
    lots_path = Path(lots_path)
    vehicle_loader = api.VehiclesLoader(str(drivers_path))
    lots_loader = api.ParkingLotLoader(str(lots_path))

    tracker = SimTracker(
        vehicles=vehicle_loader.vehicles,
        spaces=lots_loader.spaces,
    )
    tracker.input_drivers_path = drivers_path
    tracker.input_lots_path = lots_path
    observer = Observer()
    simulator = SimRunner(
        sim_tracker=tracker,
        observer=observer,
        t_start=t_start,
    )

    simulator.run_simulation()
    df_summary = observer.get_summary_info()
    return df_summary


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Run curbside parking simulation.")
    parser.add_argument(
        "--drivers",
        type=str,
        default=str(_default_drivers_path()),
        help="Path to drivers CSV (default: data/drivers.csv).",
    )
    parser.add_argument(
        "--lots",
        type=str,
        default=str(_default_lots_path()),
        help="Path to parking lots CSV (default: data/parking_lots.csv).",
    )
    args = parser.parse_args(argv)

    df_summary = run_from_files(drivers_path=args.drivers, lots_path=args.lots)
    print(df_summary.head())


if __name__ == "__main__":
    main()