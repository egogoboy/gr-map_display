function data = pack_lidia( ...
    ned_north, ...
    ned_east, ...
    ned_down, ...
    att_roll, ...
    att_pitch, ...
    att_yaw, ...
    v_body_x, ...
    v_body_y, ...
    v_body_z, ...
    v_ned_north, ...
    v_ned_east, ...
    v_ned_down, ...
    ctrl_stick_right, ...
    ctrl_stick_pull, ...
    ctrl_throttle, ...
    ctrl_pedals_right, ...
    ctrl_collective_up, ...
    t_boot, ...
    trgt_ctrl_stick_right, ...
    trgt_ctrl_stick_pull, ...
    trgt_ctrl_throttle, ...
    trgt_ctrl_pedals_right, ...
    trgt_ctrl_collective_up) % 23 arguments
%PACK_LIDIA Pack aircraft data into binary format
%   The output is array of bytes in MsgPack format, as expected by
%   'smol' source of lidia package
%
%   This is generated using pack_maker.py to create code suitable for
%   use in Simulink - known size of I/O (see below), no map or struct usage
%
%   Arguments:
%       ned: Position in local horizon coordinate system, in meters
%       att: Aircraft attitude, in radians
%       v_body: Velocity in body frame, in meters per second
%       v_ned: Velocity in local horizon coordinate system, in meters per second
%       ctrl: Control inceptors position, normalized by max deflection
%       t_boot: Time from the start of simulation, in milliseconds
%       trgt_ctrl: TARGET Control inceptors position, normalized by max deflection

    data = uint8([...
        0x87, ... % map length 7
        0xa3, 'ned', ... % string length 3
        0x93, ... % array length 3
        0xcb, b(double(ned_north)), ... % double
        0xcb, b(double(ned_east)), ... % double
        0xcb, b(double(ned_down)), ... % double
        0xa3, 'att', ... % string length 3
        0x93, ... % array length 3
        0xca, b(single(att_roll)), ... % float
        0xca, b(single(att_pitch)), ... % float
        0xca, b(single(att_yaw)), ... % float
        0xa6, 'v_body', ... % string length 6
        0x93, ... % array length 3
        0xca, b(single(v_body_x)), ... % float
        0xca, b(single(v_body_y)), ... % float
        0xca, b(single(v_body_z)), ... % float
        0xa5, 'v_ned', ... % string length 5
        0x93, ... % array length 3
        0xca, b(single(v_ned_north)), ... % float
        0xca, b(single(v_ned_east)), ... % float
        0xca, b(single(v_ned_down)), ... % float
        0xa4, 'ctrl', ... % string length 4
        0x95, ... % array length 5
        0xca, b(single(ctrl_stick_right)), ... % float
        0xca, b(single(ctrl_stick_pull)), ... % float
        0xca, b(single(ctrl_throttle)), ... % float
        0xca, b(single(ctrl_pedals_right)), ... % float
        0xca, b(single(ctrl_collective_up)), ... % float
        0xa6, 't_boot', ... % string length 6
        0xce, b(uint32(t_boot)), ... % 32-bit unsigned integer
        0xa4, 'trgt', ... % string length 4
        0x81, ... % map length 1
        0xa4, 'ctrl', ... % string length 4
        0x95, ... % array length 5
        0xca, b(single(trgt_ctrl_stick_right)), ... % float
        0xca, b(single(trgt_ctrl_stick_pull)), ... % float
        0xca, b(single(trgt_ctrl_throttle)), ... % float
        0xca, b(single(trgt_ctrl_pedals_right)), ... % float
        0xca, b(single(trgt_ctrl_collective_up)), ... % float
    ]);
% data length 178 bytes
end

% You might need to manually configure Simulink output:
%   Size: 1 178
%   Type: uint8
% The warning message "Wrap on overflow detected" can be ignored

function bytes = b(value)
    % reverse byte order to convert from little endian to big endian
    bytes = typecast(swapbytes(value), 'uint8');
end
