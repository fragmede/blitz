"""Stack-based bytecode interpreter for Blitz."""

import math
import random
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from .opcodes import OpCode, Chunk, Function, CompiledProgram, Intrinsic


class VMError(Exception):
    """Runtime error in the VM."""
    pass


@dataclass
class CallFrame:
    """A call frame on the call stack."""
    function: Function
    ip: int  # Instruction pointer
    stack_base: int  # Base of this frame's stack window


class VM:
    """Blitz virtual machine."""

    def __init__(self, program: CompiledProgram):
        self.program = program
        self.stack: List[Any] = []
        self.globals: Dict[str, Any] = {}
        self.frames: List[CallFrame] = []
        self.intrinsic_handlers: Dict[Intrinsic, Callable] = {}

        # Game state (set by runtime)
        self.game_state = None

        # Register default intrinsic handlers
        self._register_default_intrinsics()

    def _register_default_intrinsics(self):
        """Register default intrinsic implementations."""
        # Math
        self.intrinsic_handlers[Intrinsic.SIN] = lambda args: math.sin(args[0])
        self.intrinsic_handlers[Intrinsic.COS] = lambda args: math.cos(args[0])
        self.intrinsic_handlers[Intrinsic.SQRT] = lambda args: math.sqrt(max(0, args[0]))
        self.intrinsic_handlers[Intrinsic.ABS] = lambda args: abs(args[0])
        self.intrinsic_handlers[Intrinsic.RANDOM] = lambda args: random.random()
        self.intrinsic_handlers[Intrinsic.FLOOR] = lambda args: math.floor(args[0])
        self.intrinsic_handlers[Intrinsic.MIN] = lambda args: min(args[0], args[1])
        self.intrinsic_handlers[Intrinsic.MAX] = lambda args: max(args[0], args[1])

        # System
        self.intrinsic_handlers[Intrinsic.PRINT] = lambda args: print(args[0]) or 0.0
        self.intrinsic_handlers[Intrinsic.TIME] = lambda args: 0.0  # Overridden by runtime

    def register_intrinsic(self, intrinsic: Intrinsic, handler: Callable):
        """Register a custom intrinsic handler."""
        self.intrinsic_handlers[intrinsic] = handler

    def run_main(self):
        """Execute the main chunk."""
        self._run_chunk(self.program.main_chunk)

    def call_function(self, name: str, *args) -> Any:
        """Call a named function with arguments."""
        if name not in self.program.functions:
            raise VMError(f"Function '{name}' not found")

        func = self.program.functions[name]
        if len(args) != func.arity:
            raise VMError(f"Function '{name}' expects {func.arity} args, got {len(args)}")

        # Push arguments
        for arg in args:
            self.stack.append(arg)

        # Create call frame
        frame = CallFrame(func, 0, len(self.stack) - func.arity)
        self.frames.append(frame)

        # Run function
        result = self._run()

        return result

    def _run_chunk(self, chunk: Chunk):
        """Execute a chunk of bytecode."""
        ip = 0
        while ip < len(chunk.code):
            instr = chunk.code[ip]
            ip += 1

            if instr.opcode == OpCode.HALT:
                break

            elif instr.opcode == OpCode.CONST:
                self.stack.append(chunk.constants[instr.operand])

            elif instr.opcode == OpCode.POP:
                if self.stack:
                    self.stack.pop()

            elif instr.opcode == OpCode.DUP:
                self.stack.append(self.stack[-1])

            elif instr.opcode == OpCode.GET_GLOBAL:
                name = chunk.constants[instr.operand]
                if name in self.globals:
                    self.stack.append(self.globals[name])
                else:
                    self.stack.append(0.0)  # Default to 0

            elif instr.opcode == OpCode.SET_GLOBAL:
                name = chunk.constants[instr.operand]
                self.globals[name] = self.stack.pop()

            elif instr.opcode == OpCode.ADD:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a + b)

            elif instr.opcode == OpCode.SUB:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a - b)

            elif instr.opcode == OpCode.MUL:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a * b)

            elif instr.opcode == OpCode.DIV:
                b, a = self.stack.pop(), self.stack.pop()
                if b == 0:
                    self.stack.append(0.0)
                else:
                    self.stack.append(a / b)

            elif instr.opcode == OpCode.MOD:
                b, a = self.stack.pop(), self.stack.pop()
                if b == 0:
                    self.stack.append(0.0)
                else:
                    self.stack.append(a % b)

            elif instr.opcode == OpCode.NEG:
                self.stack[-1] = -self.stack[-1]

            elif instr.opcode == OpCode.EQ:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1.0 if a == b else 0.0)

            elif instr.opcode == OpCode.NE:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1.0 if a != b else 0.0)

            elif instr.opcode == OpCode.LT:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1.0 if a < b else 0.0)

            elif instr.opcode == OpCode.GT:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1.0 if a > b else 0.0)

            elif instr.opcode == OpCode.LE:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1.0 if a <= b else 0.0)

            elif instr.opcode == OpCode.GE:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1.0 if a >= b else 0.0)

            elif instr.opcode == OpCode.NOT:
                val = self.stack.pop()
                self.stack.append(1.0 if not val else 0.0)

            elif instr.opcode == OpCode.JMP:
                ip = instr.operand

            elif instr.opcode == OpCode.JZ:
                if not self.stack[-1]:
                    ip = instr.operand

            elif instr.opcode == OpCode.JNZ:
                if self.stack[-1]:
                    ip = instr.operand

            elif instr.opcode == OpCode.LOOP:
                ip = instr.operand

            elif instr.opcode == OpCode.CALL:
                arg_count = instr.operand
                callee = self.stack.pop()

                # callee should be a function name
                if isinstance(callee, str) and callee in self.program.functions:
                    func = self.program.functions[callee]
                    frame = CallFrame(func, 0, len(self.stack) - arg_count)
                    self.frames.append(frame)
                    result = self._run()
                    self.stack.append(result)
                else:
                    raise VMError(f"Cannot call: {callee}")

            elif instr.opcode == OpCode.INTRINSIC:
                intrinsic_id = Intrinsic(instr.operand)
                result = self._call_intrinsic(intrinsic_id)
                self.stack.append(result)

    def _run(self) -> Any:
        """Run the current call frame until it returns."""
        frame = self.frames[-1]
        chunk = frame.function.chunk

        while frame.ip < len(chunk.code):
            instr = chunk.code[frame.ip]
            frame.ip += 1

            if instr.opcode == OpCode.CONST:
                self.stack.append(chunk.constants[instr.operand])

            elif instr.opcode == OpCode.POP:
                if self.stack:
                    self.stack.pop()

            elif instr.opcode == OpCode.DUP:
                self.stack.append(self.stack[-1])

            elif instr.opcode == OpCode.GET_LOCAL:
                slot = frame.stack_base + instr.operand
                self.stack.append(self.stack[slot])

            elif instr.opcode == OpCode.SET_LOCAL:
                slot = frame.stack_base + instr.operand
                self.stack[slot] = self.stack.pop()

            elif instr.opcode == OpCode.GET_GLOBAL:
                name = chunk.constants[instr.operand]
                if name in self.globals:
                    self.stack.append(self.globals[name])
                else:
                    self.stack.append(0.0)

            elif instr.opcode == OpCode.SET_GLOBAL:
                name = chunk.constants[instr.operand]
                self.globals[name] = self.stack.pop()

            elif instr.opcode == OpCode.ADD:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a + b)

            elif instr.opcode == OpCode.SUB:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a - b)

            elif instr.opcode == OpCode.MUL:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a * b)

            elif instr.opcode == OpCode.DIV:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a / b if b != 0 else 0.0)

            elif instr.opcode == OpCode.MOD:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a % b if b != 0 else 0.0)

            elif instr.opcode == OpCode.NEG:
                self.stack[-1] = -self.stack[-1]

            elif instr.opcode == OpCode.EQ:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1.0 if a == b else 0.0)

            elif instr.opcode == OpCode.NE:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1.0 if a != b else 0.0)

            elif instr.opcode == OpCode.LT:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1.0 if a < b else 0.0)

            elif instr.opcode == OpCode.GT:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1.0 if a > b else 0.0)

            elif instr.opcode == OpCode.LE:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1.0 if a <= b else 0.0)

            elif instr.opcode == OpCode.GE:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1.0 if a >= b else 0.0)

            elif instr.opcode == OpCode.NOT:
                val = self.stack.pop()
                self.stack.append(1.0 if not val else 0.0)

            elif instr.opcode == OpCode.JMP:
                frame.ip = instr.operand

            elif instr.opcode == OpCode.JZ:
                if not self.stack[-1]:
                    frame.ip = instr.operand

            elif instr.opcode == OpCode.JNZ:
                if self.stack[-1]:
                    frame.ip = instr.operand

            elif instr.opcode == OpCode.LOOP:
                frame.ip = instr.operand

            elif instr.opcode == OpCode.CALL:
                arg_count = instr.operand
                callee = self.stack.pop()

                if isinstance(callee, str) and callee in self.program.functions:
                    func = self.program.functions[callee]
                    new_frame = CallFrame(func, 0, len(self.stack) - arg_count)
                    self.frames.append(new_frame)
                    result = self._run()
                    self.stack.append(result)
                else:
                    raise VMError(f"Cannot call: {callee}")

            elif instr.opcode == OpCode.RET:
                result = self.stack.pop()
                # Clean up local variables
                while len(self.stack) > frame.stack_base:
                    self.stack.pop()
                self.frames.pop()
                return result

            elif instr.opcode == OpCode.INTRINSIC:
                intrinsic_id = Intrinsic(instr.operand)
                result = self._call_intrinsic(intrinsic_id)
                self.stack.append(result)

        # Implicit return
        self.frames.pop()
        return 0.0

    def _call_intrinsic(self, intrinsic_id: Intrinsic) -> Any:
        """Call an intrinsic function."""
        from .opcodes import INTRINSICS

        # Find arity
        arity = 0
        for name, (id_, ar) in INTRINSICS.items():
            if id_ == intrinsic_id:
                arity = ar
                break

        # Pop arguments
        args = []
        for _ in range(arity):
            args.insert(0, self.stack.pop())

        # Call handler
        if intrinsic_id in self.intrinsic_handlers:
            return self.intrinsic_handlers[intrinsic_id](args)
        else:
            raise VMError(f"Unhandled intrinsic: {intrinsic_id}")
