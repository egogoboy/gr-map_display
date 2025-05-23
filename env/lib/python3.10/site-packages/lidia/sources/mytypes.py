from argparse import _SubParsersAction, Namespace
from multiprocessing import Queue
from pydantic import BaseModel
from struct import unpack_from
from typing import Callable, NoReturn, Tuple

from ..config import Config

RunFn = Callable[[Queue, Namespace, Config], NoReturn]
SetupFn = Callable[[_SubParsersAction], Tuple[str, RunFn]]


FG_NET_FDM_VERSION = 24


class FGNetFDM(BaseModel):
    """FlightGear network communication structure from src/Network/net_fdm.hxx"""
    version: int = 0
    """increment when data values change"""
    padding: int = 0
    """padding"""
    longitude: float = 0
    """geodetic (radians)"""
    latitude: float = 0
    """geodetic (radians)"""
    altitude: float = 0
    """above sea level (meters)"""
    agl: float = 0
    """above ground level (meters)"""
    phi: float = 0
    """roll (radians)"""
    theta: float = 0
    """pitch (radians)"""
    psi: float = 0
    """yaw or true heading (radians)"""
    alpha: float = 0
    """angle of attack (radians)"""
    beta: float = 0
    """side slip angle (radians)"""
    phidot: float = 0
    """roll rate (radians/sec)"""
    thetadot: float = 0
    """pitch rate (radians/sec)"""
    psidot: float = 0
    """yaw rate (radians/sec)"""
    vcas: float = 0
    """calibrated airspeed"""
    climb_rate: float = 0
    """feet per second"""
    v_north: float = 0
    """north velocity in local/body frame, fps"""
    v_east: float = 0
    """east velocity in local/body frame, fps"""
    v_down: float = 0
    """down/vertical velocity in local/body frame, fps"""
    v_body_u: float = 0
    """ECEF velocity in body frame"""
    v_body_v: float = 0
    """ECEF velocity in body frame"""
    v_body_w: float = 0
    """ECEF velocity in body frame"""
    A_X_pilot: float = 0
    """X accel in body frame ft/sec^2"""
    A_Y_pilot: float = 0
    """Y accel in body frame ft/sec^2"""
    A_Z_pilot: float = 0
    """Z accel in body frame ft/sec^2"""
    stall_warning: float = 0
    """0.0 - 1.0 indicating the amount of stall"""
    slip_deg: float = 0
    """slip ball deflection"""
    num_engines: int = 0
    """Number of valid engines"""
    eng_state: Tuple[int, int, int, int] = (0, 0, 0, 0)
    """Engine state (off, cranking, running)"""
    rpm: Tuple[float, float, float, float] = (0, 0, 0, 0)
    """Engine RPM rev/min"""
    fuel_flow: Tuple[float, float, float, float] = (0, 0, 0, 0)
    """Fuel flow gallons/hr"""
    fuel_px: Tuple[float, float, float, float] = (0, 0, 0, 0)
    """Fuel pressure psi"""
    egt: Tuple[float, float, float, float] = (0, 0, 0, 0)
    """Exhuast gas temp deg F"""
    cht: Tuple[float, float, float, float] = (0, 0, 0, 0)
    """Cylinder head temp deg F"""
    mp_osi: Tuple[float, float, float, float] = (0, 0, 0, 0)
    """Manifold pressure"""
    tit: Tuple[float, float, float, float] = (0, 0, 0, 0)
    """Turbine Inlet Temperature"""
    oil_temp: Tuple[float, float, float, float] = (0, 0, 0, 0)
    """Oil temp deg F"""
    oil_px: Tuple[float, float, float, float] = (0, 0, 0, 0)
    """Oil pressure psi"""
    num_tanks: int = 0
    """Max number of fuel tanks"""
    fuel_quantity: Tuple[float, float, float, float] = (0, 0, 0, 0)
    num_wheels: int = 0
    wow: Tuple[int, int, int] = (0, 0, 0)
    gear_pos: Tuple[float, float, float] = (0, 0, 0)
    gear_steer: Tuple[float, float, float] = (0, 0, 0)
    gear_compression: Tuple[float, float, float] = (0, 0, 0)
    cur_time: int = 0
    """current unix time"""
    warp: int = 0
    """offset in seconds to unix time"""
    visibility: float = 0
    """visibility in meters (for env. effects)"""
    elevator: float = 0
    elevator_trim_tab: float = 0
    left_flap: float = 0
    right_flap: float = 0
    left_aileron: float = 0
    right_aileron: float = 0
    rudder: float = 0
    nose_wheel: float = 0
    speedbrake: float = 0
    spoilers: float = 0

    @classmethod
    def from_bytes(cls, data):
        version = unpack_from("!I", data)[0]
        if version != FG_NET_FDM_VERSION:
            raise ValueError(
                f"Expected protocol version {FG_NET_FDM_VERSION}, got {version}")
        this = cls()
        decoded = unpack_from(
            "!IIdddffffffffffffffffffffffIIIIIffffffffffffffffffffffffffffffffffffIffffIIIIfffffffffIifffffffffff", data)
        this.version = decoded[0]
        this.padding = decoded[1]
        this.longitude = decoded[2]
        this.latitude = decoded[3]
        this.altitude = decoded[4]
        this.agl = decoded[5]
        this.phi = decoded[6]
        this.theta = decoded[7]
        this.psi = decoded[8]
        this.alpha = decoded[9]
        this.beta = decoded[10]
        this.phidot = decoded[11]
        this.thetadot = decoded[12]
        this.psidot = decoded[13]
        this.vcas = decoded[14]
        this.climb_rate = decoded[15]
        this.v_north = decoded[16]
        this.v_east = decoded[17]
        this.v_down = decoded[18]
        this.v_body_u = decoded[19]
        this.v_body_v = decoded[20]
        this.v_body_w = decoded[21]
        this.A_X_pilot = decoded[22]
        this.A_Y_pilot = decoded[23]
        this.A_Z_pilot = decoded[24]
        this.stall_warning = decoded[25]
        this.slip_deg = decoded[26]
        this.num_engines = decoded[27]
        this.eng_state = decoded[28:32]
        this.rpm = decoded[32:36]
        this.fuel_flow = decoded[36:40]
        this.fuel_px = decoded[40:44]
        this.egt = decoded[44:48]
        this.cht = decoded[48:52]
        this.mp_osi = decoded[52:56]
        this.tit = decoded[56:60]
        this.oil_temp = decoded[60:64]
        this.oil_px = decoded[64:68]
        this.num_tanks = decoded[68]
        this.fuel_quantity = decoded[69:73]
        this.num_wheels = decoded[73]
        this.wow = decoded[74:77]
        this.gear_pos = decoded[77:80]
        this.gear_steer = decoded[80:83]
        this.gear_compression = decoded[83:86]
        this.cur_time = decoded[86]
        this.warp = decoded[87]
        this.visibility = decoded[88]
        this.elevator = decoded[89]
        this.elevator_trim_tab = decoded[90]
        this.left_flap = decoded[91]
        this.right_flap = decoded[92]
        this.left_aileron = decoded[93]
        this.right_aileron = decoded[94]
        this.rudder = decoded[95]
        this.nose_wheel = decoded[96]
        this.speedbrake = decoded[97]
        this.spoilers = decoded[98]
        return this
