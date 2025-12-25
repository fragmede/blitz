# Blitz

A custom programming language, bytecode compiler, interpreter, and shoot'em up game - all rendered with a single GLSL fragment shader.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           BLITZ SYSTEM                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────┐  │
│  │  .blitz  │───▶│  Lexer   │───▶│  Parser  │───▶│   Codegen    │  │
│  │  source  │    │ (tokens) │    │  (AST)   │    │ (bytecode)   │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────────┘  │
│                                                         │          │
│                                                         ▼          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    BYTECODE (.blitzc)                        │  │
│  │  Stack-based VM instructions: PUSH, POP, ADD, JMP, CALL...   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                         │          │
│                                                         ▼          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      INTERPRETER                             │  │
│  │  Executes bytecode, manages game state, calls intrinsics     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                         │          │
│                                                         ▼          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    GAME RUNTIME                              │  │
│  │  Entity management, collision detection, input handling      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                         │          │
│                                                         ▼          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                 SINGLE GLSL SHADER                           │  │
│  │  ALL rendering: player, enemies, bullets, background, FX     │  │
│  │  Uses SDFs, procedural graphics, uniform entity buffers      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## The Language

Blitz is a simple imperative language designed for game logic:

```blitz
// Variables
var player_x = 400.0
var player_y = 550.0
var score = 0

// Functions
fn clamp(val, min, max) {
    if val < min { return min }
    if val > max { return max }
    return val
}

// Main game loop (called every frame)
fn update(dt) {
    // Input handling
    if key_left() {
        player_x = player_x - 300.0 * dt
    }
    if key_right() {
        player_x = player_x + 300.0 * dt
    }

    player_x = clamp(player_x, 20.0, 780.0)

    if key_fire() {
        spawn_bullet(player_x, player_y - 20.0)
    }
}

fn on_collision(a, b) {
    if a.type == BULLET and b.type == ENEMY {
        destroy(a)
        destroy(b)
        score = score + 100
    }
}
```

## Bytecode

Stack-based virtual machine with these instruction categories:

| Category | Instructions |
|----------|-------------|
| Stack | `PUSH_CONST`, `PUSH_VAR`, `POP`, `DUP` |
| Arithmetic | `ADD`, `SUB`, `MUL`, `DIV`, `NEG`, `MOD` |
| Comparison | `EQ`, `NE`, `LT`, `GT`, `LE`, `GE` |
| Logic | `AND`, `OR`, `NOT` |
| Control | `JMP`, `JZ`, `JNZ`, `CALL`, `RET` |
| Variables | `LOAD_LOCAL`, `STORE_LOCAL`, `LOAD_GLOBAL`, `STORE_GLOBAL` |
| Intrinsics | `INTRINSIC` (game-specific functions) |

## The Shader

One fragment shader renders EVERYTHING:

- **Background**: Procedural starfield with parallax
- **Player**: SDF-based ship shape with glow
- **Enemies**: Various procedural enemy designs
- **Bullets**: Glowing projectiles
- **Explosions**: Particle-like effects
- **UI**: Score display, health bar

Game state is passed via uniforms and a data texture.

## Project Structure

```
shader/
├── README.md
├── todo.md
├── blitz/
│   ├── __init__.py
│   ├── lexer.py        # Tokenizer
│   ├── parser.py       # AST builder
│   ├── ast.py          # AST node definitions
│   ├── codegen.py      # Bytecode generator
│   └── compiler.py     # Main compiler interface
├── vm/
│   ├── __init__.py
│   ├── opcodes.py      # Bytecode definitions
│   └── interpreter.py  # Bytecode executor
├── runtime/
│   ├── __init__.py
│   ├── game.py         # Game state management
│   ├── entities.py     # Entity system
│   └── intrinsics.py   # Built-in game functions
├── render/
│   ├── __init__.py
│   ├── window.py       # Window/OpenGL setup
│   └── shader.glsl     # THE shader (all rendering)
├── game/
│   └── shooter.blitz   # The game source code
└── main.py             # Entry point
```

## Running

```bash
# Install dependencies
uv pip install moderngl moderngl-window numpy pyglet

# Run the default game (shooter.blitz)
uv run python main.py

# Run a specific game
uv run python main.py game/shooter.blitz
uv run python main.py game/sideways.blitz

# Compile to bytecode only (no run)
uv run python main.py --compile game/shooter.blitz

# Run pre-compiled bytecode directly
uv run python main.py game/shooter.blitzc
uv run python main.py game/sideways.blitzc

# Compile and show bytecode disassembly
uv run python main.py --debug game/shooter.blitz
```

Or with standard pip:
```bash
pip install moderngl moderngl-window numpy pyglet
python main.py
python main.py game/shooter.blitzc  # Run pre-compiled
```

## Technical Details

### Shader Data Transfer

Entity data is packed into a texture (1024x1 RGBA32F):
- Each texel = one entity
- R: x position (0-800)
- G: y position (0-600)
- B: entity type + flags (packed)
- A: animation frame / rotation / extra data

Global uniforms:
- `u_time`: elapsed time
- `u_resolution`: screen size
- `u_player_pos`: player position (vec2)
- `u_score`: current score
- `u_entity_count`: active entities

### Why One Shader?

The challenge is to render everything without multiple draw calls or shader switches. This is achieved through:

1. **SDFs (Signed Distance Functions)**: Mathematical shapes that can be evaluated per-pixel
2. **Procedural textures**: No external assets, everything generated mathematically
3. **Branchless blending**: Smooth transitions between elements
4. **Entity iteration**: Loop through entity buffer in shader

## Inspiration

Built to prove that focused, well-architected code beats framework bloat.
