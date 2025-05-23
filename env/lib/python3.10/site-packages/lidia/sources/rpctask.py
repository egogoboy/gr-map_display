"""listen to UDP packets from Rotorcraft-Pilot Coupling Task simulator"""
from argparse import _SubParsersAction, ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
from multiprocessing import Queue
import socket
from struct import unpack_from
from typing import Tuple

from ..aircraft import *
from ..config import Config
from .mytypes import RunFn


def setup(subparsers: _SubParsersAction) -> Tuple[str, RunFn]:
    NAME = 'rpctask'
    parser: ArgumentParser = subparsers.add_parser(
        NAME,
        help=__doc__,
        formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--ip',
                        help='listen UDP adress', default='0.0.0.0')
    parser.add_argument('-p', '--port', type=int,
                        help='listen UDP port', default=5004)

    return (NAME, run)


def run(q: Queue, args: Namespace, _config: Config):

    last_trim = Controls()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        # Timeout is required to handle leaving with Ctrl+C
        sock.settimeout(1.0)
        sock.bind((args.ip, args.port))
        if args.verbosity >= 0:
            print(f'Listening for UDP packets on {args.ip}:{args.port}')

        while True:
            try:
                data, _ = sock.recvfrom(1024)
                # As named in the original FlightGear protocol file
                # cyclic has coordinates 0,0 in bottom left and 1,1 in top right
                (pitch_ctrl, roll_ctrl, pwr_ctrl,
                 pitch_target, roll_target, pwr_target,
                 cyc_ftr, coll_ftr) = unpack_from('>' + 'd' * 8, data)

                state = AircraftState()
                state.ctrl = Controls()
                state.ctrl.stick_right = (roll_ctrl * 2.0) - 1.0
                state.ctrl.stick_pull = (pitch_ctrl * -2.0) + 1.0
                state.ctrl.collective_up = pwr_ctrl

                state.trgt = AircraftData()
                state.trgt.ctrl = Controls()
                state.trgt.ctrl.stick_right = (roll_target * 2.0) - 1.0
                state.trgt.ctrl.stick_pull = (pitch_target * -2.0) + 1.0
                state.trgt.ctrl.collective_up = pwr_target

                state.btn = Buttons()
                if cyc_ftr > 0.5:
                    state.btn.cyc_ftr = True
                if coll_ftr > 0.5:
                    state.btn.coll_ftr = True

                if len(data) >= 8 * 14:
                    (up_bdr_cyc, low_bdr_cyc, right_bdr_cyc, left_bdr_cyc,
                     up_bdr_coll, low_bdr_coll) = unpack_from('>' + 'd' * 6, data, 8 * 8)
                    state.brdr = Borders()
                    state.brdr.high.stick_right = (right_bdr_cyc * 2.0) - 1.0
                    state.brdr.low.stick_right = (left_bdr_cyc * 2.0) - 1.0
                    state.brdr.high.stick_pull = (low_bdr_cyc * -2.0) + 1.0
                    state.brdr.low.stick_pull = (up_bdr_cyc * -2.0) + 1.0
                    state.brdr.high.collective_up = up_bdr_coll
                    state.brdr.low.collective_up = low_bdr_coll

                if state.btn.coll_ftr:
                    last_trim.collective_up = state.ctrl.collective_up
                if state.btn.cyc_ftr:
                    last_trim.stick_right = state.ctrl.stick_right
                    last_trim.stick_pull = state.ctrl.stick_pull
                state.trim = AircraftData()
                state.trim.ctrl = last_trim

                q.put(('smol', state.smol()))
            except socket.timeout:
                continue
