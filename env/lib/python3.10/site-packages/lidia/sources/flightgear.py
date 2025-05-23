"""listen to UDP packets from FlightGear native socket protocol"""
from argparse import _SubParsersAction, ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
from multiprocessing import Queue
import socket
from typing import Tuple

from ..aircraft import *
from ..config import Config
from .mytypes import RunFn, FGNetFDM


def setup(subparsers: _SubParsersAction) -> Tuple[str, RunFn]:
    NAME = 'flightgear'
    parser: ArgumentParser = subparsers.add_parser(
        NAME,
        help=__doc__,
        formatter_class=ArgumentDefaultsHelpFormatter,
        epilog="""To send packets at 30Hz from a local FlightGear instance,
add this command line argument: --native-fdm=socket,out,30,127.0.0.1,5004,udp""")
    parser.add_argument('-i', '--ip',
                        help='listen UDP adress', default='0.0.0.0')
    parser.add_argument('-p', '--port', type=int,
                        help='listen UDP port', default=5004)

    return (NAME, run)


def run(q: Queue, args: Namespace, config: Config):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        # Timeout is required to handle leaving with Ctrl+C
        sock.settimeout(1.0)
        sock.bind((args.ip, args.port))
        if args.verbosity >= 0:
            print(f'Listening for UDP packets on {args.ip}:{args.port}')

        while True:
            try:
                data, _ = sock.recvfrom(1024)
                fg = FGNetFDM.from_bytes(data)

                FT = 0.3048
                """conversion multiplier from feet to meters"""

                state = AircraftState()
                state.ned = NED()
                # TODO: Add argument for reference location, calculate north and east from that
                state.ned.down = -fg.altitude
                state.att = Attitude()
                state.att.roll = fg.phi
                state.att.pitch = fg.theta
                state.att.yaw = fg.psi
                # Velocities in ft/s
                state.v_body = XYZ()
                state.v_body.x = fg.v_body_u * FT
                state.v_body.y = fg.v_body_v * FT
                state.v_body.z = fg.v_body_w * FT
                state.v_ned = NED()
                state.v_ned.north = fg.v_north * FT
                state.v_ned.east = fg.v_east * FT
                state.v_ned.down = fg.v_down * FT
                state.ctrl = Controls()
                state.ctrl.stick_pull = -fg.elevator
                state.ctrl.stick_right = fg.right_aileron
                state.ctrl.pedals_right = fg.rudder

                state.model_instruments(config)
                if state.instr.ralt is not None:
                    state.instr.ralt = fg.agl * config.instruments.altitude_multiplier
                state.set_time(config)

                q.put(('smol', state.smol()))
            except socket.timeout:
                continue
