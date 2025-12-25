"""AST node definitions for the Blitz language."""

from dataclasses import dataclass
from typing import List, Optional, Any
from abc import ABC, abstractmethod


class ASTNode(ABC):
    """Base class for all AST nodes."""
    pass


class Expr(ASTNode):
    """Base class for expression nodes."""
    pass


class Stmt(ASTNode):
    """Base class for statement nodes."""
    pass


# ============ Expressions ============

@dataclass
class NumberLiteral(Expr):
    value: float


@dataclass
class StringLiteral(Expr):
    value: str


@dataclass
class BoolLiteral(Expr):
    value: bool


@dataclass
class Identifier(Expr):
    name: str


@dataclass
class BinaryExpr(Expr):
    left: Expr
    operator: str  # '+', '-', '*', '/', '%', '==', '!=', '<', '>', '<=', '>=', 'and', 'or'
    right: Expr


@dataclass
class UnaryExpr(Expr):
    operator: str  # '-', 'not'
    operand: Expr


@dataclass
class CallExpr(Expr):
    callee: Expr
    arguments: List[Expr]


@dataclass
class MemberExpr(Expr):
    object: Expr
    member: str


@dataclass
class AssignExpr(Expr):
    name: str
    value: Expr


@dataclass
class GroupExpr(Expr):
    expression: Expr


# ============ Statements ============

@dataclass
class ExprStmt(Stmt):
    expression: Expr


@dataclass
class VarDecl(Stmt):
    name: str
    initializer: Optional[Expr]


@dataclass
class Block(Stmt):
    statements: List[Stmt]


@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt]


@dataclass
class WhileStmt(Stmt):
    condition: Expr
    body: Stmt


@dataclass
class ReturnStmt(Stmt):
    value: Optional[Expr]


@dataclass
class FnDecl(Stmt):
    name: str
    params: List[str]
    body: Block


# ============ Program ============

@dataclass
class Program(ASTNode):
    declarations: List[Stmt]


# ============ Visitor Pattern ============

class ASTVisitor(ABC):
    """Visitor interface for AST traversal."""

    def visit(self, node: ASTNode) -> Any:
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ASTNode) -> Any:
        raise NotImplementedError(f"No visit method for {type(node).__name__}")


class ASTPrinter(ASTVisitor):
    """Pretty-print an AST for debugging."""

    def __init__(self):
        self.indent = 0

    def _line(self, text: str) -> str:
        return "  " * self.indent + text

    def visit_Program(self, node: Program) -> str:
        lines = ["Program:"]
        self.indent += 1
        for decl in node.declarations:
            lines.append(self.visit(decl))
        self.indent -= 1
        return "\n".join(lines)

    def visit_FnDecl(self, node: FnDecl) -> str:
        lines = [self._line(f"FnDecl: {node.name}({', '.join(node.params)})")]
        self.indent += 1
        lines.append(self.visit(node.body))
        self.indent -= 1
        return "\n".join(lines)

    def visit_VarDecl(self, node: VarDecl) -> str:
        if node.initializer:
            return self._line(f"VarDecl: {node.name} = {self.visit(node.initializer)}")
        return self._line(f"VarDecl: {node.name}")

    def visit_Block(self, node: Block) -> str:
        lines = [self._line("Block:")]
        self.indent += 1
        for stmt in node.statements:
            lines.append(self.visit(stmt))
        self.indent -= 1
        return "\n".join(lines)

    def visit_IfStmt(self, node: IfStmt) -> str:
        lines = [self._line(f"If: {self.visit(node.condition)}")]
        self.indent += 1
        lines.append(self._line("Then:"))
        self.indent += 1
        lines.append(self.visit(node.then_branch))
        self.indent -= 1
        if node.else_branch:
            lines.append(self._line("Else:"))
            self.indent += 1
            lines.append(self.visit(node.else_branch))
            self.indent -= 1
        self.indent -= 1
        return "\n".join(lines)

    def visit_WhileStmt(self, node: WhileStmt) -> str:
        lines = [self._line(f"While: {self.visit(node.condition)}")]
        self.indent += 1
        lines.append(self.visit(node.body))
        self.indent -= 1
        return "\n".join(lines)

    def visit_ReturnStmt(self, node: ReturnStmt) -> str:
        if node.value:
            return self._line(f"Return: {self.visit(node.value)}")
        return self._line("Return")

    def visit_ExprStmt(self, node: ExprStmt) -> str:
        return self._line(f"ExprStmt: {self.visit(node.expression)}")

    def visit_NumberLiteral(self, node: NumberLiteral) -> str:
        return f"{node.value}"

    def visit_StringLiteral(self, node: StringLiteral) -> str:
        return f'"{node.value}"'

    def visit_BoolLiteral(self, node: BoolLiteral) -> str:
        return "true" if node.value else "false"

    def visit_Identifier(self, node: Identifier) -> str:
        return node.name

    def visit_BinaryExpr(self, node: BinaryExpr) -> str:
        return f"({self.visit(node.left)} {node.operator} {self.visit(node.right)})"

    def visit_UnaryExpr(self, node: UnaryExpr) -> str:
        return f"({node.operator} {self.visit(node.operand)})"

    def visit_CallExpr(self, node: CallExpr) -> str:
        args = ", ".join(self.visit(arg) for arg in node.arguments)
        return f"{self.visit(node.callee)}({args})"

    def visit_MemberExpr(self, node: MemberExpr) -> str:
        return f"{self.visit(node.object)}.{node.member}"

    def visit_AssignExpr(self, node: AssignExpr) -> str:
        return f"({node.name} = {self.visit(node.value)})"

    def visit_GroupExpr(self, node: GroupExpr) -> str:
        return f"({self.visit(node.expression)})"
