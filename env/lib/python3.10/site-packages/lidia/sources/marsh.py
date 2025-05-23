
"""connect to MARSH Sim system, see https://marsh-sim.github.io/"""
from argparse import _SubParsersAction, ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
from collections import OrderedDict
from math import isnan, nan, sqrt
import msgpack
from multiprocessing import Queue
from pydantic.fields import ModelField
from pymavlink import mavutil
from time import time
from typing import Tuple

from ..aircraft import *
from ..config import Config
from .. import mavlink_all as mavlink
from ..mytypes import NestingModel
from .mytypes import RunFn


def setup(subparsers: _SubParsersAction) -> Tuple[str, RunFn]:
    NAME = 'marsh'
    parser: ArgumentParser = subparsers.add_parser(
        NAME,
        help=__doc__,
        formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('-m', '--manager',
                        help='MARSH Manager IP addr', default='127.0.0.1')

    return (NAME, run)


class ParamConfig:
    def __init__(self):
        self.info = OrderedDict()
        self.ignore_fields = {
            'json_schema_url',
            'cas',
        }
        for name, field in Config.__fields__.items():
            if name in self.ignore_fields:
                continue

            self._add_field_info([name], field)

    def _add_field_info(self, path: List[str], field: ModelField):
        if issubclass(field.type_, NestingModel):
            model: NestingModel = field.type_
            for name, inner_field in model.__fields__.items():
                if name in self.ignore_fields:
                    continue
                self._add_field_info(path + [name], inner_field)
        elif field.type_ in {int, float, bool}:
            assert path[-1] not in self.info
            self.info[path[-1]] = (path, field.type_)

    def get(self, config: Config, param_name: str):
        path, _ = self.info[param_name]
        field = config
        for part in path:
            field = getattr(field, part)
        return field

    def set(self, config: Config, param_name: str, value: float | int | bool):
        path, type_ = self.info[param_name]
        if type_ is bool and value is not bool:
            assert value == 0 or value == 1
        elif type_ is int:
            assert round(value) == value

        obj = config
        for part in path[:-1]:
            obj = getattr(obj, part)
        setattr(obj, path[-1], type_(value))

    def __contains__(self, item):
        return item in self.info

    def __len__(self):
        return len(self.info)

    def send(self, config: Config, mav: mavlink.MAVLink, index: int, name=''):
        """
        convenience function to send PARAM_VALUE
        pass index -1 to use name instead

        silently returns on invalid index or name
        """
        param_id = bytearray(16)

        if index >= 0:
            if index >= len(self):
                return

            # HACK: is there a nicer way to get items from OrderedDict by order?
            name = list(self.info.keys())[index]
        else:
            if name not in self:
                return

            index = list(self.info.keys()).index(name)
        name_bytes = name.encode('utf8')
        param_id[:len(name_bytes)] = name_bytes

        mav.param_value_send(param_id, self.get(config, name), mavlink.MAV_PARAM_TYPE_REAL32,
                             len(self), index)


def run(q: Queue, args: Namespace, config: Config):

    connection_string = f'udpout:{args.manager}:24400'
    mav = mavlink.MAVLink(mavutil.mavlink_connection(connection_string))
    mav.srcSystem = 1  # default system
    mav.srcComponent = mavlink.MARSH_COMP_ID_INSTRUMENTS
    if args.verbosity >= 0:
        print(f'Connecting to MARSH Manager on {connection_string}')

    last_state = AircraftState()
    params = ParamConfig()

    # for messages requiring time_boot*
    start_time = time()

    # controlling when messages should be sent
    heartbeat_next = 0.0
    heartbeat_interval = 1.0

    # monitoring connection to manager with heartbeat
    timeout_interval = 5.0
    manager_timeout = 0.0
    manager_connected = False

    # the loop goes as fast as it can, relying on the variables above for timing
    while True:
        if time() >= heartbeat_next:
            mav.heartbeat_send(
                mavlink.MAV_TYPE_GENERIC,
                mavlink.MAV_AUTOPILOT_INVALID,
                mavlink.MAV_MODE_FLAG_TEST_ENABLED,
                0,
                mavlink.MAV_STATE_ACTIVE
            )
            heartbeat_next = time() + heartbeat_interval

        state_changed = False

        # handle incoming messages
        try:
            while (message := mav.file.recv_msg()) is not None:
                message: mavlink.MAVLink_message
                if args.verbosity >= 2:
                    print('Received', message.get_type())
                if message.get_type() == 'HEARTBEAT':
                    if message.get_srcComponent() == mavlink.MARSH_COMP_ID_MANAGER:
                        if not manager_connected and args.verbosity >= 0:
                            print('Connected to simulation manager')
                            for msgid in [
                                mavlink.MAVLINK_MSG_ID_V2_EXTENSION,
                                mavlink.MAVLINK_MSG_ID_SET_POSITION_TARGET_LOCAL_NED,
                            ]:
                                mav.command_long_send(mav.srcSystem, mavlink.MARSH_COMP_ID_MANAGER,
                                                      mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
                                                      0,  # not a confirmation
                                                      msgid,  # requested msg
                                                      0,  # default interval
                                                      nan, nan, nan, nan,  # unused
                                                      1)  # request is for sender (lidia)
                        manager_connected = True
                        manager_timeout = time() + timeout_interval
                elif message.get_type() == 'MANUAL_CONTROL':
                    # This line helps with type hints
                    mc: mavlink.MAVLink_manual_control_message = message
                    state_changed = True

                    last_state.ctrl = Controls()
                    # Invalid axes are sent as INT16_MAX
                    INVALID = 0x7FFF
                    if mc.x != INVALID:
                        last_state.ctrl.stick_pull = mc.x / -1000
                    if mc.y != INVALID:
                        last_state.ctrl.stick_right = mc.y / 1000
                    if mc.z != INVALID:
                        last_state.ctrl.throttle = mc.z / 1000
                        last_state.ctrl.collective_up = mc.z / 1000
                    if mc.z != INVALID:
                        last_state.ctrl.pedals_right = mc.r / 1000

                    # TODO: assign buttons

                elif message.get_type() == 'MANUAL_SETPOINT':
                    # This line helps with type hints
                    ms: mavlink.MAVLink_manual_setpoint_message = message  # pyright:ignore[reportAssignmentType]
                    state_changed = True

                    if ms.mode_switch == 0:  # MARSH_MANUAL_SETPOINT_MODE_TARGET
                        if last_state.trgt is None:
                            last_state.trgt = AircraftData()
                        last_state.trgt.ctrl = Controls()
                        last_state.trgt.ctrl.stick_right = ms.roll
                        last_state.trgt.ctrl.stick_pull = ms.pitch
                        last_state.trgt.ctrl.pedals_right = ms.yaw
                        last_state.trgt.ctrl.throttle = ms.thrust
                        last_state.trgt.ctrl.collective_up = ms.thrust
                    elif ms.mode_switch == 1:  # MARSH_MANUAL_SETPOINT_MODE_TRIM
                        if last_state.trim is None:
                            last_state.trim = AircraftData()
                        last_state.trim.ctrl = Controls()
                        last_state.trim.ctrl.stick_right = ms.roll
                        last_state.trim.ctrl.stick_pull = ms.pitch
                        last_state.trim.ctrl.pedals_right = ms.yaw
                        last_state.trim.ctrl.throttle = ms.thrust
                        last_state.trim.ctrl.collective_up = ms.thrust
                    else:
                        if args.verbosity >= 1:
                            print(f'Unhandled MANUAL_SETPOINT.mode_switch {ms.mode_switch}, check MARSH_MANUAL_SETPOINT_MODE definitions')

                elif message.get_type() == 'SIM_STATE':
                    ss: mavlink.MAVLink_sim_state_message = message
                    state_changed = True

                    last_state.att = Attitude()
                    last_state.att.roll = ss.roll
                    last_state.att.pitch = ss.pitch
                    last_state.att.yaw = ss.yaw

                    last_state.a_body = XYZ()
                    last_state.a_body.x = ss.xacc
                    last_state.a_body.y = ss.yacc
                    last_state.a_body.z = ss.zacc

                    last_state.v_ned = NED()
                    last_state.v_ned.north = ss.vn
                    last_state.v_ned.east = ss.ve
                    last_state.v_ned.down = ss.vd

                    last_state.ned = NED()
                    # TODO: Add argument for reference location, calculate north and east from that
                    last_state.ned.down = -ss.alt

                elif message.get_type() == 'LOCAL_POSITION_NED':
                    lpn: mavlink.MAVLink_local_position_ned_message = message
                    state_changed = True

                    last_state.ned = NED()
                    last_state.ned.north = lpn.x
                    last_state.ned.east = lpn.y
                    last_state.ned.down = lpn.z

                    last_state.v_ned = NED()
                    last_state.v_ned.north = lpn.vx
                    last_state.v_ned.east = lpn.vy
                    last_state.v_ned.down = lpn.vz

                elif message.get_type() == 'ATTITUDE':
                    att: mavlink.MAVLink_attitude_message = message
                    state_changed = True

                    last_state.att = Attitude()
                    last_state.att.roll = att.roll
                    last_state.att.pitch = att.pitch
                    last_state.att.yaw = att.yaw

                elif message.get_type() == 'HIGHRES_IMU':
                    imu: mavlink.MAVLink_highres_imu_message = message
                    state_changed = True

                    last_state.a_body = XYZ()
                    last_state.a_body.x = imu.xacc
                    last_state.a_body.y = imu.yacc
                    last_state.a_body.z = imu.zacc

                elif message.get_type() == 'RAW_RPM':
                    rr: mavlink.MAVLink_raw_rpm_message = message
                    state_changed = True

                    if last_state.hrpm is None:
                        last_state.hrpm = HelicopterRPM()

                    if rr.index == 0:
                        last_state.hrpm.rotor = rr.frequency / config.pfd.rpm_r_nominal
                    else:
                        last_state.hrpm.engine = rr.frequency / config.pfd.rpm_e_nominal

                elif message.get_type() == 'SET_POSITION_TARGET_LOCAL_NED':
                    local: mavlink.MAVLink_set_position_target_local_ned_message = message
                    if last_state.trgt is None:
                        last_state.trgt = AircraftData()
                    if last_state.trgt.instr is None:
                        last_state.trgt.instr = Instruments()

                    # ignore all, don't use force instead of acceleration
                    type_mask = 0b0000_1101_1111_1111

                    alt = -local.z
                    if local.type_mask & mavlink.POSITION_TARGET_TYPEMASK_Z_IGNORE:
                        alt = nan
                    if not isnan(alt):
                        last_state.trgt.instr.alt = alt * config.instruments.alt_multiplier
                        type_mask ^= mavlink.POSITION_TARGET_TYPEMASK_Z_IGNORE  # flip the bit to not ignored
                        state_changed = True

                    speed = local.vx
                    if not isnan(local.vy):
                        speed = sqrt(local.vx ** 2 + local.vy ** 2)
                    if local.type_mask & mavlink.POSITION_TARGET_TYPEMASK_VX_IGNORE:
                        speed = nan
                    if not isnan(speed):
                        last_state.trgt.instr.ias = speed * config.instruments.speed_multiplier
                        # flip the bit to not ignored
                        type_mask ^= mavlink.POSITION_TARGET_TYPEMASK_VX_IGNORE
                        state_changed = True

                    climb = -local.vz
                    if local.type_mask & mavlink.POSITION_TARGET_TYPEMASK_VZ_IGNORE:
                        climb = nan
                    if not isnan(climb):
                        if last_state.trgt.v_ned is None:
                            last_state.trgt.v_ned = NED()
                        last_state.trgt.v_ned.down = climb
                        # flip the bit to not ignored
                        type_mask ^= mavlink.POSITION_TARGET_TYPEMASK_VZ_IGNORE
                        state_changed = True

                    yaw = local.yaw
                    if local.type_mask & mavlink.POSITION_TARGET_TYPEMASK_YAW_IGNORE:
                        yaw = nan
                    if not isnan(yaw):
                        if last_state.trgt.att is None:
                            last_state.trgt.att = Attitude()
                        last_state.trgt.att.yaw = yaw
                        # flip the bit to not ignored
                        type_mask ^= mavlink.POSITION_TARGET_TYPEMASK_YAW_IGNORE
                        state_changed = True

                    # Respond with the values that were set by this message
                    mav.position_target_local_ned_send(
                        round((time() - start_time) *
                              1000), mavlink.MAV_FRAME_LOCAL_NED, type_mask,
                        nan, nan, alt,
                        nan, nan, climb,
                        nan, nan, nan,
                        yaw, nan
                    )

                elif message.get_type() in ['PARAM_REQUEST_READ', 'PARAM_REQUEST_LIST', 'PARAM_SET']:
                    # check that this is relevant to us
                    if message.target_system == mav.srcSystem and message.target_component == mav.srcComponent:
                        if message.get_type() == 'PARAM_REQUEST_READ':
                            m: mavlink.MAVLink_param_request_read_message = message
                            params.send(config, mav, m.param_index, m.param_id)
                        elif message.get_type() == 'PARAM_REQUEST_LIST':
                            for i in range(len(params)):
                                params.send(config, mav, i)
                        elif message.get_type() == 'PARAM_SET':
                            m: mavlink.MAVLink_param_set_message = message
                            # check that parameter is defined and sent as float
                            if m.param_id in params and m.param_type == mavlink.MAV_PARAM_TYPE_REAL32:
                                params.set(config, m.param_id, m.param_value)
                                q.put(('config', config.dict(by_alias=True)))
                            params.send(config, mav, -1, m.param_id)

                elif message.get_type() == 'V2_EXTENSION':
                    # smol payload passthrough
                    ext: mavlink.MAVLink_v2_extension_message = message
                    if ext.message_type == 44400:  # may change to 24400 if registered
                        try:
                            # some implementations don't handle payload truncation well,
                            # this way only unpacks the first object and ignores any trailing data
                            unpacker = msgpack.Unpacker()
                            unpacker.feed(bytes(ext.payload))
                            decoded = next(unpacker)
                            state = AircraftState.from_smol(decoded)

                            state_changed = last_state.update(state, True)
                        except Exception as e:
                            print('Error in V2_EXTENSION payload:', e)

        except ConnectionResetError:
            # thrown on Windows when there is no peer listening
            pass

        if manager_connected and time() > manager_timeout:
            manager_connected = False
            if args.verbosity >= 0:
                print('Lost connection to simulation manager')

        if state_changed:
            state = last_state
            state.model_instruments(config)
            if state.trgt is not None:
                state.trgt.model_instruments(config)
            if state.trim is not None:
                state.trim.model_instruments(config)
            q.put(('smol', state.smol()))


if __name__ == '__main__':
    # try accessing config with strings
    config = Config()
    print(getattr(getattr(config, 'rpctask'), 'ok_tolerance'))
    setattr(getattr(config, 'rpctask'), 'ok_tolerance', 0.02)
    print(getattr(getattr(config, 'rpctask'), 'ok_tolerance'))

    # check accessing through ParamConfig
    param = ParamConfig()
    print(param.get(config, 'ok_tolerance'))
    param.set(config, 'ok_tolerance', 0.01)
    print(config.rpctask.ok_tolerance)
