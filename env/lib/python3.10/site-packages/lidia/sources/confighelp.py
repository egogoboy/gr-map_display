"""mock source to show detailed help about configuration"""
from argparse import _SubParsersAction, ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
import json
from multiprocessing import Queue
from os import path
from typing import Tuple

from ..config import Config, schema_location, write_schema
from .mytypes import RunFn


def setup(subparsers: _SubParsersAction) -> Tuple[str, RunFn]:
    NAME = 'confighelp'
    parser: ArgumentParser = subparsers.add_parser(
        NAME,
        help=__doc__,
        formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('-t', '--template', type=str,
                        help='filename to write template, ending in ".json", ".yaml" or ".toml"')
    parser.add_argument('--write-schema', action='store_true',
                        help='write JSON Schema generated from current `Config` class')

    return (NAME, run)


def run(_q: Queue, args: Namespace, config: Config):
    if not path.exists(schema_location()) or args.write_schema:
        write_schema()

    if args.template is not None:
        fname: str = args.template
        # Windows path with backward slashes doesn't work
        url = 'file:' + schema_location().replace('\\', '/')
        template = {'$schema': url}
        if fname.lower().endswith('.json'):
            with open(fname, 'w') as out:
                json.dump(template, out)
        elif fname.lower().endswith('.yaml') or fname.lower().endswith('.yml'):
            with open(fname, 'w') as out:
                out.write(
                    f'# Lidia Config schema for redhat.vscode-yaml\n# yaml-language-server: $schema={url}\n\n')
        elif fname.lower().endswith('.toml'):
            with open(fname, 'w') as out:
                # `tomli` (a.k.a. `tomllib` in >= 3.11) doesn't write toml files
                out.write(
                    f'# Lidia Config schema for tamasfe.even-better-toml\n"$schema" = "{url}"\n\n')
        else:
            raise ValueError(
                'Config files have to end with ".json", ".yaml", ".yml" or ".toml" to write correct format')

    root_path = path.abspath(path.dirname(__file__))
    help_path = path.join(root_path, 'confighelp.md')
    with open(help_path, 'r') as help_file:
        print(help_file.read())

    raise KeyboardInterrupt  # exit immediately using the usual control flow
