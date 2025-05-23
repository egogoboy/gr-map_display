
"""listen to UDP packets with SMOL encoded as MessagePack or JSON"""
from argparse import _SubParsersAction, ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
import json
import msgpack
from multiprocessing import Queue
import socket
from typing import Tuple

from ..aircraft import *
from ..config import Config
from .mytypes import RunFn


def setup(subparsers: _SubParsersAction) -> Tuple[str, RunFn]:
    NAME = 'smol'
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

                decoded = None
                if data[0] == ord('{'):
                    try:
                        decoded = json.loads(data)
                    except json.JSONDecodeError as e:
                        print(e)
                else:
                    try:
                        decoded = msgpack.unpackb(data)
                    except msgpack.exceptions.ExtraData:
                        pass  # Some applications put extra bytes in the UDP packet
                    except Exception as e:
                        print(e)

                if decoded is not None:
                    try:
                        state = AircraftState.from_smol(decoded)
                        state.model_instruments(config)
                        if state.trgt is not None:
                            state.trgt.model_instruments(config)
                        if state.trim is not None:
                            state.trim.model_instruments(config)
                        q.put(('smol', state.smol()))
                    except Exception as e:
                        if args.verbosity > 0:
                            print('Error', e, 'in data', decoded)
                        else:
                            print(e)

            except socket.timeout:
                continue
