"""listen to UDP packets from RPC simulator for approach task"""
from argparse import _SubParsersAction, ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
from multiprocessing import Queue
import socket
from struct import unpack_from
from typing import Tuple

from ..aircraft import *
from ..config import Config
from .mytypes import RunFn


def setup(subparsers: _SubParsersAction) -> Tuple[str, RunFn]:
    NAME = 'approach'
    parser: ArgumentParser = subparsers.add_parser(
        NAME,
        help=__doc__,
        formatter_class=ArgumentDefaultsHelpFormatter)
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
                # Contents of UDP packet is 4 doubles:
                # - Position of helicopter north of ship, in meters
                # - Position of helicopter east of ship, in meters
                # - Position of helicopter above  ship, in meters
                # - Helicopter heading, in radians
                #   - 0 pointing north, pi/2 (90⁰) pointing east
                (north, east, altitude, yaw) = unpack_from('>' + 'd' * 4, data)

                state = AircraftState()
                state.ned = NED()
                state.ned.north = north
                state.ned.east = east
                state.ned.down = -altitude
                state.att = Attitude()
                state.att.yaw = yaw
                state.model_instruments(config)
                state.set_time(config)

                q.put(('smol', state.smol()))
            except socket.timeout:
                continue
