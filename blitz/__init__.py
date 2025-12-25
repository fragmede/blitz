"""Blitz programming language compiler."""

# Imports are done lazily to avoid circular dependencies
# Use: from blitz.compiler import compile_file
# Or:  from blitz.lexer import Lexer

__all__ = [
    'Lexer', 'Token', 'TokenType',
    'Parser',
    'CodeGenerator',
    'compile_source', 'compile_file',
]
