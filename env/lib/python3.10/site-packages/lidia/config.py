"""All definitions for lidia configuration, reused to generate the schema for config files.

To support setting it remotely when using MARSH source, specific numeric and boolean values
should have names that are unique and no longer than 16 characters.
"""
from enum import Enum
import os
from os import path
from typing import Dict, Optional
from pydantic import Field

from .mytypes import NestingModel


class RpctaskConfig(NestingModel):
    """Configuration for `rpctask`"""
    ok_tolerance: float = Field(default=0.03, alias='correct_tolerance')
    """Acceptable margin for green color.

DEPRECATED: Renamed to `ok_tolerance`, `correct_tolerance` won't be accepted after next major release"""
    warn_tolerance: float = Field(default=0.05, alias='warning_tolerance')
    """Acceptable margin for yellow color.

DEPRECATED: Renamed to `warn_tolerance`, `warning_tolerance` won't be accepted after next major release"""


class PfdConfig(NestingModel):
    """configuration for `pfd`"""
    show_alt_target: bool = True
    """Display the altitude target after receiving `trgt.instr.alt`"""
    ias_never_exceed: float = 167.0
    """Never exceed speed (Vne) shown on IAS tape"""
    show_ias_target: bool = True
    """Display the IAS target after receiving `trgt.instr.ias`"""
    show_vsi_target: bool = True
    """Display the VSI target after receiving `trgt.v_ned`"""
    show_adi_target: bool = True
    """Display the attitude target after receiving `trgt.att`"""
    adi_target_roll: bool = True
    """Rotate attitude target indicator to show desired roll"""
    adi_target_yaw: bool = False
    """Move attitude target indicator to show desired yaw"""
    show_flightpath: bool = True
    """Show flightpath vector (FPV) indicator on ADI"""
    show_retrograde: bool = False
    """Show reverse flight path vector on ADI"""
    move_roll_ticks: bool = False
    """Move roll angle scale with horizon, keeping sideslip triangle in place"""
    sideslip_max: float = 15.0
    """Maximal displayed sideslip angle, in degrees"""
    rpm_e_good_low: float = 0.97
    """Engine RPM safe region lower limit"""
    rpm_e_good_high: float = 1.03
    """Engine RPM safe region upper limit"""
    rpm_e_warn_low: float = 0.97
    """Engine RPM warning region lower limit"""
    rpm_e_warn_high: float = 1.03
    """Engine RPM warning region upper limit"""
    rpm_e_nominal: float = 6000.0
    """Engine RPM nominal value, in revolutions per minute"""
    rpm_r_good_low: float = 0.97
    """Rotor RPM safe region lower limit"""
    rpm_r_good_high: float = 1.03
    """Rotor RPM safe region upper limit"""
    rpm_r_warn_low: float = 0.90
    """Rotor RPM warning region lower limit"""
    rpm_r_warn_high: float = 1.10
    """Rotor RPM warning region upper limit"""
    rpm_r_nominal: float = 380.0
    """Rotor RPM nominal value, in revolutions per minute"""
    traffic_range: float = 18520.0
    """Range of displayed traffic information, in meters"""


class ApproachConfig(NestingModel):
    """Ship approach configuration"""
    nominal_alt: float = 3
    """Altitude at which the scale is 1, in meters"""
    camera_height: float = 10
    """Position of camera above aircraft origin, in meters

    Larger values of this make the scale change less drastically at low altitude"""


class InstrumentsConfig(NestingModel):
    """Configuration for instruments visualisation, units etc."""
    speed_multiplier: float = 3600.0 / 1852.0
    """Scaling factor to change state velocity in meters per second to displayed IAS and GS, default for knots"""
    alt_multiplier: float = Field(
        default=1 / 0.3048, alias='altitude_multiplier')
    """Scaling factor to change state altitude in meters to displayed altitude, default for feet

DEPRECATED: Renamed to `alt_multiplier`, `altitude_multiplier` won't be accepted after next major release"""
    ralt_activation: float = Field(
        default=2500.0 * 0.3048, alias='radio_altimeter_activation')
    """Activation height of radio altimeter above which it is not modeled, default 2500ft

DEPRECATED: Will be renamed to `ralt_activation` in next major release"""


class CASCategory(Enum):
    """Category (severity, type) of a message shown in CAS"""
    WARNING = 1
    """Red, blinking until acknowledged"""
    CAUTION = 2
    """Amber, blinking until acknowledged"""
    ADVISORY = 3
    """Green, blinking for a fixed time"""
    STATUS = 4
    """White messages"""


class CASEvent(NestingModel):
    """Event that can be displayed in CAS"""
    category: CASCategory
    """Category to put the message into"""
    text: str
    """Text to be shown"""


class CASConfig(NestingModel):
    """Configuration for Crew Alerting System, including events"""
    events: Dict[int, CASEvent] = {}
    """Dictionary of events by their integer id"""


class Config(NestingModel):
    """Root of configuration structure

    Every config field in this and children should be provided with defaults,
    that can be overriden by config files"""

    json_schema_url: Optional[str] = Field(alias='$schema', default=None)
    """Allow the `$schema` property for specifying JSON Schema URL"""
    rpctask = RpctaskConfig()
    pfd = PfdConfig()
    approach = ApproachConfig()
    instruments = InstrumentsConfig()
    cas = CASConfig()
    start_time: Optional[float] = None
    """Epoch time in seconds of starting the program (see `time.time()`)"""


def schema_location():
    root_path = path.abspath(path.dirname(__file__))
    data_path = path.join(root_path, 'data')
    os.makedirs(data_path, exist_ok=True)
    return path.join(data_path, 'lidia-config.json')


def write_schema():
    with open(schema_location(), 'w') as out:
        out.write(Config.schema_json(by_alias=True))


if __name__ == '__main__':
    # check that config works with old and new names
    print(Config().updated({"rpctask": {"correct_tolerance": 0.01}}).rpctask)
    print(Config().updated({"rpctask": {"ok_tolerance": 0.01}}).rpctask)
    # still rejects wrong fields
    try:
        print(Config().updated({"rpctask": {"foo": 0.01}}).rpctask)
    except Exception as e:
        print(e)
