"""Unit tests of multiple-bc drag models"""

import pytest

from py_ballisticcalc import *


class TestMBC:

    @pytest.fixture(autouse=True)
    def setup_method(self, loaded_engine_instance) -> None:
        """Establish baseline trajectory"""
        self.range = 1000
        self.step = 100
        self.dm = DragModel(0.22, TableG7)
        self.ammo = Ammo(self.dm, Velocity.FPS(2600))
        self.weapon = Weapon(4, 12)
        self.calc = Calculator(engine=loaded_engine_instance)
        self.baseline_shot = Shot(weapon=self.weapon, ammo=self.ammo)
        self.baseline_trajectory = self.calc.fire(shot=self.baseline_shot, trajectory_range=self.range,
                                                  trajectory_step=self.step).trajectory

    def test_mbc1(self):
        """We should get the same trajectory whether we give single bc or use multi-bc with single value"""
        dm_multi = DragModelMultiBC(
            [BCPoint(.22, V=Velocity.FPS(2500)), BCPoint(.22, V=Velocity.FPS(1500)), BCPoint(BC=.22, Mach=3)], TableG7)
        multi_shot = Shot(weapon=self.weapon, ammo=Ammo(dm_multi, self.ammo.mv))
        multi_trajectory = self.calc.fire(shot=multi_shot, trajectory_range=self.range,
                                          trajectory_step=self.step).trajectory
        for i in range(len(multi_trajectory)):
            assert multi_trajectory[i].formatted() == self.baseline_trajectory[i].formatted()

    def test_mbc2(self):
        """Setting different bc above muzzle velocity should have no effect"""
        dm_multi = DragModelMultiBC([BCPoint(.22, V=Velocity.FPS(2700)), BCPoint(.5, V=Velocity.FPS(3500))], TableG7)
        multi_shot = Shot(weapon=self.weapon, ammo=Ammo(dm_multi, self.ammo.mv))
        multi_trajectory = self.calc.fire(shot=multi_shot, trajectory_range=self.range,
                                          trajectory_step=self.step).trajectory
        for i in range(len(multi_trajectory)):
            assert multi_trajectory[i].formatted() == self.baseline_trajectory[i].formatted()

    def test_mbc3(self):
        """Setting higher bc should result in higher downrange velocities"""
        # So here we'll boost the bc for velocities lower than the baseline's velocity at 200 yards
        dm_multi = DragModelMultiBC(
            [BCPoint(.5, V=self.baseline_trajectory[3].velocity),
             BCPoint(.22, V=self.baseline_trajectory[2].velocity)],
            TableG7)
        multi_shot = Shot(weapon=self.weapon, ammo=Ammo(dm_multi, self.ammo.mv))
        multi_trajectory = self.calc.fire(shot=multi_shot, trajectory_range=self.range,
                                          trajectory_step=self.step).trajectory
        # Should show no change before 200 yards
        assert pytest.approx(multi_trajectory[1].velocity.raw_value, abs=1e-3) == self.baseline_trajectory[
            1].velocity.raw_value
        # Should be faster at any point after 200 yards
        assert multi_trajectory[4].velocity.raw_value > self.baseline_trajectory[4].velocity.raw_value

    def test_mbc(self):
        dm = DragModelMultiBC([BCPoint(0.275, V=Velocity.MPS(800)),
                               BCPoint(0.255, V=Velocity.MPS(500)),
                               BCPoint(0.26, V=Velocity.MPS(700))],
                              TableG7, weight=178, diameter=.308)
        assert pytest.approx(dm.drag_table[0].CD, abs=1e-8) == 0.1259323091692403
        assert pytest.approx(dm.drag_table[-1].CD, abs=1e-8) == 0.1577125859466895

    @pytest.mark.parametrize(
        "mach, expected_cd",
        [
            (1, 0.3384895315),
            (2, 0.2585639866),
            (3, 0.2069547831),
            (4, 0.1652052415),
            (5, 0.1381406102),
        ],
        ids=["mach_1", "mach_2", "mach_3", "mach_4", "mach_5"],
    )
    def test_mbc_valid(self, mach, expected_cd):
        # Litz's multi-bc table comversion to CDM, 338LM 285GR HORNADY ELD-M
        dm = DragModelMultiBC([BCPoint(0.417, V=Velocity.MPS(745)), BCPoint(0.409, V=Velocity.MPS(662)),
                               BCPoint(0.4, V=Velocity.MPS(580))],
                              drag_table=TableG7,
                              weight=Weight.Grain(285),
                              diameter=Distance.Inch(0.338)
                              )
        cds = [p.CD for p in dm.drag_table]
        machs = [p.Mach for p in dm.drag_table]

        try:
            idx = machs.index(mach)
            assert pytest.approx(cds[idx], abs=1e-3) == expected_cd
        except ValueError:
            pytest.fail(f"Mach number {mach} not found in drag table.")
