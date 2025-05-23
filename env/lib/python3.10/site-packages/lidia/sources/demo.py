"""looping simulation demonstrating GUI"""
from argparse import _SubParsersAction, ArgumentDefaultsHelpFormatter, ArgumentError, ArgumentParser, Namespace
from math import pi, sin
from multiprocessing import Queue
from time import sleep, time
from typing import Tuple

from ..aircraft import *
from ..config import Config
from .mytypes import RunFn


def setup(subparsers: _SubParsersAction) -> Tuple[str, RunFn]:
    NAME = 'demo'
    parser: ArgumentParser = subparsers.add_parser(
        NAME,
        help=__doc__,
        formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('-T', '--period', type=float,
                        help='loop time in seconds', default=5.0)
    parser.add_argument('-f', '--frequency', type=float,
                        help='number of messages sent per second', default=30.0)
    parser.add_argument('--no-trim', action='store_false', dest='trim',
                        help='do not demonstrate trim function')
    parser.add_argument('--no-borders', action='store_false', dest='borders',
                        help='do not demonstrate borders function')
    parser.add_argument('--outside-range', action='store_true',
                        help='demonstrate values outside allowed range')
    parser.add_argument('--alt-zero', type=float,
                        help='altitude to hover around', default=65.0)
    parser.add_argument('--alt-change', type=float,
                        help='altitude change amplitude', default=10.0)

    return (NAME, run)


def run(q: Queue, args: Namespace, config: Config):
    if args.period <= 0:
        raise ArgumentError(args.frequency, 'period must be positive')
    if args.frequency <= 0:
        raise ArgumentError(args.frequency, 'frequency must be positive')

    outside_offset = 0.6 if args.outside_range else 0.0

    def val(phase):
        """Generate a sinusoidal value with phase offset (from 0 to 1)"""
        return 0.6 * sin((time() / args.period + phase) * 2 * pi) + outside_offset

    def cycle_index(): return int(time() // args.period) % 3
    def current_phase(): return (time() / args.period) % 1

    last_trim = Controls()
    last_v_ned = NED()
    # prevent zero division on first iteration
    last_time = time() - 1 / args.frequency

    while True:
        state = AircraftState()
        state.ned = NED()
        state.ned.down = -args.alt_zero - args.alt_change * val(0.75)

        state.att = Attitude()
        state.att.pitch = 0.5 * val(0)
        state.att.roll = 0.5 * val(0.25)
        state.att.yaw = 0.5 * val(0.5)

        state.v_body = XYZ()
        state.v_body.x = 15 + 2.5 * val(0.5)
        state.v_body.y = 1 * val(0.65)
        state.v_body.z = 2 * val(0.25)

        state.v_ned = state.xyz2ned(state.v_body)

        dt = time() - last_time
        state.a_ned = NED(down=9.81) + (state.v_ned - last_v_ned) / dt
        # a_body is simulated by instruments model if it's unset
        last_v_ned = state.v_ned
        last_time = time()

        state.ctrl = Controls()
        state.ctrl.stick_pull = val(0.1)
        state.ctrl.stick_right = val(0.35)
        state.ctrl.pedals_right = val(0.6)
        state.ctrl.collective_up = 0.3 + 0.5 * (val(0.2) + outside_offset)

        state.hrpm = HelicopterRPM()
        state.hrpm.rotor = 1.0 + 0.2 * val(0.1)
        state.hrpm.engine = 1.0 + 0.1 * val(0.0)
        # Simulate sprag clutch
        state.hrpm.rotor = max(state.hrpm.rotor, state.hrpm.engine)

        state.trgt = AircraftData()
        state.trgt.ctrl = Controls()
        state.trgt.ctrl.stick_pull = val(0.55)
        state.trgt.ctrl.stick_right = val(0.3)
        state.trgt.ctrl.pedals_right = val(0.5)
        state.trgt.ctrl.collective_up = 0.3 + 0.5 * (val(0.4) + outside_offset)
        state.trgt.att = Attitude()
        state.trgt.att.pitch = 0.3 * val(0.1)
        state.trgt.att.roll = 0.3 * val(0.35)
        state.trgt.att.yaw = 0.3 * val(0.6)
        state.trgt.instr = Instruments()
        state.trgt.instr.ias = 28 + 5 * val(0.6)
        state.trgt.instr.alt = args.alt_zero * config.instruments.alt_multiplier
        state.trgt.v_ned = NED()
        state.trgt.v_ned.down = 2 * val(0.6)

        state.btn = Buttons()
        if cycle_index() == 1 and args.trim:
            if current_phase() < 0.4:
                state.btn.coll_ftr = True
            if current_phase() > 0.6:
                state.btn.cyc_ftr = True

        if state.btn.coll_ftr:
            last_trim.collective_up = state.ctrl.collective_up
        if state.btn.cyc_ftr:
            last_trim.stick_right = state.ctrl.stick_right
            last_trim.stick_pull = state.ctrl.stick_pull
        state.trim = AircraftData()
        state.trim.ctrl = last_trim

        state.brdr = Borders()
        if cycle_index() == 2 and args.borders:
            if current_phase() < 0.5:
                state.brdr.low = Controls.from_list(
                    [-0.8, -0.8, 0.1, -0.8, 0.1])
                state.brdr.high = Controls.from_list(
                    [0.8, 0.8, 0.9, 0.8, 0.9])
            if current_phase() > 0.5:
                state.brdr.low = Controls.from_list(
                    [-0.5, -0.5, 0.25, -0.5, 0.25])
                state.brdr.high = Controls.from_list(
                    [0.5, 0.5, 0.75, 0.5, 0.75])

        state.model_instruments(config)
        if cycle_index() == 0:
            state.instr.gs = None
            state.instr.ralt = None
        else:
            state.instr.qnh = None

        state.set_time(config)

        state.instr.tcas = []
        state.instr.tcas.append(TrafficObject(
            vol=TrafficVolume.OTHER_TRAFFIC,
            brg=1.0, dist=12000, alt=100, vsi=-1
        ))
        state.instr.tcas.append(TrafficObject(
            vol=TrafficVolume.PROXIMATE_TRAFFIC,
            brg=0.3, dist=18000, alt=30, vsi=1
        ))
        state.instr.tcas.append(TrafficObject(
            vol=TrafficVolume.TRAFFIC_ADVISORY,
            brg=-0.3, dist=10000, alt=-10, vsi=1
        ))
        state.instr.tcas.append(TrafficObject(
            vol=TrafficVolume.RESOLUTION_ADVISORY,
            brg=-0.5, dist=5000, alt=-120, vsi=0
        ))
        # Keep traffic objects fixed in world space
        for trobj in state.instr.tcas:
            trobj.brg -= state.att.yaw

        q.put(('smol', state.smol()))
        sleep(1 / args.frequency)
