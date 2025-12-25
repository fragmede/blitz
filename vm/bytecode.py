"""Binary bytecode serialization for the Blitz VM.

File format (.blitzc):
    Header (16 bytes):
        - Magic: "BLTZ" (4 bytes)
        - Version: u16 (2 bytes)
        - Flags: u16 (2 bytes)
        - Num functions: u32 (4 bytes)
        - Num globals: u32 (4 bytes)

    Constants pool:
        - Num constants: u32
        - For each constant:
            - Type tag: u8 (0=float, 1=string)
            - If float: f64 (8 bytes)
            - If string: length u16, then UTF-8 bytes

    Globals:
        - For each global:
            - Name length: u16
            - Name: UTF-8 bytes
            - Constant pool index: u32

    Functions:
        - For each function:
            - Name length: u16
            - Name: UTF-8 bytes
            - Arity: u8
            - Locals count: u16
            - Num instructions: u32
            - Instructions (each 4 bytes: opcode u8, operand u24)
            - Num constants: u32
            - Constants (same format as above)

    Main chunk:
        - Num instructions: u32
        - Instructions
        - Num constants: u32
        - Constants
"""

import struct
from typing import BinaryIO
from .opcodes import OpCode, Instruction, Chunk, Function, CompiledProgram

MAGIC = b'BLTZ'
VERSION = 1


def write_bytecode(program: CompiledProgram, f: BinaryIO) -> int:
    """Write compiled program to binary file. Returns bytes written."""
    bytes_written = 0

    # Header
    f.write(MAGIC)
    f.write(struct.pack('<HH', VERSION, 0))  # version, flags
    f.write(struct.pack('<II', len(program.functions), len(program.globals)))
    bytes_written += 16

    # Helper to write a constant
    def write_constant(value):
        nonlocal bytes_written
        if isinstance(value, (int, float)):
            f.write(struct.pack('<B', 0))  # float type
            f.write(struct.pack('<d', float(value)))
            bytes_written += 9
        elif isinstance(value, str):
            encoded = value.encode('utf-8')
            f.write(struct.pack('<B', 1))  # string type
            f.write(struct.pack('<H', len(encoded)))
            f.write(encoded)
            bytes_written += 3 + len(encoded)
        else:
            # Treat as float
            f.write(struct.pack('<B', 0))
            f.write(struct.pack('<d', 0.0))
            bytes_written += 9

    # Helper to write a chunk
    def write_chunk(chunk: Chunk):
        nonlocal bytes_written
        # Instructions
        f.write(struct.pack('<I', len(chunk.code)))
        bytes_written += 4
        for instr in chunk.code:
            # Pack opcode (1 byte) + operand (3 bytes) = 4 bytes
            packed = (instr.opcode & 0xFF) | ((instr.operand & 0xFFFFFF) << 8)
            f.write(struct.pack('<I', packed))
            bytes_written += 4

        # Constants
        f.write(struct.pack('<I', len(chunk.constants)))
        bytes_written += 4
        for const in chunk.constants:
            write_constant(const)

    # Globals
    for name, idx in program.globals.items():
        encoded = name.encode('utf-8')
        f.write(struct.pack('<H', len(encoded)))
        f.write(encoded)
        f.write(struct.pack('<I', idx))
        bytes_written += 6 + len(encoded)

    # Functions
    for name, func in program.functions.items():
        encoded = name.encode('utf-8')
        f.write(struct.pack('<H', len(encoded)))
        f.write(encoded)
        f.write(struct.pack('<BH', func.arity, func.locals_count))
        bytes_written += 5 + len(encoded)
        write_chunk(func.chunk)

    # Main chunk
    write_chunk(program.main_chunk)

    return bytes_written


def read_bytecode(f: BinaryIO) -> CompiledProgram:
    """Read compiled program from binary file."""
    # Header
    magic = f.read(4)
    if magic != MAGIC:
        raise ValueError(f"Invalid bytecode file (expected {MAGIC!r}, got {magic!r})")

    version, flags = struct.unpack('<HH', f.read(4))
    if version > VERSION:
        raise ValueError(f"Bytecode version {version} not supported (max {VERSION})")

    num_functions, num_globals = struct.unpack('<II', f.read(8))

    # Helper to read a constant
    def read_constant():
        type_tag = struct.unpack('<B', f.read(1))[0]
        if type_tag == 0:  # float
            return struct.unpack('<d', f.read(8))[0]
        elif type_tag == 1:  # string
            length = struct.unpack('<H', f.read(2))[0]
            return f.read(length).decode('utf-8')
        else:
            raise ValueError(f"Unknown constant type {type_tag}")

    # Helper to read a chunk
    def read_chunk() -> Chunk:
        chunk = Chunk()

        # Instructions
        num_instructions = struct.unpack('<I', f.read(4))[0]
        for _ in range(num_instructions):
            packed = struct.unpack('<I', f.read(4))[0]
            opcode = OpCode(packed & 0xFF)
            operand = (packed >> 8) & 0xFFFFFF
            chunk.code.append(Instruction(opcode, operand))

        # Constants
        num_constants = struct.unpack('<I', f.read(4))[0]
        for _ in range(num_constants):
            chunk.constants.append(read_constant())

        return chunk

    program = CompiledProgram()

    # Globals
    for _ in range(num_globals):
        name_len = struct.unpack('<H', f.read(2))[0]
        name = f.read(name_len).decode('utf-8')
        idx = struct.unpack('<I', f.read(4))[0]
        program.globals[name] = idx

    # Functions
    for _ in range(num_functions):
        name_len = struct.unpack('<H', f.read(2))[0]
        name = f.read(name_len).decode('utf-8')
        arity, locals_count = struct.unpack('<BH', f.read(3))
        chunk = read_chunk()

        func = Function(name=name, arity=arity, chunk=chunk, locals_count=locals_count)
        program.functions[name] = func

    # Main chunk
    program.main_chunk = read_chunk()

    return program


def save_bytecode(program: CompiledProgram, path: str) -> int:
    """Save compiled program to file. Returns bytes written."""
    with open(path, 'wb') as f:
        return write_bytecode(program, f)


def load_bytecode(path: str) -> CompiledProgram:
    """Load compiled program from file."""
    with open(path, 'rb') as f:
        return read_bytecode(f)
