# Blitz vs shmup8 Comparison

## Original Blog Post: "Making a game on a custom bytecode VM in 7 days and 3kB"

In the last few days, I built a shoot 'em up game by embedding a tiny custom bytecode VM and rendering the graphics using a fullscreen pixel shader. The result is a 3kB Windows executable.

This was done for Langjam Gamejam, a 7-day challenge where you create a programming language and then use it to build a game.

The project combines several interests of mine: language tooling, game development, procedural graphics, and demoscene-style size constraints. The game jam format forced me to keep the scope small and explore new ideas. Also, it was fun!

### The Context
When I first heard about the game jam, I immediately got interested. I thought for a few days, as it's not easy to find a game concept that would benefit from a new language (apart from, well, programming games like TIS-100).

Then I remembered demoscene productions that used custom bytecode to make things smaller. An example that came to mind was Ikadalawampu, a 2010 demo in 4kB that runs on Amiga. I was still a bit skeptical: is it really worth embedding an interpreter, just to make the actual code smaller? I had to give it a try.

Another inspiration of mine has been the first-person shooter video game, kkrieger, made in 2004 and that fits in 96kB. Since then, we've rarely seen good video games that were size-coded. Exploring this domain has been on the side of my mind for a while.

### The Plan
1. Design a language
2. Implement a compiler to compile it to bytecode, using F#
3. Write a bytecode interpreter, using C++
4. Create a shoot'em up game, using the custom language
5. Render the graphics, using a single GLSL shader

Although the design choices were made with size-coding in mind, I also didn't want to spend time optimizing the code. I originally estimated that the game would fit in 4 to 8kB, so I named the project shmup8. The executable turned out to be smaller than expected, but it's also because I didn't include music or 3D graphics. As always, the shader code is minified and the executable compressed with Crinkler.

### Live-coding Workflow
Coding is much more fun when there's instant visual feedback. I wanted to be able to write the entire game logic and visuals without recompiling C++ code. The idea was to run the executable once, then iterate entirely through live reload.

Each time I edit the source code in my IDE, my custom compiler is invoked, it dumps bytecode in a file. Then the C++ project reloads the bytecode that it executes at every frame. In a similar way, the GLSL shader is also reloaded automatically when edited.

Rapid iteration is a critical feature for productivity, especially in creative environments where you can hardly predict what will feel good.

### Bytecode Design
I quickly decided that the communication between bytecode and shader would happen through float arrays.

With minimalism in mind, I decided that I needed just one type: float32. All values are stored in arrays. You want a local variable? Pick a slot in a float array and use it. How to index the array? Use a float, the interpreter will cast it to int. How to write conditions? Use a float, it's true if it's greater than 0.5.

The bytecode has only two kinds of statements: either you update a cell in an array; or you jump (possibly with a condition) to another address in the bytecode.

The bytecode also has a concept of expression: so when you update a cell, the value can be a complex math expression that references other array cells or functions (like sine).

Constants between 0 and 255 are stored one byte. Other float numbers are stored on 2 bytes using my favourite float trick!

This design avoids things like stacks, registers, and type tagging, which keeps both the interpreter and the bytecode compact.

### Language Design
The minimalist bytecode restricts what I can support in the language, but I still have the possibility of using syntactic sugar to make some things nicer.

Using a C-like syntax, I implemented support for assignments, if conditions and while loops. Syntactic sugar is used to allow augmented assignments and for loops.

Each time the compiler sees a variable, it gives it a location in a float array. When a value is to be shared with the shader, I have to give it a specific position. For example, I decided that `state[5]` would store the current score. For increased readability, I added support for inlining things.

### Shader Graphics
This is very similar to what we have in ShaderToy. It's just about computing the color of a pixel based on the data provided by the game engine.

I kept the graphics code simple, as the game jam time is limited.

I used a feedback effect (blending the previous frame with the current frame) to make the visuals more interesting, and combined the effect with some noise functions.

### Game Design
The game design is also kept simple. The game is infinite. It starts with three enemies. It adds an enemy every 7 seconds. There are three kinds of enemies, each of them has its special behavior and visuals.

Contrary to what some might believe, enemies can't die. When a missile hits an enemy, it gets teleported outside the screen, and it's able to come back to the playing field.

This approach keeps the code very simple, while ensuring the game gets more and more challenging. Like in Super Hexagon, special care was taken to provide a rapid restart and encourage replays. Expect the game to last between 30s and 60s.

### Conclusion
The quick iteration workflow was essential. Designing the bytecode and the game in parallel made it hard to predict which features would be needed upfront, and many constraints only became apparent once I started writing the game itself.

Of course, a question remains... Is the bytecode actually smaller than using compiled C++? I ported the game logic to C++, removed the bytecode interpreter and checked the size.

The C++ version is 90 bytes bigger than the bytecode version. So the savings from using bytecode are more important than the interpreter size. Some people might say that the C++ engine I ported was not really optimized; but neither are the interpreter and the bytecode. So take the actual numbers with a grain of salt.

## Our Comparison Analysis

| Feature | Blog Post (shmup8) | Our Project (Blitz) |
|---------|-------------------|-------------------|
| Language | Custom C-like | Custom C-like (Blitz) |
| Compiler | F# → bytecode | Python → bytecode |
| Interpreter | C++ | Python VM |
| Game | Shoot'em up | Two games (vertical + horizontal) |
| Graphics | Single GLSL shader | Single GLSL shader |
| Lines of code | Not stated | ~3,450 lines |
| Final size | 3kB executable | N/A (Python, not compiled) |
| Live reload | Yes | No |
| Duration | 7 days | ~1 session |

### What We Have That's Competitive:
- Full compiler toolchain (lexer → parser → AST → bytecode)
- Stack-based VM with call frames, functions, locals, globals
- Complete game intrinsics (input, spawning, collision)
- Single GLSL shader rendering everything (SDFs, procedural starfield, 7-segment score)
- Two complete games proving the language works
- HiDPI/Retina support
- Game mode system (vertical/horizontal)

### What They Have That We Don't:
- 3kB compiled executable (we're Python, not size-optimized)
- Live-coding workflow with hot reload
- Music (we have none)
- Feedback effects in shader (frame blending)
- More polished visuals

### Key Differences:
1. Their bytecode is *extremely* minimal (single type: float32, no stack)
2. Ours is a proper stack-based VM with function calls, more like a real language
3. They optimized for size (Crinkler compression, 2-byte floats)
4. We optimized for demonstrating a complete language implementation

### Verdict: 
We built something more *complete* as a language (proper AST, real functions, multiple games), but they built something more *impressive* as a demo (3kB executable, live reload, feedback effects).

### Potential Improvements:
1. Add live reload (watch files, hot-reload on change)
2. Add shader feedback effects
3. Add more polish to the graphics
4. Add sound/music