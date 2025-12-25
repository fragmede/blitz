"""Code generator: compiles AST to bytecode."""

import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path for imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from blitz.ast import (
    ASTVisitor, Program, Stmt, Expr, FnDecl, VarDecl, Block, IfStmt,
    WhileStmt, ReturnStmt, ExprStmt, NumberLiteral, StringLiteral,
    BoolLiteral, Identifier, BinaryExpr, UnaryExpr, CallExpr, MemberExpr,
    AssignExpr, GroupExpr
)
from vm.opcodes import OpCode, Chunk, Function, CompiledProgram, INTRINSICS


class CompileError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class Local:
    """A local variable in scope."""
    def __init__(self, name: str, depth: int):
        self.name = name
        self.depth = depth


class CodeGenerator(ASTVisitor):
    """Compiles AST to bytecode."""

    def __init__(self):
        self.program = CompiledProgram()
        self.current_function: Optional[Function] = None
        self.current_chunk: Chunk = self.program.main_chunk
        self.locals: List[Local] = []
        self.scope_depth = 0

    def compile(self, program: Program) -> CompiledProgram:
        """Compile a program AST to bytecode."""
        self.visit(program)
        self.emit(OpCode.HALT)
        return self.program

    def visit_Program(self, node: Program):
        for decl in node.declarations:
            self.visit(decl)

    def visit_FnDecl(self, node: FnDecl):
        # Create a new function
        function = Function(node.name, len(node.params))
        self.program.functions[node.name] = function

        # Save current state
        enclosing_function = self.current_function
        enclosing_chunk = self.current_chunk
        enclosing_locals = self.locals

        # Switch to function's chunk
        self.current_function = function
        self.current_chunk = function.chunk
        self.locals = []
        self.scope_depth = 0

        # Begin function scope
        self.begin_scope()

        # Declare parameters as locals
        for param in node.params:
            self.declare_local(param)

        # Compile function body
        for stmt in node.body.statements:
            self.visit(stmt)

        # Emit implicit return if needed
        if not self.current_chunk.code or self.current_chunk.code[-1].opcode != OpCode.RET:
            self.emit_constant(0.0)  # Return 0 by default
            self.emit(OpCode.RET)

        function.locals_count = len(self.locals)

        # Restore state
        self.current_function = enclosing_function
        self.current_chunk = enclosing_chunk
        self.locals = enclosing_locals
        self.scope_depth = 0

    def visit_VarDecl(self, node: VarDecl):
        if self.scope_depth > 0:
            # Local variable
            self.declare_local(node.name)
            if node.initializer:
                self.visit(node.initializer)
            else:
                self.emit_constant(0.0)  # Default to 0
            # Value is already on stack at the right slot
        else:
            # Global variable
            name_index = self.current_chunk.add_constant(node.name)
            self.program.globals[node.name] = name_index
            if node.initializer:
                self.visit(node.initializer)
            else:
                self.emit_constant(0.0)
            self.emit(OpCode.SET_GLOBAL, name_index)

    def visit_Block(self, node: Block):
        self.begin_scope()
        for stmt in node.statements:
            self.visit(stmt)
        self.end_scope()

    def visit_IfStmt(self, node: IfStmt):
        # Compile condition
        self.visit(node.condition)

        # Jump over then branch if false
        then_jump = self.emit_jump(OpCode.JZ)

        # Pop condition value
        self.emit(OpCode.POP)

        # Compile then branch
        self.visit(node.then_branch)

        # Jump over else branch
        else_jump = self.emit_jump(OpCode.JMP)

        # Patch then jump to here
        self.patch_jump(then_jump)
        self.emit(OpCode.POP)  # Pop condition value

        # Compile else branch
        if node.else_branch:
            self.visit(node.else_branch)

        # Patch else jump to here
        self.patch_jump(else_jump)

    def visit_WhileStmt(self, node: WhileStmt):
        loop_start = len(self.current_chunk.code)

        # Compile condition
        self.visit(node.condition)

        # Jump out if false
        exit_jump = self.emit_jump(OpCode.JZ)
        self.emit(OpCode.POP)  # Pop condition

        # Compile body
        self.visit(node.body)

        # Jump back to condition
        self.emit_loop(loop_start)

        # Patch exit jump
        self.patch_jump(exit_jump)
        self.emit(OpCode.POP)  # Pop condition

    def visit_ReturnStmt(self, node: ReturnStmt):
        if node.value:
            self.visit(node.value)
        else:
            self.emit_constant(0.0)  # Return 0 if no value
        self.emit(OpCode.RET)

    def visit_ExprStmt(self, node: ExprStmt):
        self.visit(node.expression)
        self.emit(OpCode.POP)  # Discard result

    # ============ Expressions ============

    def visit_NumberLiteral(self, node: NumberLiteral):
        self.emit_constant(node.value)

    def visit_StringLiteral(self, node: StringLiteral):
        self.emit_constant(node.value)

    def visit_BoolLiteral(self, node: BoolLiteral):
        self.emit_constant(1.0 if node.value else 0.0)

    def visit_Identifier(self, node: Identifier):
        # Check for local variable first
        slot = self.resolve_local(node.name)
        if slot != -1:
            self.emit(OpCode.GET_LOCAL, slot)
        else:
            # Global variable
            name_index = self.current_chunk.add_constant(node.name)
            self.emit(OpCode.GET_GLOBAL, name_index)

    def visit_AssignExpr(self, node: AssignExpr):
        self.visit(node.value)
        self.emit(OpCode.DUP)  # Keep value on stack for expression result

        slot = self.resolve_local(node.name)
        if slot != -1:
            self.emit(OpCode.SET_LOCAL, slot)
        else:
            name_index = self.current_chunk.add_constant(node.name)
            self.emit(OpCode.SET_GLOBAL, name_index)

    def visit_BinaryExpr(self, node: BinaryExpr):
        # Handle short-circuit operators specially
        if node.operator == "and":
            self.visit(node.left)
            end_jump = self.emit_jump(OpCode.JZ)
            self.emit(OpCode.POP)
            self.visit(node.right)
            self.patch_jump(end_jump)
            return

        if node.operator == "or":
            self.visit(node.left)
            else_jump = self.emit_jump(OpCode.JZ)
            end_jump = self.emit_jump(OpCode.JMP)
            self.patch_jump(else_jump)
            self.emit(OpCode.POP)
            self.visit(node.right)
            self.patch_jump(end_jump)
            return

        # Regular binary operators
        self.visit(node.left)
        self.visit(node.right)

        op_map = {
            '+': OpCode.ADD,
            '-': OpCode.SUB,
            '*': OpCode.MUL,
            '/': OpCode.DIV,
            '%': OpCode.MOD,
            '==': OpCode.EQ,
            '!=': OpCode.NE,
            '<': OpCode.LT,
            '>': OpCode.GT,
            '<=': OpCode.LE,
            '>=': OpCode.GE,
        }

        if node.operator in op_map:
            self.emit(op_map[node.operator])
        else:
            raise CompileError(f"Unknown binary operator: {node.operator}")

    def visit_UnaryExpr(self, node: UnaryExpr):
        self.visit(node.operand)

        if node.operator == '-':
            self.emit(OpCode.NEG)
        elif node.operator == 'not':
            self.emit(OpCode.NOT)
        else:
            raise CompileError(f"Unknown unary operator: {node.operator}")

    def visit_CallExpr(self, node: CallExpr):
        # Check if it's an intrinsic
        if isinstance(node.callee, Identifier):
            name = node.callee.name
            if name in INTRINSICS:
                intrinsic_id, expected_arity = INTRINSICS[name]
                if len(node.arguments) != expected_arity:
                    raise CompileError(
                        f"Intrinsic '{name}' expects {expected_arity} arguments, got {len(node.arguments)}"
                    )
                # Compile arguments
                for arg in node.arguments:
                    self.visit(arg)
                # Emit intrinsic call
                self.emit(OpCode.INTRINSIC, intrinsic_id)
                return

        # Regular function call
        # Compile arguments first
        for arg in node.arguments:
            self.visit(arg)

        # For user-defined function calls, push the function name as a string
        # The VM will look up the function by name
        if isinstance(node.callee, Identifier):
            # Push function name as a string constant
            self.emit_constant(node.callee.name)
        else:
            # For dynamic calls (e.g., obj.method()), compile the callee
            self.visit(node.callee)

        # Emit call with argument count
        self.emit(OpCode.CALL, len(node.arguments))

    def visit_MemberExpr(self, node: MemberExpr):
        # For now, just compile the object
        # Member access would need more complex handling
        self.visit(node.object)
        raise CompileError("Member access not yet supported")

    def visit_GroupExpr(self, node: GroupExpr):
        self.visit(node.expression)

    # ============ Helpers ============

    def emit(self, opcode: OpCode, operand: int = 0) -> int:
        return self.current_chunk.add_instruction(opcode, operand)

    def emit_constant(self, value) -> int:
        index = self.current_chunk.add_constant(value)
        return self.emit(OpCode.CONST, index)

    def emit_jump(self, opcode: OpCode) -> int:
        """Emit a jump instruction with placeholder offset."""
        return self.emit(opcode, 0xFFFF)  # Placeholder

    def patch_jump(self, index: int):
        """Patch a jump to point to current instruction."""
        target = len(self.current_chunk.code)
        self.current_chunk.patch_jump(index, target)

    def emit_loop(self, loop_start: int):
        """Emit a backwards jump to loop_start."""
        self.emit(OpCode.LOOP, loop_start)

    def begin_scope(self):
        self.scope_depth += 1

    def end_scope(self):
        self.scope_depth -= 1
        # Pop locals that are going out of scope
        while self.locals and self.locals[-1].depth > self.scope_depth:
            self.emit(OpCode.POP)
            self.locals.pop()

    def declare_local(self, name: str):
        # Check for duplicate in current scope
        for local in reversed(self.locals):
            if local.depth < self.scope_depth:
                break
            if local.name == name:
                raise CompileError(f"Variable '{name}' already declared in this scope")

        self.locals.append(Local(name, self.scope_depth))

    def resolve_local(self, name: str) -> int:
        """Find local variable slot, or -1 if not found."""
        for i in range(len(self.locals) - 1, -1, -1):
            if self.locals[i].name == name:
                return i
        return -1


def generate_code(program: Program) -> CompiledProgram:
    """Convenience function to compile an AST."""
    generator = CodeGenerator()
    return generator.compile(program)
