#!/usr/bin/env python3
"""
Blitz Shooter - Main entry point

A shoot'em up game with:
- Custom Blitz programming language
- Bytecode compiler
- Stack-based virtual machine
- All graphics rendered in a single GLSL shader

Usage:
    python main.py [game.blitz]           # Compile and run
    python main.py --compile game.blitz   # Compile to .blitzc only
    python main.py game.blitzc            # Run pre-compiled bytecode
    python main.py --debug game.blitz     # Show bytecode disassembly
"""

import sys
from pathlib import Path


def main():
    # Add project to path
    project_dir = Path(__file__).parent
    sys.path.insert(0, str(project_dir))

    from blitz.compiler import compile_file, disassemble_program
    from vm.bytecode import save_bytecode, load_bytecode
    from runtime.game import GameRuntime

    # Default game file
    game_file = project_dir / "game" / "shooter.blitz"

    # Parse command line arguments
    compile_only = "--compile" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if args:
        game_file = Path(args[0])

    if not game_file.exists():
        print(f"Error: Game file not found: {game_file}")
        sys.exit(1)

    try:
        # Check if loading pre-compiled bytecode
        if game_file.suffix == '.blitzc':
            print(f"Loading bytecode {game_file}...")
            program = load_bytecode(str(game_file))
            print(f"Loaded {game_file.stat().st_size} bytes")
        else:
            print(f"Compiling {game_file}...")
            # Compile the game
            program = compile_file(str(game_file))

            # Save bytecode
            bytecode_file = game_file.with_suffix('.blitzc')
            bytes_written = save_bytecode(program, str(bytecode_file))
            print(f"Wrote bytecode: {bytecode_file} ({bytes_written} bytes)")

            if compile_only:
                print("\nCompilation complete (--compile mode)")
                print(f"  Functions: {len(program.functions)}")
                print(f"  Globals: {len(program.globals)}")
                return

        # Show disassembly in debug mode
        if "--debug" in sys.argv:
            print("\n" + disassemble_program(program))
            print()

        print("Compilation successful!")
        print(f"  Functions: {len(program.functions)}")
        print(f"  Globals: {len(program.globals)}")

        # Create runtime
        runtime = GameRuntime(program, width=800, height=600)

        # Initialize game (runs main chunk)
        runtime.init()

        print("\nStarting game...")
        print("  Arrow keys: Move")
        print("  Space/Z: Fire")
        print("  ESC: Quit")
        print()

        # Check for moderngl
        try:
            from render.window import run_game
            run_game(runtime)
        except ImportError as e:
            print(f"Error: {e}")
            print("\nTo run the graphical game, install dependencies:")
            print("  pip install moderngl moderngl-window pyglet")
            print("\nRunning in console mode instead...")
            run_console_mode(runtime)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_console_mode(runtime):
    """Run in console mode for testing without graphics."""
    import time

    print("\n--- Console Mode ---")
    print("Simulating 5 seconds of gameplay...\n")

    # Simulate some gameplay
    dt = 1.0 / 60.0  # 60 FPS

    # Press fire for testing
    runtime.key_down('fire')

    for frame in range(300):  # 5 seconds at 60 FPS
        runtime.update(dt)

        # Print status every second
        if frame % 60 == 0:
            state = runtime.state
            entities = runtime.entities.active_count
            print(f"Time: {state.time:.1f}s | Score: {state.score} | "
                  f"Lives: {state.lives} | Entities: {entities}")

    print("\n--- Simulation complete ---")
    print(f"Final score: {runtime.state.score}")


if __name__ == "__main__":
    main()
