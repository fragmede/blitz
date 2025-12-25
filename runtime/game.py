"""Game runtime that connects the VM to the rendering system."""

import sys
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Set, Callable, Optional
import numpy as np

# Add project root to path for imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from runtime.entities import EntityManager, EntityType, Entity
from vm.interpreter import VM
from vm.opcodes import Intrinsic, CompiledProgram


@dataclass
class GameState:
    """Global game state."""
    score: int = 0
    lives: int = 3
    wave: int = 1
    time: float = 0.0
    player_x: float = 400.0
    player_y: float = 50.0  # Player at bottom (low Y in OpenGL coords)
    game_over: bool = False
    paused: bool = False


class GameRuntime:
    """Main game runtime that orchestrates everything."""

    def __init__(self, program: CompiledProgram, width: int = 800, height: int = 600):
        self.program = program
        self.width = width
        self.height = height

        # Game state
        self.state = GameState()
        self.entities = EntityManager()
        self.game_mode = 0  # 0 = vertical, 1 = horizontal

        # Input state
        self.keys_pressed: Set[str] = set()

        # Timing
        self.start_time = time.time()
        self.last_update = self.start_time

        # Create VM
        self.vm = VM(program)
        self._register_intrinsics()

        # Create player entity
        self.player_id = self.entities.spawn(
            EntityType.PLAYER,
            self.state.player_x,
            self.state.player_y
        )

    def _register_intrinsics(self):
        """Register game intrinsic handlers."""
        # Input
        self.vm.register_intrinsic(Intrinsic.KEY_LEFT,
            lambda args: 1.0 if 'left' in self.keys_pressed else 0.0)
        self.vm.register_intrinsic(Intrinsic.KEY_RIGHT,
            lambda args: 1.0 if 'right' in self.keys_pressed else 0.0)
        self.vm.register_intrinsic(Intrinsic.KEY_UP,
            lambda args: 1.0 if 'up' in self.keys_pressed else 0.0)
        self.vm.register_intrinsic(Intrinsic.KEY_DOWN,
            lambda args: 1.0 if 'down' in self.keys_pressed else 0.0)
        self.vm.register_intrinsic(Intrinsic.KEY_FIRE,
            lambda args: 1.0 if 'fire' in self.keys_pressed else 0.0)

        # Time
        self.vm.register_intrinsic(Intrinsic.TIME,
            lambda args: time.time() - self.start_time)

        # Entity management
        self.vm.register_intrinsic(Intrinsic.SPAWN_BULLET,
            lambda args: float(self.entities.spawn(EntityType.BULLET, args[0], args[1])))
        self.vm.register_intrinsic(Intrinsic.SPAWN_ENEMY,
            lambda args: float(self.entities.spawn(EntityType.ENEMY, args[0], args[1])))
        self.vm.register_intrinsic(Intrinsic.DESTROY,
            lambda args: self._destroy_entity(int(args[0])))
        self.vm.register_intrinsic(Intrinsic.GET_X,
            lambda args: self._get_entity_x(int(args[0])))
        self.vm.register_intrinsic(Intrinsic.GET_Y,
            lambda args: self._get_entity_y(int(args[0])))
        self.vm.register_intrinsic(Intrinsic.SET_X,
            lambda args: self._set_entity_x(int(args[0]), args[1]))
        self.vm.register_intrinsic(Intrinsic.SET_Y,
            lambda args: self._set_entity_y(int(args[0]), args[1]))
        self.vm.register_intrinsic(Intrinsic.GET_TYPE,
            lambda args: self._get_entity_type(int(args[0])))
        self.vm.register_intrinsic(Intrinsic.SET_GAME_MODE,
            lambda args: self._set_game_mode(int(args[0])))

    def _set_game_mode(self, mode: int) -> float:
        """Set game mode (0 = vertical, 1 = horizontal)."""
        self.entities.set_game_mode(mode)
        self.game_mode = mode
        return 0.0

    def _destroy_entity(self, entity_id: int) -> float:
        self.entities.destroy(entity_id)
        return 0.0

    def _get_entity_x(self, entity_id: int) -> float:
        entity = self.entities.get(entity_id)
        return entity.x if entity else 0.0

    def _get_entity_y(self, entity_id: int) -> float:
        entity = self.entities.get(entity_id)
        return entity.y if entity else 0.0

    def _set_entity_x(self, entity_id: int, x: float) -> float:
        entity = self.entities.get(entity_id)
        if entity:
            entity.x = x
        return 0.0

    def _set_entity_y(self, entity_id: int, y: float) -> float:
        entity = self.entities.get(entity_id)
        if entity:
            entity.y = y
        return 0.0

    def _get_entity_type(self, entity_id: int) -> float:
        entity = self.entities.get(entity_id)
        return float(entity.type) if entity else 0.0

    def init(self):
        """Initialize the game (run main chunk)."""
        self.vm.run_main()

    def update(self, dt: float):
        """Update game state for one frame."""
        if self.state.game_over or self.state.paused:
            return

        self.state.time += dt

        # Update screen dimensions in VM globals (for dynamic bounds)
        self.vm.globals['screen_width'] = float(self.width)
        self.vm.globals['screen_height'] = float(self.height)

        # Update player position in VM globals
        player = self.entities.get(self.player_id)
        if player:
            self.vm.globals['player_x'] = player.x
            self.vm.globals['player_y'] = player.y

        # Call update function in Blitz code
        if 'update' in self.program.functions:
            self.vm.call_function('update', dt)

        # Sync player position back from VM
        if player:
            if 'player_x' in self.vm.globals:
                player.x = self.vm.globals['player_x']
            if 'player_y' in self.vm.globals:
                player.y = self.vm.globals['player_y']

            self.state.player_x = player.x
            self.state.player_y = player.y

        # Update entities (movement)
        self.entities.update(dt)

        # Check collisions
        self._handle_collisions()

        # Remove off-screen entities
        self._cleanup_entities()

        # Update score from VM
        if 'score' in self.vm.globals:
            self.state.score = int(self.vm.globals['score'])

    def _handle_collisions(self):
        """Handle entity collisions."""
        collisions = self.entities.check_collisions()

        for e1, e2 in collisions:
            # Bullet hitting enemy
            if (e1.type == EntityType.BULLET and e2.type == EntityType.ENEMY) or \
               (e1.type == EntityType.ENEMY and e2.type == EntityType.BULLET):
                bullet = e1 if e1.type == EntityType.BULLET else e2
                enemy = e2 if e1.type == EntityType.BULLET else e1

                # Spawn explosion
                self.entities.spawn(EntityType.EXPLOSION, enemy.x, enemy.y)

                # Destroy both
                self.entities.destroy(bullet.id)
                self.entities.destroy(enemy.id)

                # Add score
                self.state.score += 100
                self.vm.globals['score'] = float(self.state.score)

            # Enemy hitting player
            elif (e1.type == EntityType.PLAYER and e2.type == EntityType.ENEMY) or \
                 (e1.type == EntityType.ENEMY and e2.type == EntityType.PLAYER):
                enemy = e1 if e1.type == EntityType.ENEMY else e2

                # Spawn explosion at enemy
                self.entities.spawn(EntityType.EXPLOSION, enemy.x, enemy.y)
                self.entities.destroy(enemy.id)

                # Lose a life
                self.state.lives -= 1
                if self.state.lives <= 0:
                    self.state.game_over = True

    def _cleanup_entities(self):
        """Remove entities that are off-screen."""
        for entity in self.entities.get_all_active():
            if entity.type == EntityType.PLAYER:
                continue  # Don't remove player

            # Check bounds
            margin = 50
            if (entity.y < -margin or entity.y > self.height + margin or
                entity.x < -margin or entity.x > self.width + margin):
                self.entities.destroy(entity.id)

    def key_down(self, key: str):
        """Handle key press."""
        self.keys_pressed.add(key)

    def key_up(self, key: str):
        """Handle key release."""
        self.keys_pressed.discard(key)

    def get_entity_data(self) -> np.ndarray:
        """Get entity data as numpy array for shader."""
        return self.entities.to_array()

    def get_render_uniforms(self) -> dict:
        """Get uniform values for the shader."""
        return {
            'u_time': self.state.time,
            'u_resolution': (self.width, self.height),
            'u_player_pos': (self.state.player_x, self.state.player_y),
            'u_score': self.state.score,
            'u_lives': self.state.lives,
            'u_entity_count': self.entities.active_count,
            'u_game_mode': self.game_mode,
        }
