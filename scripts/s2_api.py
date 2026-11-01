from enum import Enum
from dataclasses import dataclass
import pandas as pd


class VehicleStatus(Enum):
    NOT_ARRIVED = 0
    ARRIVED = 1
    PARKED = 2
    DOUBLE_PARKED = 3
    DEPARTED = 4
    FAILED = 5


@dataclass
class ParkingSpace:
    id: int
    car_enabled: bool
    truck_enabled: bool
    occupied: bool


@dataclass
class Vehicle:
    id: int
    type: str
    status: VehicleStatus
    arrive_time: int
    max_wait_time: int
    park_len: int

    assigned_lot: ParkingSpace | None = None
    waited_time: int = 0
    parked_time: int = 0
    departed_time: int = 0
    was_double_parked: bool = False

    def has_arrived(self, t: int):
        return self.arrive_time <= t

    def update_status_by_delta_t(self, delta_t: int):
        if self.status == VehicleStatus.ARRIVED:
            self.waited_time += delta_t
        if self.status in [VehicleStatus.PARKED, VehicleStatus.DOUBLE_PARKED]:
            self.parked_time += delta_t


class VehiclesLoader:
    def __init__(self, file_path: str):
        df = pd.read_csv(file_path)
        self.df = df
        self.vehicles: list[Vehicle] = self.convert_df_to_list(df)

    def convert_df_to_list(self, df: pd.DataFrame):
        vehicles = []
        for _, row in df.iterrows():
            vehicle = self.process_df_row(row)
            vehicles.append(vehicle)
        return vehicles

    def process_df_row(self, row: pd.Series):
        data_dict = {
            "id": row["id"],
            "type": row["type"],
            "status": VehicleStatus.NOT_ARRIVED,
            "arrive_time": int(row["arrival_time"] * 60),
            "max_wait_time": int(row["waiting_time"]),
            "park_len": int(row["duration"] * 60),
            "assigned_lot": None,
        }
        return Vehicle(**data_dict)


class ParkingLotLoader:
    def __init__(self, file_path: str):
        df = pd.read_csv(file_path)
        self.df = df
        self.spaces: list[ParkingSpace] = self.convert_df_to_list(df)

    def convert_df_to_list(self, df: pd.DataFrame):
        spaces = []
        for _, row in df.iterrows():
            data_lst = [
                row["parking_space_id"],
                row["car_enabled"],
                row["truck_enabled"],
                row["occupied"],
            ]
            space = ParkingSpace(*data_lst)
            spaces.append(space)
        return spaces