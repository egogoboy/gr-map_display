import argparse
from enum import auto, IntEnum
import inspect
from io import StringIO, TextIOBase
import os
import platform
from pydantic import BaseModel
import re
import sys
from typing import Any, Dict, List, Tuple, Type

# setup cross-platform getch() and clear()
if platform.system() == "Windows":
    import msvcrt

    def getch():
        return msvcrt.getwch()

    def clear():
        os.system('cls')
else:
    import tty
    import termios

    def getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    def clear():
        os.system('clear')

this_path = os.path.dirname(os.path.realpath(__file__))
lidia_path = os.path.join(this_path, '..', '..')
sys.path.append(lidia_path)
from lidia.aircraft import AircraftData, VectorModel  # noqa prevent moving to top of file


class FieldInfo(BaseModel):
    """Details of a `AircraftData` field"""

    name: str
    """Field name"""
    docstring: str
    """Field docstring"""
    field_type: Type
    """Contained type"""

    @staticmethod
    def inspect_AircraftData() -> List['FieldInfo']:
        infos = []
        pattern = re.compile(
            r'^[ \t]+([a-z_]+): Optional\[(?:[A-Za-z]+)\] = None\n[ \t]+"""([^"]+)"""$', flags=re.MULTILINE)
        for name, doc in re.findall(pattern, inspect.getsource(AircraftData)):
            field = AircraftData.__fields__[name]
            infos.append(FieldInfo(
                name=name,
                docstring=doc,
                field_type=field.annotation.__args__[
                    0],  # annotation type Optional
            ))

        return infos


class Generator(IntEnum):
    MATLAB = auto()
    MBDYN = auto()
    MBDYN_TYPE = auto()


class Model:
    def __init__(self, output: str, verbose=False):
        self.output = output
        self.editing_output = False
        self.previous_output = ''
        self.verbose = verbose
        self.last_key = 0

        self.parts = ['main', 'trgt', 'trim']
        self.selected_part = self.parts[0]

        # only serialization of vectors is supported
        self.toggles = [info for info in FieldInfo.inspect_AircraftData()
                        if (issubclass(info.field_type, VectorModel) or info.field_type is int)]
        self.enabled = {part: ([False] * len(self.toggles))
                        for part in self.parts}

        self.generators = [
            (Generator.MATLAB, 'MATLAB', '.m'),
            (Generator.MBDYN, 'MBDyn', '{.set, .drv, .elm}'),
        ]
        self.enabled_gens = [False] * len(self.generators)

        self.extra_choices = 3
        self.selected_choice = 0

        self.status = ''

    @property
    def choices_num(self) -> int:
        return len(self.toggles) + len(self.parts) + len(self.generators) + self.extra_choices

    @property
    def selected_part_index(self) -> int:
        return next(i for i, p in enumerate(self.parts) if p == self.selected_part)

    @property
    def enabled_num(self) -> int:
        return sum(len([en for en in self.enabled[p] if en]) for p in self.parts)


class Command(IntEnum):
    QUIT = auto()
    MAKE = auto()


class Message(IntEnum):
    KEY = auto()
    STATUS = auto()


def view(model: Model) -> None:
    clear()
    if model.editing_output:
        print('Edit output filename')
        print('Confirm editing with Enter, cancel with Esc\n')
    else:
        print('Choose fields to be serialized in message')
        print('Use arrows or j, k to move, select with Enter or Space\n')

    for i, (info, enabled) in enumerate(zip(model.toggles, model.enabled[model.selected_part])):
        print('{}({}) {:<16}{} ({})'.format(
            '->' if i == model.selected_choice else '  ',
            '*' if enabled else ' ',
            info.name if model.selected_part == model.parts[0] else '{}.{}'.format(
                model.selected_part, info.name),
            info.docstring,
            info.field_type.__name__))
    print()
    for i, part in enumerate(model.parts):
        print('{}({}) {} edit {} message'.format(
            '->' if i == model.selected_choice - len(model.toggles) else '  ',
            '*' if part == model.selected_part else ' ',
            '[Tab]' if i == (model.selected_part_index +
                             1) % len(model.parts) else '     ',
            part))
    print()
    for i, (_, name, extension) in enumerate(model.generators):
        print('{}({}) {}: {}{}'.format(
            '->' if i == model.selected_choice -
            len(model.toggles) - len(model.parts) else '  ',
            '*' if model.enabled_gens[i] else ' ',
            name,
            model.output,
            extension))

    print('\n{}[o]utput file: {}'.format(
        '->' if model.selected_choice == model.choices_num - 3 else '  ',
        model.output + ('█' if model.editing_output else '')))
    gen_count = model.enabled_gens.count(True)
    field_count = sum([model.enabled[p].count(True) for p in model.parts])
    print('{}[g]enerate with {} generator{} for {} field{}'.format(
        '->' if model.selected_choice == model.choices_num - 2 else '  ',
        gen_count, '' if gen_count == 1 else 's',
        field_count, '' if field_count == 1 else 's',
    ))
    print('{}[q]uit'.format(
        '->' if model.selected_choice == model.choices_num - 1 else '  '))

    print('\n{}'.format(model.status))
    if model.verbose:
        print('last key pressed {}'.format(model.last_key))


def update(model: Model, message: Message, data: Any) -> Tuple[Model, List[Command]]:
    commands = []
    if message == Message.KEY:
        key: int = data
        model.last_key = key

        if model.editing_output:
            model = update_output(model, key)
        else:
            model, cs = update_menu(model, key)
            commands.extend(cs)

    elif message == Message.STATUS:
        status: str = data
        model.status = status

    return model, commands


def update_output(model: Model, key: int) -> Model:
    if key >= 32 and key <= 126:  # printable ASCII characters
        model.output += chr(key)
    elif key in [8, 127]:  # Backspace (Win, Linux)
        model.output = model.output[:-1]
    elif key == 13:  # Enter
        if model.output == '':
            model.status = 'Empty output filename!'
        else:
            model.editing_output = False
            model.status = ''
    elif key == 27:  # Esc
        model.output = model.previous_output
        model.editing_output = False
        model.status = 'Edit cancelled'
    return model


def update_menu(model: Model, key: int) -> Tuple[Model, List[Command]]:
    commands = []
    if key in [ord('o'), ord('O')]:
        model.selected_choice = model.choices_num - 3
        model.previous_output = model.output
        model.editing_output = True
    elif key in [ord('g'), ord('G')]:
        model.selected_choice = model.choices_num - 2
        commands.append(Command.MAKE)
    elif key in [ord('q'), ord('Q'), 3]:  # Ctrl+C
        commands.append(Command.QUIT)
    elif key in [ord('j'), ord('J'), 66, 80]:  # Linux down, Win down
        model.selected_choice = (
            model.selected_choice + 1) % model.choices_num
    elif key in [ord('k'), ord('K'), 65, 72]:  # Linux up, Win up
        model.selected_choice = (
            model.selected_choice - 1) % model.choices_num
    elif key == 9:  # Tab
        model.selected_part = model.parts[(
            model.selected_part_index + 1) % len(model.parts)]

    elif key in [13, 32]:  # Enter, Space
        i = model.selected_choice
        if 0 <= i < len(model.toggles):
            model.enabled[model.selected_part][i] = not model.enabled[model.selected_part][i]
        i -= len(model.toggles)

        if 0 <= i < len(model.parts):
            model.selected_part = model.parts[i]
        i -= len(model.parts)

        if 0 <= i < len(model.generators):
            model.enabled_gens[i] = not model.enabled_gens[i]
        i -= len(model.generators)

        if model.selected_choice == model.choices_num - 3:
            model.previous_output = model.output
            model.editing_output = True
        elif model.selected_choice == model.choices_num - 2:
            commands.append(Command.MAKE)
        elif model.selected_choice == model.choices_num - 1:
            commands.append(Command.QUIT)

    return model, commands


def main():
    parser = argparse.ArgumentParser(
        description='generate MATLAB function to pack data for lidia',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                        help='increase amount of shown information')
    parser.add_argument('-o', '--output', default='pack_lidia',
                        help='output file path')
    args = parser.parse_args()

    model = Model(os.path.normpath(args.output), args.verbose)
    messages = []
    while True:
        commands = []
        for msg, data in messages:
            mdl, c = update(model, msg, data)
            model = mdl
            commands.extend(c)
            messages.clear()

        for cmd in commands:
            if cmd == Command.QUIT:
                sys.exit(0)
            if cmd == Command.MAKE:
                selected = {p: [info.name for info, en in zip(
                    model.toggles, model.enabled[p]) if en] for p in model.parts}
                if len(os.path.dirname(model.output)) > 0:
                    os.makedirs(os.path.dirname(model.output), exist_ok=True)
                filename = os.path.basename(model.output)

                status = []
                infos = {
                    info.name: info for info in FieldInfo.inspect_AircraftData()}
                for enabled, (gen, name, extension) in zip(model.enabled_gens, model.generators):
                    if not enabled:
                        continue

                    out_path = model.output + extension
                    if gen == Generator.MATLAB:
                        forbidden_characters = re.findall(
                            r'[^A-Za-z0-9_]', model.output)
                        if len(forbidden_characters) > 0:
                            status.append(
                                f'Error: characters {set(forbidden_characters)} not allowed in MATLAB function name')
                        else:
                            with open(out_path, 'w') as out:
                                codegen_matlab(out, filename, infos,
                                               selected['main'], selected['trgt'], selected['trim'])
                            status.append(
                                f'Saved {name} generator to {out_path}')
                    elif gen == Generator.MBDYN:
                        codegen_mbdyn(model.output, infos,
                                      selected['main'], selected['trgt'], selected['trim'])
                        status.append(f'Saved {name} generator to {out_path}')
                if model.enabled_gens.count(True) == 0:
                    status.append('No output format enabled')
                messages.append((Message.STATUS, '\n'.join(status)))

        view(model)
        if len(messages) > 0:
            continue

        key = ord(getch())
        messages.append((Message.KEY, key))


MBD_PREFIX = 'LIDIA_'


def codegen_mbdyn(output: str, infos: Dict[str, FieldInfo],
                  main_fields: List[str], trgt_fields: List[str], trim_fields: List[str]) -> None:
    filename = os.path.basename(output)
    defines = ['output']
    for group, prefix in [(main_fields, ''), (trgt_fields, 'trgt_'), (trim_fields, 'trim_')]:
        for f in group:
            if issubclass(infos[f].field_type, BaseModel):
                defines.extend(
                    f'{prefix}{f}_{a}' for a in infos[f].field_type.__fields__)
            else:
                defines.append(f'{prefix}{f}')
    with open(output + '.set', 'w') as out_set:
        out_set.write('''##### Generated with pack_maker.py
# constants definition file
# include it in your model like this:
#
# include: "./{}.set";

### identifiers:
'''.format(filename))

        next_id = 55000
        for d in defines:
            out_set.write('set: const integer {}{} = {};\n'.format(
                MBD_PREFIX,
                d.upper(),
                next_id))
            next_id += 1
        out_set.write('''
# vim:ft=mbd
''')

    with open(output + '.drv', 'w') as out_drv:
        out_drv.write('''##### Generated with pack_maker.py
# drive definition file
# include it in your model like this:
#
# include: "./{}.drv";
#
# modify the following drive callers to get relevant data from model
# example of getting Z-axis position of NODE_CG:
#
# drive caller: LIDIA_NED_DOWN, node, NODE_CG, structural, string, "X[3]", direct;

### drive templates:
'''.format(filename))
        for d in defines[1:]:  # skip stream id
            out_drv.write('drive caller: {}{}, const, 0;\n'.format(
                MBD_PREFIX,
                d.upper()))
        out_drv.write('''
# vim:ft=mbd
''')

    with open(output + '.elm', 'w') as out_elm:
        out_elm.write('''##### Generated with pack_maker.py
# output stream definition
# include it in your model **inside the elements block** like this:
#
# include: "./{}.elm";
#
# you also need to increase the number of output elements in the control data block:
# begin: control data;
#     output elements: +1;
# end: control data;

### output stream definition
stream output: {}{},
\tstream name, "Lidia output in SMOL format",
\tcreate, no,
\tport, 5100,
\thost, "127.0.0.1",
\tsocket type, udp,
'''.format(filename, MBD_PREFIX, defines[0].upper()))

        values = StringIO()
        pack_fieldlists(Generator.MBDYN, values, infos,
                        main_fields, trgt_fields, trim_fields)

        out_elm.write('\tvalues, {},\n'.format(values.getvalue().count('\n')))
        out_elm.write(values.getvalue())
        out_elm.write('''
\tmodifier, copy cast,
\t\tswap, f, d, i,
''')
        type_out = StringIO()
        pack_fieldlists(Generator.MBDYN_TYPE, type_out, infos,
                        main_fields, trgt_fields, trim_fields)
        out_elm.write(type_out.getvalue()[:-2])  # strip ending ',\n'
        out_elm.write('''
\t;

# vim:ft=mbd
''')


def codegen_matlab(out: TextIOBase, function_name: str, infos: Dict[str, FieldInfo],
                   main_fields: List[str], trgt_fields: List[str], trim_fields: List[str]) -> None:
    out.write('function data = {}( ...\n    '.format(function_name))
    arglist = []
    for f in main_fields:
        if issubclass(infos[f].field_type, BaseModel):
            arglist.extend('{}_{}'.format(f, a)
                           for a in infos[f].field_type.__fields__)
        else:
            arglist.append(f)
    for f in trgt_fields:
        if issubclass(infos[f].field_type, BaseModel):
            arglist.extend('trgt_{}_{}'.format(f, a)
                           for a in infos[f].field_type.__fields__)
        else:
            arglist.append('trgt_{}'.format(f))
    for f in trim_fields:
        if issubclass(infos[f].field_type, BaseModel):
            arglist.extend('trim_{}_{}'.format(f, a)
                           for a in infos[f].field_type.__fields__)
        else:
            arglist.append('trim_{}'.format(f))

    out.write(', ...\n    '.join(arglist))
    out.write(''') % {} arguments
%PACK_LIDIA Pack aircraft data into binary format
%   The output is array of bytes in MsgPack format, as expected by
%   'smol' source of lidia package
%
%   This is generated using pack_maker.py to create code suitable for
%   use in Simulink - known size of I/O (see below), no map or struct usage
%
%   Arguments:
'''.format(len(arglist)))
    for fieldgroup, arg_prefix, doc_prefix in [(main_fields, '', ''), (trgt_fields, 'trgt_', 'TARGET '), (trim_fields, 'trim_', 'TRIM ')]:
        for f in fieldgroup:
            out.write('%       {}{}: {}{}\n'.format(
                arg_prefix, f, doc_prefix, infos[f].docstring))
    out.write('''
    data = uint8([...
''')
    length = pack_fieldlists(Generator.MATLAB, out,
                             infos, main_fields, trgt_fields, trim_fields)

    out.write('''    ]);
% data length {0} bytes
end

% You might need to manually configure Simulink output:
%   Size: 1 {0}
%   Type: uint8
% The warning message "Wrap on overflow detected" can be ignored

function bytes = b(value)
    % reverse byte order to convert from little endian to big endian
    bytes = typecast(swapbytes(value), 'uint8');
end
'''.format(length))


def pack_fieldlists(gen: Generator, out: TextIOBase, infos: Dict[str, FieldInfo], main_fields, trgt_fields, trim_fields) -> int:
    length = 0

    field_count = len(main_fields) + \
        (1 if len(trgt_fields) > 0 else 0) + \
        (1 if len(trim_fields) > 0 else 0)
    length += pack_map(gen, out, field_count)

    for function_name in main_fields:
        length += pack_field(gen, out, infos[function_name], '')

    for fieldgroup, prefix in [(trgt_fields, 'trgt'), (trim_fields, 'trim')]:
        if len(fieldgroup) > 0:
            length += pack_str(gen, out, prefix)
            length += pack_map(gen, out, len(fieldgroup))
            for function_name in fieldgroup:
                length += pack_field(gen, out, infos[function_name], prefix)
    return length


def pack_field(gen: Generator, out: TextIOBase, info: FieldInfo, prefix: str) -> int:
    length = 0
    length += pack_str(gen, out, info.name)
    if issubclass(info.field_type, VectorModel):
        length += pack_vector(gen, out, info.name, info.field_type, prefix)
    elif info.field_type is int:
        length += pack_int(gen, out, info.name if len(prefix) ==
                           0 else '{}_{}'.format(prefix, info.name))
    else:
        raise NotImplementedError(
            'No code generation for class:', info.field_type)
    return length


def pack_vector(gen: Generator, out: TextIOBase, name: str, cls: Type[VectorModel], prefix: str) -> int:
    length = 0
    length += pack_array(gen, out, len(cls.__fields__))
    for inner in cls.__fields__:
        length += pack_float(gen, out, '{}{}_{}'.format(
            '' if len(prefix) == 0 else (prefix + '_'),
            name, inner), double=(name == 'ned'))  # special case for positional accuracy
    return length


def pack_map(gen: Generator, out: TextIOBase, count: int) -> int:
    if count > 15:
        raise NotImplementedError('only fixmap handled for now')
    if gen == Generator.MATLAB:
        out.write(
            '        0x8{:x}, ... % map length {}\n'.format(count, count))
    elif gen == Generator.MBDYN:
        val = 0x80 + count
        out.write(
            f'\tdrive, const, {val},\t# 0x{val:02X} map length {count}\n')
    elif gen == Generator.MBDYN_TYPE:
        out.write('\t\tuint8_t,\n')
    return 1


def pack_array(gen: Generator, out: TextIOBase, count: int) -> int:
    if count > 15:
        raise NotImplementedError('only fixarray handled for now')
    if gen == Generator.MATLAB:
        out.write(
            '        0x9{:x}, ... % array length {}\n'.format(count, count))
    elif gen == Generator.MBDYN:
        val = 0x90 + count
        out.write(
            f'\tdrive, const, {val},\t# 0x{val:02X} array length {count}\n')
    elif gen == Generator.MBDYN_TYPE:
        out.write('\t\tuint8_t,\n')

    return 1


def pack_str(gen: Generator, out: TextIOBase, data: str) -> int:
    if len(data) > 31:
        raise NotImplementedError('only fixstr handled for now')
    if gen == Generator.MATLAB:
        out.write("        0x{:x}, '{}', ... % string length {}\n".format(
            0b10100000 + len(data), data, len(data)))
    elif gen == Generator.MBDYN:
        val = 0b10100000 + len(data)
        out.write(
            f'\tdrive, const, {val},\t# 0x{val:02X} string length {len(data)}\n')
        for c in data:
            out.write(f"\tdrive, const, {ord(c)},\t# '{c}'\n")
    elif gen == Generator.MBDYN_TYPE:
        for _ in range(len(data) + 1):
            out.write('\t\tuint8_t,\n')
    return 1 + len(data)


def pack_float(gen: Generator, out: TextIOBase, name: str, double=False) -> int:
    if gen == Generator.MATLAB:
        out.write('        0xc{}, b({}({})), ... % {}\n'.format(
            'b' if double else 'a',
            'double' if double else 'single',
            name,
            'double' if double else 'float',
        ))
    elif gen == Generator.MBDYN:
        val = 0xCB if double else 0xCA
        out.write('\tdrive, const, {},\t# 0x{:02X} {}\n'.format(
            val, val, 'double' if double else 'float'
        ))
        out.write(f'\tdrive, reference, {MBD_PREFIX}{name.upper()},\n')
    elif gen == Generator.MBDYN_TYPE:
        out.write('\t\tuint8_t,\n')
        out.write(f'\t\t{"double" if double else "float"},\n')
    return 9 if double else 5


def pack_int(gen: Generator, out: TextIOBase, name: str) -> int:
    if gen == Generator.MATLAB:
        out.write(
            '        0xce, b(uint32({})), ... % 32-bit unsigned integer\n'.format(name))
    elif gen == Generator.MBDYN:
        val = 0xCE
        out.write(f'\tdrive, const, {val},\t# 0x{val:02X} uint32_t\n')
        out.write(f'\tdrive, reference, {MBD_PREFIX}{name.upper()},\n')
    elif gen == Generator.MBDYN_TYPE:
        out.write('\t\tuint8_t,\n')
        out.write('\t\tuint32_t,\n')
    return 5


if __name__ == '__main__':
    main()
