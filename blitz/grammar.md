# Blitz Language Grammar

## Lexical Elements

### Keywords
```
var fn if else while return true false and or not
```

### Operators
```
+  -  *  /  %           // Arithmetic
== != < > <= >=         // Comparison
=                       // Assignment
.                       // Member access
```

### Punctuation
```
( ) { } [ ] , ;
```

### Literals
- **Numbers**: `42`, `3.14`, `-17`, `0.5`
- **Booleans**: `true`, `false`
- **Strings**: `"hello world"` (for future use)

### Comments
```
// Single line comment
/* Multi-line
   comment */
```

## Grammar (EBNF)

```ebnf
program        = { declaration } ;

declaration    = fn_decl | var_decl | statement ;

fn_decl        = "fn" IDENTIFIER "(" [ parameters ] ")" block ;
parameters     = IDENTIFIER { "," IDENTIFIER } ;

var_decl       = "var" IDENTIFIER [ "=" expression ] ;

statement      = expr_stmt
               | if_stmt
               | while_stmt
               | return_stmt
               | block ;

expr_stmt      = expression ;
if_stmt        = "if" expression block [ "else" ( if_stmt | block ) ] ;
while_stmt     = "while" expression block ;
return_stmt    = "return" [ expression ] ;
block          = "{" { declaration } "}" ;

expression     = assignment ;
assignment     = ( IDENTIFIER "=" assignment ) | logic_or ;

logic_or       = logic_and { "or" logic_and } ;
logic_and      = equality { "and" equality } ;
equality       = comparison { ( "==" | "!=" ) comparison } ;
comparison     = term { ( "<" | ">" | "<=" | ">=" ) term } ;
term           = factor { ( "+" | "-" ) factor } ;
factor         = unary { ( "*" | "/" | "%" ) unary } ;
unary          = ( "-" | "not" ) unary | call ;
call           = primary { "(" [ arguments ] ")" | "." IDENTIFIER } ;
arguments      = expression { "," expression } ;
primary        = NUMBER | STRING | "true" | "false"
               | IDENTIFIER
               | "(" expression ")" ;
```

## Operator Precedence (lowest to highest)

| Precedence | Operators | Associativity |
|------------|-----------|---------------|
| 1 | `=` | Right |
| 2 | `or` | Left |
| 3 | `and` | Left |
| 4 | `== !=` | Left |
| 5 | `< > <= >=` | Left |
| 6 | `+ -` | Left |
| 7 | `* / %` | Left |
| 8 | `- not` (unary) | Right |
| 9 | `() .` (call, member) | Left |

## Type System

Blitz is dynamically typed with these runtime types:
- **Number**: 64-bit floating point
- **Boolean**: true/false
- **Entity**: Game entity reference (opaque handle)
- **Nil**: Absence of value

## Built-in Intrinsics

### Input
- `key_left()` -> bool
- `key_right()` -> bool
- `key_up()` -> bool
- `key_down()` -> bool
- `key_fire()` -> bool

### Math
- `sin(x)` -> number
- `cos(x)` -> number
- `sqrt(x)` -> number
- `abs(x)` -> number
- `random()` -> number (0 to 1)
- `floor(x)` -> number
- `min(a, b)` -> number
- `max(a, b)` -> number

### Game
- `spawn_bullet(x, y)` -> entity
- `spawn_enemy(x, y, type)` -> entity
- `destroy(entity)` -> nil
- `get_x(entity)` -> number
- `get_y(entity)` -> number
- `set_x(entity, x)` -> nil
- `set_y(entity, y)` -> nil

### System
- `print(value)` -> nil (debug)
- `time()` -> number (elapsed seconds)

## Example Program

```blitz
var player_x = 400.0
var player_y = 550.0
var fire_cooldown = 0.0

fn update(dt) {
    // Movement
    if key_left() {
        player_x = player_x - 300.0 * dt
    }
    if key_right() {
        player_x = player_x + 300.0 * dt
    }

    // Clamp to screen
    if player_x < 20.0 {
        player_x = 20.0
    }
    if player_x > 780.0 {
        player_x = 780.0
    }

    // Shooting
    if fire_cooldown > 0.0 {
        fire_cooldown = fire_cooldown - dt
    }

    if key_fire() and fire_cooldown <= 0.0 {
        spawn_bullet(player_x, player_y - 20.0)
        fire_cooldown = 0.15
    }
}

fn on_collision(a_type, b_type, a_id, b_id) {
    // Handle bullet hitting enemy
    if a_type == 1 and b_type == 2 {
        destroy(a_id)
        destroy(b_id)
    }
}
```
