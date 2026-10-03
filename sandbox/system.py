"""
pairwise-sandbox-system - SandboxSystem

This module contains a deliberately broken implementation.
Fix all bugs so that tests pass.
"""


class SandboxSystem:
    def __init__(self):
        self.state = {}

    def place_block(self, *args, **kwargs):
        """BUG: 放置方块不做碰撞检查，能放在玩家身上"""
        return None

    def update_physics(self, *args, **kwargs):
        """BUG: 物理不做重力，方块飘着"""
        return None

    def update_circuit(self, *args, **kwargs):
        """BUG: 电路不做导电，电线不导电"""
        return None

    def update_block(self, *args, **kwargs):
        """BUG: 方块不做状态，水不流动"""
        return None

    def generate_world(self, *args, **kwargs):
        """BUG: 世界不做地形，永远平地"""
        return None

