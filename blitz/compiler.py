"""Main compiler interface for Blitz."""

import sys
from pathlib import Path

# Add project root to path for imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from blitz.lexer import Lexer
from blitz.parser import Parser
from blitz.codegen import CodeGenerator
from vm.opcodes import CompiledProgram


def compile_source(source: str) -> CompiledProgram:
    """Compile source code to a program."""
    # Lexing
    lexer = Lexer(source)
    tokens = lexer.scan_tokens()

    # Check for lexer errors
    for token in tokens:
        from blitz.lexer import TokenType
        if token.type == TokenType.ERROR:
            raise SyntaxError(f"Lexer error at line {token.line}: {token.lexeme}")

    # Parsing
    parser = Parser(tokens)
    ast = parser.parse()

    # Code generation
    codegen = CodeGenerator()
    program = codegen.compile(ast)

    return program


def compile_file(path: str) -> CompiledProgram:
    """Compile a file to a program."""
    source = Path(path).read_text()
    return compile_source(source)


def disassemble_program(program: CompiledProgram) -> str:
    """Return a human-readable disassembly of a compiled program."""
    lines = []

    # Main chunk
    lines.append(program.main_chunk.disassemble("main"))
    lines.append("")

    # Functions
    for name, func in program.functions.items():
        lines.append(f"Function: {name}({func.arity} params, {func.locals_count} locals)")
        lines.append(func.chunk.disassemble(name))
        lines.append("")

    # Globals
    if program.globals:
        lines.append("Globals:")
        for name in program.globals:
            lines.append(f"  {name}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m blitz.compiler <file.blitz>")
        sys.exit(1)

    path = sys.argv[1]
    try:
        program = compile_file(path)
        print(disassemble_program(program))
    except Exception as e:
        print(f"Compilation error: {e}")
        sys.exit(1)
