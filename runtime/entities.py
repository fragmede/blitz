"""Entity system for the game runtime."""

from enum import IntEnum, auto
from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np


class EntityType(IntEnum):
    """Types of game entities."""
    NONE = 0
    PLAYER = 1
    BULLET = 2
    ENEMY = 3
    EXPLOSION = 4
    POWERUP = 5


@dataclass
class Entity:
    """A game entity."""
    id: int
    type: EntityType
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0  # Velocity x
    vy: float = 0.0  # Velocity y
    width: float = 20.0
    height: float = 20.0
    active: bool = True
    data: float = 0.0  # Extra data (animation frame, health, etc.)
    lifetime: float = 0.0  # For temporary entities


class EntityManager:
    """Manages game entities with object pooling."""

    MAX_ENTITIES = 512

    def __init__(self):
        self.entities: List[Optional[Entity]] = [None] * self.MAX_ENTITIES
        self.active_count = 0
        self.next_id = 1

    def spawn(self, entity_type: EntityType, x: float, y: float) -> int:
        """Spawn a new entity and return its ID."""
        # Find a free slot
        for i in range(self.MAX_ENTITIES):
            if self.entities[i] is None or not self.entities[i].active:
                entity_id = self.next_id
                self.next_id += 1

                # Set default properties based on type
                width, height = self._get_default_size(entity_type)
                vx, vy = self._get_default_velocity(entity_type)

                self.entities[i] = Entity(
                    id=entity_id,
                    type=entity_type,
                    x=x,
                    y=y,
                    vx=vx,
                    vy=vy,
                    width=width,
                    height=height,
                    active=True
                )
                self.active_count += 1
                return entity_id

        return -1  # No free slots

    def destroy(self, entity_id: int):
        """Destroy an entity by ID."""
        for i in range(self.MAX_ENTITIES):
            if self.entities[i] and self.entities[i].id == entity_id:
                self.entities[i].active = False
                self.active_count -= 1
                return

    def get(self, entity_id: int) -> Optional[Entity]:
        """Get an entity by ID."""
        for i in range(self.MAX_ENTITIES):
            if self.entities[i] and self.entities[i].id == entity_id and self.entities[i].active:
                return self.entities[i]
        return None

    def get_all_active(self) -> List[Entity]:
        """Get all active entities."""
        return [e for e in self.entities if e and e.active]

    def update(self, dt: float):
        """Update all entities."""
        for entity in self.entities:
            if entity and entity.active:
                # Update position
                entity.x += entity.vx * dt
                entity.y += entity.vy * dt

                # Update lifetime for temporary entities
                if entity.type in (EntityType.BULLET, EntityType.EXPLOSION):
                    entity.lifetime += dt

                # Remove expired entities
                if entity.type == EntityType.EXPLOSION and entity.lifetime > 0.5:
                    entity.active = False
                    self.active_count -= 1

    def check_collisions(self) -> List[tuple]:
        """Check for entity collisions. Returns list of (entity1, entity2) pairs."""
        collisions = []
        active = self.get_all_active()

        for i, e1 in enumerate(active):
            for e2 in active[i+1:]:
                if self._aabb_collision(e1, e2):
                    collisions.append((e1, e2))

        return collisions

    def _aabb_collision(self, e1: Entity, e2: Entity) -> bool:
        """Check AABB collision between two entities."""
        return (e1.x - e1.width/2 < e2.x + e2.width/2 and
                e1.x + e1.width/2 > e2.x - e2.width/2 and
                e1.y - e1.height/2 < e2.y + e2.height/2 and
                e1.y + e1.height/2 > e2.y - e2.height/2)

    def _get_default_size(self, entity_type: EntityType) -> tuple:
        """Get default width/height for entity type."""
        sizes = {
            EntityType.PLAYER: (40, 40),
            EntityType.BULLET: (8, 16),
            EntityType.ENEMY: (32, 32),
            EntityType.EXPLOSION: (48, 48),
            EntityType.POWERUP: (20, 20),
        }
        return sizes.get(entity_type, (20, 20))

    def _get_default_velocity(self, entity_type: EntityType) -> tuple:
        """Get default velocity for entity type."""
        velocities = {
            EntityType.PLAYER: (0, 0),
            EntityType.BULLET: (0, -500),  # Bullets go up
            EntityType.ENEMY: (0, 100),    # Enemies go down
            EntityType.EXPLOSION: (0, 0),
            EntityType.POWERUP: (0, 50),
        }
        return velocities.get(entity_type, (0, 0))

    def to_array(self) -> np.ndarray:
        """Convert entities to a numpy array for shader upload.

        Returns array of shape (MAX_ENTITIES, 4) where each row is:
        [x, y, type_and_flags, data]
        """
        data = np.zeros((self.MAX_ENTITIES, 4), dtype=np.float32)

        for i, entity in enumerate(self.entities):
            if entity and entity.active:
                data[i, 0] = entity.x
                data[i, 1] = entity.y
                # Pack type and active flag
                data[i, 2] = float(entity.type) + (1.0 if entity.active else 0.0) * 0.1
                data[i, 3] = entity.data
            else:
                data[i, 2] = 0.0  # Inactive

        return data

    def clear(self):
        """Clear all entities."""
        for i in range(self.MAX_ENTITIES):
            self.entities[i] = None
        self.active_count = 0
