# Blitz Project Todo

## Phase 1: Language Foundation

- [x] Define language grammar (grammar.md)
- [x] Implement lexer (tokenizer)
  - [x] Token types: keywords, identifiers, numbers, operators, punctuation
  - [x] Handle comments (// and /* */)
  - [x] String literals
  - [x] Error reporting with line numbers
- [x] Define AST node types
  - [x] Expressions: binary, unary, literals, identifiers, calls, member access
  - [x] Statements: var decl, assignment, if/else, while, return, block
  - [x] Top-level: function definitions, global variables
- [x] Implement parser (recursive descent)
  - [x] Expression parsing with precedence
  - [x] Statement parsing
  - [x] Function definitions
  - [x] Error recovery

## Phase 2: Bytecode Compiler

- [x] Define bytecode format
  - [x] Opcode enum
  - [x] Instruction encoding
  - [x] Constant pool
  - [x] Function table
- [x] Implement code generator
  - [x] Expression compilation
  - [x] Statement compilation
  - [x] Variable resolution (local vs global)
  - [x] Function compilation
  - [x] Jump patching for control flow

## Phase 3: Virtual Machine

- [x] Stack-based interpreter
  - [x] Operand stack
  - [x] Call stack (frames)
  - [x] Local variables
  - [x] Global variables
- [x] Instruction execution loop
  - [x] Arithmetic operations
  - [x] Comparison operations
  - [x] Control flow (jumps, calls, returns)
  - [x] Intrinsic dispatch

## Phase 4: Game Runtime

- [x] Entity system
  - [x] Entity struct (type, position, velocity, etc.)
  - [x] Entity pool with recycling
  - [x] Spawn/destroy functions
- [x] Collision detection
  - [x] AABB collision
  - [x] Collision callbacks to Blitz code
- [x] Input handling
  - [x] Key state tracking
  - [x] Expose to Blitz via intrinsics
- [x] Game intrinsics
  - [x] `key_left()`, `key_right()`, `key_up()`, `key_down()`, `key_fire()`
  - [x] `spawn_bullet(x, y)`, `spawn_enemy(x, y, type)`
  - [x] `destroy(entity)`
  - [x] `random()`, `sin()`, `cos()`, `sqrt()`

## Phase 5: Shader Renderer

- [x] Window/OpenGL setup with moderngl
- [x] Single fullscreen quad
- [x] Entity data texture
  - [x] Pack entity state into texture
  - [x] Upload each frame
- [x] THE shader
  - [x] Background (starfield)
  - [x] Player ship (SDF)
  - [x] Enemy ships (SDF, multiple types)
  - [x] Bullets (glowing circles)
  - [x] Explosions (procedural)
  - [x] Score display (7-segment digits)
- [x] Uniform updates each frame

## Phase 6: The Game

- [x] Write shooter.blitz
  - [x] Player movement
  - [x] Shooting mechanics
  - [x] Enemy spawning patterns
  - [x] Collision handling
  - [x] Score tracking
  - [x] Wave system

## Phase 7: Polish (Future)

- [ ] Add sound (optional stretch goal)
- [ ] Add more enemy types
- [ ] Add power-ups
- [ ] Title screen
- [ ] Game over screen

---

## Current Progress

**Status**: COMPLETE - Core implementation done!

### What's Built:
1. **Blitz Language** - Custom C-like language with functions, variables, control flow
2. **Compiler** - Lexer, parser, AST, bytecode generator
3. **Virtual Machine** - Stack-based interpreter with intrinsics
4. **Game Runtime** - Entity system, collision detection, input handling
5. **Single Shader** - All rendering in one GLSL fragment shader
6. **The Game** - shoot'em up written entirely in Blitz

### To Run:
```bash
# Console mode (no graphics dependencies)
python main.py

# With graphics (requires: pip install moderngl moderngl-window pyglet)
python main.py
```
