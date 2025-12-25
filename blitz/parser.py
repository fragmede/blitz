"""Recursive descent parser for the Blitz language."""

from typing import List, Optional
from .lexer import Token, TokenType, Lexer
from .ast import (
    Program, Stmt, Expr, FnDecl, VarDecl, Block, IfStmt, WhileStmt,
    ReturnStmt, ExprStmt, NumberLiteral, StringLiteral, BoolLiteral,
    Identifier, BinaryExpr, UnaryExpr, CallExpr, MemberExpr, AssignExpr, GroupExpr
)


class ParseError(Exception):
    def __init__(self, message: str, token: Token):
        self.message = message
        self.token = token
        super().__init__(f"Line {token.line}, column {token.column}: {message}")


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current = 0

    def parse(self) -> Program:
        declarations = []
        while not self._is_at_end():
            decl = self._declaration()
            if decl:
                declarations.append(decl)
        return Program(declarations)

    # ============ Declarations ============

    def _declaration(self) -> Optional[Stmt]:
        try:
            if self._match(TokenType.FN):
                return self._fn_declaration()
            if self._match(TokenType.VAR):
                return self._var_declaration()
            return self._statement()
        except ParseError as e:
            self._synchronize()
            raise e

    def _fn_declaration(self) -> FnDecl:
        name = self._consume(TokenType.IDENTIFIER, "Expected function name").lexeme
        self._consume(TokenType.LPAREN, "Expected '(' after function name")

        params = []
        if not self._check(TokenType.RPAREN):
            params.append(self._consume(TokenType.IDENTIFIER, "Expected parameter name").lexeme)
            while self._match(TokenType.COMMA):
                params.append(self._consume(TokenType.IDENTIFIER, "Expected parameter name").lexeme)

        self._consume(TokenType.RPAREN, "Expected ')' after parameters")
        self._consume(TokenType.LBRACE, "Expected '{' before function body")
        body = self._block()

        return FnDecl(name, params, body)

    def _var_declaration(self) -> VarDecl:
        name = self._consume(TokenType.IDENTIFIER, "Expected variable name").lexeme

        initializer = None
        if self._match(TokenType.ASSIGN):
            initializer = self._expression()

        return VarDecl(name, initializer)

    # ============ Statements ============

    def _statement(self) -> Stmt:
        if self._match(TokenType.IF):
            return self._if_statement()
        if self._match(TokenType.WHILE):
            return self._while_statement()
        if self._match(TokenType.RETURN):
            return self._return_statement()
        if self._match(TokenType.LBRACE):
            return self._block()
        return self._expression_statement()

    def _if_statement(self) -> IfStmt:
        condition = self._expression()
        self._consume(TokenType.LBRACE, "Expected '{' after if condition")
        then_branch = self._block()

        else_branch = None
        if self._match(TokenType.ELSE):
            if self._match(TokenType.IF):
                else_branch = self._if_statement()
            else:
                self._consume(TokenType.LBRACE, "Expected '{' after else")
                else_branch = self._block()

        return IfStmt(condition, then_branch, else_branch)

    def _while_statement(self) -> WhileStmt:
        condition = self._expression()
        self._consume(TokenType.LBRACE, "Expected '{' after while condition")
        body = self._block()
        return WhileStmt(condition, body)

    def _return_statement(self) -> ReturnStmt:
        value = None
        if not self._check(TokenType.RBRACE) and not self._is_at_end():
            # Check if next token could start an expression
            if not self._check(TokenType.RBRACE):
                value = self._expression()
        return ReturnStmt(value)

    def _block(self) -> Block:
        statements = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            decl = self._declaration()
            if decl:
                statements.append(decl)
        self._consume(TokenType.RBRACE, "Expected '}' after block")
        return Block(statements)

    def _expression_statement(self) -> ExprStmt:
        expr = self._expression()
        return ExprStmt(expr)

    # ============ Expressions ============

    def _expression(self) -> Expr:
        return self._assignment()

    def _assignment(self) -> Expr:
        expr = self._or()

        if self._match(TokenType.ASSIGN):
            value = self._assignment()
            if isinstance(expr, Identifier):
                return AssignExpr(expr.name, value)
            raise ParseError("Invalid assignment target", self._previous())

        return expr

    def _or(self) -> Expr:
        expr = self._and()

        while self._match(TokenType.OR):
            right = self._and()
            expr = BinaryExpr(expr, "or", right)

        return expr

    def _and(self) -> Expr:
        expr = self._equality()

        while self._match(TokenType.AND):
            right = self._equality()
            expr = BinaryExpr(expr, "and", right)

        return expr

    def _equality(self) -> Expr:
        expr = self._comparison()

        while self._match(TokenType.EQ, TokenType.NE):
            operator = "==" if self._previous().type == TokenType.EQ else "!="
            right = self._comparison()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def _comparison(self) -> Expr:
        expr = self._term()

        while self._match(TokenType.LT, TokenType.GT, TokenType.LE, TokenType.GE):
            op_map = {
                TokenType.LT: "<",
                TokenType.GT: ">",
                TokenType.LE: "<=",
                TokenType.GE: ">="
            }
            operator = op_map[self._previous().type]
            right = self._term()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def _term(self) -> Expr:
        expr = self._factor()

        while self._match(TokenType.PLUS, TokenType.MINUS):
            operator = "+" if self._previous().type == TokenType.PLUS else "-"
            right = self._factor()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def _factor(self) -> Expr:
        expr = self._unary()

        while self._match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_map = {
                TokenType.STAR: "*",
                TokenType.SLASH: "/",
                TokenType.PERCENT: "%"
            }
            operator = op_map[self._previous().type]
            right = self._unary()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def _unary(self) -> Expr:
        if self._match(TokenType.MINUS):
            operand = self._unary()
            return UnaryExpr("-", operand)
        if self._match(TokenType.NOT):
            operand = self._unary()
            return UnaryExpr("not", operand)
        return self._call()

    def _call(self) -> Expr:
        expr = self._primary()

        while True:
            if self._match(TokenType.LPAREN):
                expr = self._finish_call(expr)
            elif self._match(TokenType.DOT):
                name = self._consume(TokenType.IDENTIFIER, "Expected property name after '.'")
                expr = MemberExpr(expr, name.lexeme)
            else:
                break

        return expr

    def _finish_call(self, callee: Expr) -> CallExpr:
        arguments = []
        if not self._check(TokenType.RPAREN):
            arguments.append(self._expression())
            while self._match(TokenType.COMMA):
                arguments.append(self._expression())
        self._consume(TokenType.RPAREN, "Expected ')' after arguments")
        return CallExpr(callee, arguments)

    def _primary(self) -> Expr:
        if self._match(TokenType.NUMBER):
            return NumberLiteral(self._previous().value)

        if self._match(TokenType.STRING):
            return StringLiteral(self._previous().value)

        if self._match(TokenType.TRUE):
            return BoolLiteral(True)

        if self._match(TokenType.FALSE):
            return BoolLiteral(False)

        if self._match(TokenType.IDENTIFIER):
            return Identifier(self._previous().lexeme)

        if self._match(TokenType.LPAREN):
            expr = self._expression()
            self._consume(TokenType.RPAREN, "Expected ')' after expression")
            return GroupExpr(expr)

        raise ParseError("Expected expression", self._peek())

    # ============ Helpers ============

    def _match(self, *types: TokenType) -> bool:
        for t in types:
            if self._check(t):
                self._advance()
                return True
        return False

    def _check(self, token_type: TokenType) -> bool:
        if self._is_at_end():
            return False
        return self._peek().type == token_type

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]

    def _consume(self, token_type: TokenType, message: str) -> Token:
        if self._check(token_type):
            return self._advance()
        raise ParseError(message, self._peek())

    def _synchronize(self):
        """Panic mode recovery: skip tokens until we find a statement boundary."""
        self._advance()

        while not self._is_at_end():
            # After a closing brace, we're likely at a good spot
            if self._previous().type == TokenType.RBRACE:
                return

            # These keywords typically start statements
            if self._peek().type in (TokenType.FN, TokenType.VAR, TokenType.IF,
                                      TokenType.WHILE, TokenType.RETURN):
                return

            self._advance()


def parse(source: str) -> Program:
    """Convenience function to parse source code."""
    lexer = Lexer(source)
    tokens = lexer.scan_tokens()
    parser = Parser(tokens)
    return parser.parse()
