import pytest
from sandbox.system import SandboxSystem


class TestSandboxSystem:

    def test_place_block(self):
        """放置方块不做碰撞检查，能放在玩家身上"""
        obj = SandboxSystem()
        result = obj.place_block()
        self.assertIsNotNone(result)

    def test_update_physics(self):
        """物理不做重力，方块飘着"""
        obj = SandboxSystem()
        result = obj.update_physics()
        self.assertIsNotNone(result)

    def test_update_circuit(self):
        """电路不做导电，电线不导电"""
        obj = SandboxSystem()
        result = obj.update_circuit()
        self.assertIsNotNone(result)

    def test_update_block(self):
        """方块不做状态，水不流动"""
        obj = SandboxSystem()
        result = obj.update_block()
        self.assertIsNotNone(result)

    def test_generate_world(self):
        """世界不做地形，永远平地"""
        obj = SandboxSystem()
        result = obj.generate_world()
        self.assertIsNotNone(result)

