"""Bytecode definitions for the Blitz VM."""

from enum import IntEnum, auto
from dataclasses import dataclass, field
from typing import List, Any, Dict


class OpCode(IntEnum):
    """Bytecode operation codes."""

    # Stack manipulation
    CONST = 0        # Push constant: CONST index
    POP = auto()     # Pop and discard top of stack
    DUP = auto()     # Duplicate top of stack

    # Variables
    GET_LOCAL = auto()   # Push local variable: GET_LOCAL slot
    SET_LOCAL = auto()   # Pop and store to local: SET_LOCAL slot
    GET_GLOBAL = auto()  # Push global variable: GET_GLOBAL name_index
    SET_GLOBAL = auto()  # Pop and store to global: SET_GLOBAL name_index

    # Arithmetic
    ADD = auto()     # Pop two, push sum
    SUB = auto()     # Pop two, push difference
    MUL = auto()     # Pop two, push product
    DIV = auto()     # Pop two, push quotient
    MOD = auto()     # Pop two, push remainder
    NEG = auto()     # Negate top of stack

    # Comparison
    EQ = auto()      # Pop two, push equality result
    NE = auto()      # Pop two, push inequality result
    LT = auto()      # Pop two, push less-than result
    GT = auto()      # Pop two, push greater-than result
    LE = auto()      # Pop two, push less-or-equal result
    GE = auto()      # Pop two, push greater-or-equal result

    # Logic
    NOT = auto()     # Logical not of top of stack
    AND = auto()     # Short-circuit and
    OR = auto()      # Short-circuit or

    # Control flow
    JMP = auto()     # Unconditional jump: JMP offset
    JZ = auto()      # Jump if zero/false: JZ offset
    JNZ = auto()     # Jump if not zero/true: JNZ offset
    LOOP = auto()    # Jump backwards: LOOP offset

    # Functions
    CALL = auto()    # Call function: CALL arg_count
    RET = auto()     # Return from function
    INTRINSIC = auto()  # Call intrinsic: INTRINSIC id arg_count

    # Special
    HALT = auto()    # Stop execution


@dataclass
class Instruction:
    """A single bytecode instruction."""
    opcode: OpCode
    operand: int = 0  # Optional operand

    def __repr__(self):
        if self.opcode in (OpCode.CONST, OpCode.GET_LOCAL, OpCode.SET_LOCAL,
                           OpCode.GET_GLOBAL, OpCode.SET_GLOBAL, OpCode.JMP,
                           OpCode.JZ, OpCode.JNZ, OpCode.LOOP, OpCode.CALL,
                           OpCode.INTRINSIC):
            return f"{self.opcode.name} {self.operand}"
        return self.opcode.name


@dataclass
class Chunk:
    """A chunk of bytecode with its constant pool."""
    code: List[Instruction] = field(default_factory=list)
    constants: List[Any] = field(default_factory=list)
    lines: List[int] = field(default_factory=list)  # Source line for each instruction

    def add_instruction(self, opcode: OpCode, operand: int = 0, line: int = 0) -> int:
        """Add an instruction and return its index."""
        self.code.append(Instruction(opcode, operand))
        self.lines.append(line)
        return len(self.code) - 1

    def add_constant(self, value: Any) -> int:
        """Add a constant and return its index."""
        # Check if constant already exists
        for i, c in enumerate(self.constants):
            if c == value and type(c) == type(value):
                return i
        self.constants.append(value)
        return len(self.constants) - 1

    def patch_jump(self, index: int, target: int):
        """Patch a jump instruction to point to target."""
        self.code[index].operand = target

    def disassemble(self, name: str = "chunk") -> str:
        """Return a human-readable disassembly."""
        lines = [f"=== {name} ==="]
        for i, instr in enumerate(self.code):
            line_info = f"[{self.lines[i]:4d}]" if self.lines else ""
            if instr.opcode == OpCode.CONST:
                const_val = self.constants[instr.operand]
                lines.append(f"{i:04d} {line_info} {instr.opcode.name:15s} {instr.operand} ({const_val})")
            elif instr.opcode in (OpCode.GET_GLOBAL, OpCode.SET_GLOBAL):
                name_val = self.constants[instr.operand]
                lines.append(f"{i:04d} {line_info} {instr.opcode.name:15s} {instr.operand} ({name_val})")
            elif instr.operand != 0 or instr.opcode in (OpCode.GET_LOCAL, OpCode.SET_LOCAL,
                                                         OpCode.JMP, OpCode.JZ, OpCode.JNZ,
                                                         OpCode.LOOP, OpCode.CALL, OpCode.INTRINSIC):
                lines.append(f"{i:04d} {line_info} {instr.opcode.name:15s} {instr.operand}")
            else:
                lines.append(f"{i:04d} {line_info} {instr.opcode.name}")
        return "\n".join(lines)


@dataclass
class Function:
    """A compiled function."""
    name: str
    arity: int  # Number of parameters
    chunk: Chunk = field(default_factory=Chunk)
    locals_count: int = 0  # Number of local variables (including params)


@dataclass
class CompiledProgram:
    """A fully compiled program."""
    functions: Dict[str, Function] = field(default_factory=dict)
    globals: Dict[str, int] = field(default_factory=dict)  # Global name -> constant pool index
    main_chunk: Chunk = field(default_factory=Chunk)  # Top-level code


# Intrinsic function IDs
class Intrinsic(IntEnum):
    # Input
    KEY_LEFT = 0
    KEY_RIGHT = auto()
    KEY_UP = auto()
    KEY_DOWN = auto()
    KEY_FIRE = auto()

    # Math
    SIN = auto()
    COS = auto()
    SQRT = auto()
    ABS = auto()
    RANDOM = auto()
    FLOOR = auto()
    MIN = auto()
    MAX = auto()

    # Game
    SPAWN_BULLET = auto()
    SPAWN_ENEMY = auto()
    DESTROY = auto()
    GET_X = auto()
    GET_Y = auto()
    SET_X = auto()
    SET_Y = auto()
    GET_TYPE = auto()
    SET_GAME_MODE = auto()  # 0 = vertical (default), 1 = horizontal

    # System
    PRINT = auto()
    TIME = auto()


# Map intrinsic names to IDs and arities
INTRINSICS = {
    'key_left': (Intrinsic.KEY_LEFT, 0),
    'key_right': (Intrinsic.KEY_RIGHT, 0),
    'key_up': (Intrinsic.KEY_UP, 0),
    'key_down': (Intrinsic.KEY_DOWN, 0),
    'key_fire': (Intrinsic.KEY_FIRE, 0),
    'sin': (Intrinsic.SIN, 1),
    'cos': (Intrinsic.COS, 1),
    'sqrt': (Intrinsic.SQRT, 1),
    'abs': (Intrinsic.ABS, 1),
    'random': (Intrinsic.RANDOM, 0),
    'floor': (Intrinsic.FLOOR, 1),
    'min': (Intrinsic.MIN, 2),
    'max': (Intrinsic.MAX, 2),
    'spawn_bullet': (Intrinsic.SPAWN_BULLET, 2),
    'spawn_enemy': (Intrinsic.SPAWN_ENEMY, 3),
    'destroy': (Intrinsic.DESTROY, 1),
    'get_x': (Intrinsic.GET_X, 1),
    'get_y': (Intrinsic.GET_Y, 1),
    'set_x': (Intrinsic.SET_X, 2),
    'set_y': (Intrinsic.SET_Y, 2),
    'get_type': (Intrinsic.GET_TYPE, 1),
    'set_game_mode': (Intrinsic.SET_GAME_MODE, 1),
    'print': (Intrinsic.PRINT, 1),
    'time': (Intrinsic.TIME, 0),
}
