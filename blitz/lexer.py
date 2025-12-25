"""Lexer for the Blitz language."""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional


class TokenType(Enum):
    # Literals
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()

    # Keywords
    VAR = auto()
    FN = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    RETURN = auto()
    TRUE = auto()
    FALSE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()

    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    EQ = auto()
    NE = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    ASSIGN = auto()
    DOT = auto()

    # Punctuation
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    SEMICOLON = auto()

    # Special
    EOF = auto()
    ERROR = auto()


KEYWORDS = {
    'var': TokenType.VAR,
    'fn': TokenType.FN,
    'if': TokenType.IF,
    'else': TokenType.ELSE,
    'while': TokenType.WHILE,
    'return': TokenType.RETURN,
    'true': TokenType.TRUE,
    'false': TokenType.FALSE,
    'and': TokenType.AND,
    'or': TokenType.OR,
    'not': TokenType.NOT,
}


@dataclass
class Token:
    type: TokenType
    lexeme: str
    value: object  # For literals
    line: int
    column: int

    def __repr__(self):
        if self.value is not None:
            return f"Token({self.type.name}, {self.lexeme!r}, {self.value})"
        return f"Token({self.type.name}, {self.lexeme!r})"


class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Line {line}, column {column}: {message}")


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.tokens: List[Token] = []
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1
        self.start_column = 1

    def scan_tokens(self) -> List[Token]:
        while not self._is_at_end():
            self.start = self.current
            self.start_column = self.column
            self._scan_token()

        self.tokens.append(Token(TokenType.EOF, "", None, self.line, self.column))
        return self.tokens

    def _scan_token(self):
        c = self._advance()

        # Single-character tokens
        if c == '(':
            self._add_token(TokenType.LPAREN)
        elif c == ')':
            self._add_token(TokenType.RPAREN)
        elif c == '{':
            self._add_token(TokenType.LBRACE)
        elif c == '}':
            self._add_token(TokenType.RBRACE)
        elif c == '[':
            self._add_token(TokenType.LBRACKET)
        elif c == ']':
            self._add_token(TokenType.RBRACKET)
        elif c == ',':
            self._add_token(TokenType.COMMA)
        elif c == ';':
            self._add_token(TokenType.SEMICOLON)
        elif c == '.':
            self._add_token(TokenType.DOT)
        elif c == '+':
            self._add_token(TokenType.PLUS)
        elif c == '-':
            self._add_token(TokenType.MINUS)
        elif c == '*':
            self._add_token(TokenType.STAR)
        elif c == '%':
            self._add_token(TokenType.PERCENT)

        # Two-character tokens or single
        elif c == '/':
            if self._match('/'):
                # Single-line comment
                while self._peek() != '\n' and not self._is_at_end():
                    self._advance()
            elif self._match('*'):
                # Multi-line comment
                self._block_comment()
            else:
                self._add_token(TokenType.SLASH)

        elif c == '=':
            if self._match('='):
                self._add_token(TokenType.EQ)
            else:
                self._add_token(TokenType.ASSIGN)

        elif c == '!':
            if self._match('='):
                self._add_token(TokenType.NE)
            else:
                self._error(f"Unexpected character '!'")

        elif c == '<':
            if self._match('='):
                self._add_token(TokenType.LE)
            else:
                self._add_token(TokenType.LT)

        elif c == '>':
            if self._match('='):
                self._add_token(TokenType.GE)
            else:
                self._add_token(TokenType.GT)

        # Whitespace
        elif c in ' \r\t':
            pass  # Ignore

        elif c == '\n':
            self.line += 1
            self.column = 1

        # String literals
        elif c == '"':
            self._string()

        # Numbers
        elif c.isdigit():
            self._number()

        # Identifiers and keywords
        elif c.isalpha() or c == '_':
            self._identifier()

        else:
            self._error(f"Unexpected character '{c}'")

    def _string(self):
        while self._peek() != '"' and not self._is_at_end():
            if self._peek() == '\n':
                self.line += 1
                self.column = 1
            self._advance()

        if self._is_at_end():
            self._error("Unterminated string")
            return

        # Closing "
        self._advance()

        # Trim quotes
        value = self.source[self.start + 1:self.current - 1]
        self._add_token(TokenType.STRING, value)

    def _number(self):
        while self._peek().isdigit():
            self._advance()

        # Look for decimal part
        if self._peek() == '.' and self._peek_next().isdigit():
            self._advance()  # Consume the '.'
            while self._peek().isdigit():
                self._advance()

        value = float(self.source[self.start:self.current])
        self._add_token(TokenType.NUMBER, value)

    def _identifier(self):
        while self._peek().isalnum() or self._peek() == '_':
            self._advance()

        text = self.source[self.start:self.current]
        token_type = KEYWORDS.get(text, TokenType.IDENTIFIER)
        self._add_token(token_type)

    def _block_comment(self):
        nesting = 1
        while nesting > 0 and not self._is_at_end():
            if self._peek() == '/' and self._peek_next() == '*':
                self._advance()
                self._advance()
                nesting += 1
            elif self._peek() == '*' and self._peek_next() == '/':
                self._advance()
                self._advance()
                nesting -= 1
            else:
                if self._peek() == '\n':
                    self.line += 1
                    self.column = 1
                self._advance()

        if nesting > 0:
            self._error("Unterminated block comment")

    def _is_at_end(self) -> bool:
        return self.current >= len(self.source)

    def _advance(self) -> str:
        c = self.source[self.current]
        self.current += 1
        self.column += 1
        return c

    def _peek(self) -> str:
        if self._is_at_end():
            return '\0'
        return self.source[self.current]

    def _peek_next(self) -> str:
        if self.current + 1 >= len(self.source):
            return '\0'
        return self.source[self.current + 1]

    def _match(self, expected: str) -> bool:
        if self._is_at_end():
            return False
        if self.source[self.current] != expected:
            return False
        self.current += 1
        self.column += 1
        return True

    def _add_token(self, token_type: TokenType, value: object = None):
        lexeme = self.source[self.start:self.current]
        self.tokens.append(Token(token_type, lexeme, value, self.line, self.start_column))

    def _error(self, message: str):
        self.tokens.append(Token(TokenType.ERROR, message, None, self.line, self.start_column))


def tokenize(source: str) -> List[Token]:
    """Convenience function to tokenize source code."""
    lexer = Lexer(source)
    return lexer.scan_tokens()
