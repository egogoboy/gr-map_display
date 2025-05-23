import argparse
import json
from multiprocessing import Process, Queue
from time import time
import tomli
import re
from typing import Dict
import yaml

from . import __version__
from .server import run_server
from .config import Config
from .sources.mytypes import RunFn, SetupFn

from .sources import demo, rpctask, approach, smol, flightgear, marsh, confighelp


def main():
    parser = argparse.ArgumentParser(
        prog='lidia',
        description='serve an aircraft instruments panel as a web page',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog='you can also see help for a specific source: "lidia <src> --help"')
    parser.add_argument('-V', '--version', action='version', version=f'{parser.prog} {__version__}',
                        help='display package version')
    parser.add_argument('-v', '--verbose', action='count', dest='verbosity',
                        help='increase amount of printed information, can be added multiple times', default=0)
    parser.add_argument('-q', '--quiet', action='count',
                        help='decrease amount of printed information', default=0)
    parser.add_argument('-c', '--config', type=str,
                        help='config files separated with comma, in order of applying')
    parser.add_argument('-C', '--config-keys', type=str,
                        help='properties as comma separated dotted keys')
    parser.add_argument('-H', '--http-host', type=str,
                        help='hosts to accept for web page', default='0.0.0.0')
    parser.add_argument('-P', '--http-port', type=int,
                        help='port to serve the web page on', default=5555)
    parser.add_argument('-U', '--passthrough-host', type=str,
                        help='address to forward state to', default='127.0.0.1')
    parser.add_argument('-O', '--passthrough-port', type=int,
                        help='port to forward the state to (e.g. 50010)')
    subparsers = parser.add_subparsers(title='source', required=True, dest='source',
                                       help='source name', description='select where to get aircraft state')

    sources: Dict[str, RunFn] = {}
    for source_module in [demo, rpctask, approach, smol, flightgear, marsh, confighelp]:
        setup: SetupFn = source_module.setup
        name, run_function = setup(subparsers)
        sources[name] = run_function

    try:
        import argcomplete
        argcomplete.autocomplete(parser)
    except ImportError:
        pass

    args = parser.parse_args()

    args.verbosity -= args.quiet
    if args.verbosity >= 1:
        # mimic '=' specifier from python 3.8 to maintain 3.7 compatibility
        print(f'args={args}')

    config = Config()
    if args.config is not None:
        for config_filename in args.config.split(','):
            config_filename: str
            update_dict = None
            if config_filename.lower().endswith('.json'):
                update_dict = json.load(open(config_filename))
            elif config_filename.lower().endswith('.yaml') or config_filename.lower().endswith('.yml'):
                update_dict = yaml.safe_load(open(config_filename))
            elif config_filename.lower().endswith('.toml'):
                update_dict = tomli.load(open(config_filename, 'rb'))
            else:
                parser.error(
                    'Config files have to end with ".json", ".yaml", ".yml" or ".toml" to detect correct parser type')
            if update_dict is not None:
                config = config.updated(update_dict)
    if args.config_keys is not None:
        # FIXME: does not handle single quote escaping
        separator = re.compile(
            r"""(?!\B"[^"]*),(?![^"]*"\B)""")  # comma not between double quotes
        toml_string = '\n'.join(re.split(separator, args.config_keys))
        update_dict = tomli.loads(toml_string)
        config = config.updated(update_dict)
    if config.start_time is None:
        config.start_time = time()
    if args.verbosity >= 1:
        print(f'config=Config({config})')

    queue = Queue()
    server_process = Process(target=run_server, args=(queue, args, config))
    server_process.start()

    if args.verbosity >= 0 and not args.source.endswith('help'):
        print(f"""\
Lidia GUIs driven by '{args.source}' source served on:
    - Controls View (aka RPC task): http://localhost:{args.http_port}/controls
    - Primary Flight Display: http://localhost:{args.http_port}/pfd
    - Ship Approach: http://localhost:{args.http_port}/approach

(see this list and configuration at http://localhost:{args.http_port}/info)""")
        if args.passthrough_port is not None:
            print(
                f'State in SMOL forwarded via UDP to {args.passthrough_host}:{args.passthrough_port}')

    try:
        (sources[args.source])(queue, args, config)

    except KeyboardInterrupt:
        if args.verbosity >= 0 and not args.source.endswith('help'):
            print('Exiting main loop')
    except Exception as e:  # needed to stop the server process
        server_process.terminate()
        raise e

    server_process.terminate()
