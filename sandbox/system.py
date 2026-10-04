"""
pairwise-sandbox-system - SandboxSystem

A sandbox physics/creation system:

- place_block:    collision check + support check + block-type placement rules
- update_physics: gravity + collision detection + rigid-body velocity
- update_circuit: wire conduction + signals + logic gates (AND/OR/NOT)
- update_block:   block states (flowing water) + interaction + destruction
- generate_world: terrain heightmap + biomes + infinite chunked generation
"""

import math


class SandboxSystem:
    GRAVITY = 9.81

    SOLID_BLOCKS = {"stone", "dirt", "grass", "wood", "sand", "bedrock"}
    FLUID_BLOCKS = {"water", "lava"}
    INTERACTIVE_BLOCKS = {"button", "lever", "switch"}
    # Block-type placement rules: which support a block type requires.
    PLACEMENT_RULES = {
        "torch": {"support": "solid"},
        "flower": {"support": {"dirt", "grass"}},
        "water": {"support": "any"},
        "lava": {"support": "any"},
    }
    BLOCK_HEALTH = {
        "stone": 30,
        "dirt": 10,
        "grass": 10,
        "wood": 20,
        "sand": 5,
        "bedrock": math.inf,
    }

    def __init__(self):
        self.state = {}
        self.world = {}  # (x, y, z) -> block dict
        self.player_position = (0, 1, 0)
        self.seed = 0
        self.time = 0.0

    # ------------------------------------------------------------------
    # Placement
    # ------------------------------------------------------------------
    def _block_at(self, position):
        return self.world.get(tuple(position))

    def _is_solid(self, position):
        block = self._block_at(position)
        return block is not None and block["type"] in self.SOLID_BLOCKS

    def _has_support(self, position, block_type):
        x, y, z = position
        if y <= 0:
            return True
        rule = self.PLACEMENT_RULES.get(block_type, {}).get("support")
        below = (x, y - 1, z)
        if rule == "any":
            return True
        if isinstance(rule, set):
            below_block = self._block_at(below)
            return below_block is not None and below_block["type"] in rule
        # default: needs a solid block underneath
        return self._is_solid(below)

    def place_block(self, position=None, block_type="stone", player_position=None):
        """Place a block with collision, support and block-type checks."""
        if position is None:
            position = (0, 1, 0)
        position = tuple(position)
        if player_position is None:
            player_position = self.player_position

        # Collision check: cell already occupied by another block.
        if self._block_at(position) is not None:
            return {"placed": False, "reason": "occupied", "position": position}

        # Collision check: cannot place a block on the player.
        px, py, pz = player_position
        player_cells = {(px, py, pz), (px, py + 1, pz)}
        if position in player_cells:
            return {"placed": False, "reason": "player_collision", "position": position}

        # Support check + block-type placement rules.
        if not self._has_support(position, block_type):
            return {"placed": False, "reason": "no_support", "position": position}

        block = {
            "type": block_type,
            "position": position,
            "health": self.BLOCK_HEALTH.get(block_type, 15),
            "velocity": [0.0, 0.0, 0.0],
            "state": {},
        }
        self.world[position] = block
        return {"placed": True, "reason": None, "position": position, "block": block}

    # ------------------------------------------------------------------
    # Physics
    # ------------------------------------------------------------------
    def update_physics(self, dt=1.0):
        """Apply gravity, collision detection and rigid-body velocity."""
        moved = []
        # Process from bottom up so falling blocks land on settled ones.
        for position in sorted(list(self.world), key=lambda p: p[1]):
            block = self.world.get(position)
            if block is None or block["type"] in self.FLUID_BLOCKS:
                continue
            x, y, z = position
            if y <= 0 or self._is_solid((x, y - 1, z)):
                block["velocity"] = [0.0, 0.0, 0.0]
                continue
            # Gravity: accelerate downward, then fall with collision detection.
            block["velocity"][1] -= self.GRAVITY * dt
            new_position = position
            while True:
                nx, ny, nz = new_position[0], new_position[1] - 1, new_position[2]
                if ny < 0 or self.world.get((nx, ny, nz)) is not None:
                    break  # collision detection: stop on ground or another block
                new_position = (nx, ny, nz)
            if new_position != position:
                del self.world[position]
                block["position"] = new_position
                self.world[new_position] = block
                moved.append({"block": block, "from": position, "to": new_position})
            block["velocity"] = [0.0, 0.0, 0.0]  # rigid body comes to rest on landing
        return {"moved": moved, "dt": dt}

    # ------------------------------------------------------------------
    # Circuits
    # ------------------------------------------------------------------
    def update_circuit(self, components=None):
        """Propagate power through wires, signals and logic gates."""
        if components is None:
            components = self.state.get("circuit", [])
        by_id = {c["id"]: c for c in components}
        powered = {}

        def evaluate(comp, visiting=()):
            cid = comp["id"]
            if cid in powered:
                return powered[cid]
            if cid in visiting:
                return False
            kind = comp.get("type")
            inputs = [by_id[i] for i in comp.get("inputs", []) if i in by_id]
            if kind == "source":
                value = bool(comp.get("on", True))
            elif kind == "switch":
                value = bool(comp.get("on", False))
            elif kind == "wire":  # wires conduct power from any live input
                value = any(evaluate(i, visiting + (cid,)) for i in inputs)
            elif kind == "and":
                value = bool(inputs) and all(evaluate(i, visiting + (cid,)) for i in inputs)
            elif kind == "or":
                value = any(evaluate(i, visiting + (cid,)) for i in inputs)
            elif kind == "not":
                value = not (evaluate(inputs[0], visiting + (cid,)) if inputs else False)
            elif kind == "lamp":  # signal sink: lights up when any input is live
                value = any(evaluate(i, visiting + (cid,)) for i in inputs)
            else:
                value = bool(comp.get("on", False))
            powered[cid] = value
            comp["powered"] = value
            return value

        for comp in components:
            evaluate(comp)
        self.state["circuit"] = components
        return {"components": components, "powered": powered}

    # ------------------------------------------------------------------
    # Block updates
    # ------------------------------------------------------------------
    def update_block(self, action=None, position=None, damage=0):
        """Update block states: fluid flow, interaction and destruction."""
        result = {"flowed": [], "interacted": None, "destroyed": []}

        # Interaction: pressing a button/lever toggles its signal state.
        if action == "interact" and position is not None:
            block = self._block_at(position)
            if block is not None and block["type"] in self.INTERACTIVE_BLOCKS:
                block["state"]["on"] = not block["state"].get("on", False)
                result["interacted"] = {"position": tuple(position), "on": block["state"]["on"]}

        # Destruction: damage reduces health, broken blocks are removed.
        if action == "damage" and position is not None:
            block = self._block_at(position)
            if block is not None:
                block["health"] -= damage
                if block["health"] <= 0:
                    del self.world[tuple(position)]
                    result["destroyed"].append(tuple(position))

        # State update: water flows down, then sideways into empty cells.
        for pos in sorted(list(self.world), key=lambda p: p[1]):
            block = self.world.get(pos)
            if block is None or block["type"] not in self.FLUID_BLOCKS:
                continue
            x, y, z = pos
            below = (x, y - 1, z)
            if y > 0 and self.world.get(below) is None:
                del self.world[pos]
                block["position"] = below
                self.world[below] = block
                result["flowed"].append({"from": pos, "to": below})
                continue
            if y > 0 and self.world.get(below) is not None:
                for side in ((x + 1, y, z), (x - 1, y, z), (x, y, z + 1), (x, y, z - 1)):
                    if self.world.get(side) is None and self.world.get((side[0], side[1] - 1, side[2])) is not None:
                        spread = {
                            "type": block["type"],
                            "position": side,
                            "health": block["health"],
                            "velocity": [0.0, 0.0, 0.0],
                            "state": dict(block["state"]),
                        }
                        self.world[side] = spread
                        result["flowed"].append({"from": pos, "to": side})
                        break
        return result

    # ------------------------------------------------------------------
    # World generation
    # ------------------------------------------------------------------
    BIOMES = ("plains", "desert", "forest", "mountains")
    BIOME_SURFACE = {"plains": "grass", "desert": "sand", "forest": "grass", "mountains": "stone"}

    def _height_at(self, x, z):
        s = self.seed + 1
        return int(8 + 4 * math.sin((x + s) * 0.3) * math.cos((z - s) * 0.2)
                   + 2 * math.sin((x * 0.13 + z * 0.17) * s % 3))

    def _biome_at(self, x, z):
        temperature = math.sin((x + self.seed) * 0.05)
        humidity = math.cos((z - self.seed) * 0.05)
        if temperature > 0.5:
            return "desert"
        if humidity > 0.5:
            return "forest"
        if temperature < -0.5:
            return "mountains"
        return "plains"

    def generate_chunk(self, chunk_x=0, chunk_z=0, size=16):
        """Generate one chunk; chunks tile infinitely in every direction."""
        blocks = {}
        for dx in range(size):
            for dz in range(size):
                x, z = chunk_x * size + dx, chunk_z * size + dz
                height = self._height_at(x, z)
                biome = self._biome_at(x, z)
                surface = self.BIOME_SURFACE[biome]
                for y in range(height + 1):
                    block_type = surface if y == height else ("dirt" if y >= height - 2 else "stone")
                    blocks[(x, y, z)] = {"type": block_type, "position": (x, y, z)}
        return {"chunk": (chunk_x, chunk_z), "biomes": {self._biome_at(chunk_x * size, chunk_z * size)},
                "blocks": blocks}

    def generate_world(self, chunks=1, seed=None, size=16):
        """Generate terrain with biomes; chunked so the world is infinite."""
        if seed is not None:
            self.seed = seed
        world = {"seed": self.seed, "chunks": {}, "infinite": True}
        for cx in range(chunks):
            for cz in range(chunks):
                chunk = self.generate_chunk(cx, cz, size)
                world["chunks"][(cx, cz)] = chunk
        self.state["world"] = world
        return world
