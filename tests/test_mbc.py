"""Unit tests of multiple-BC drag models and interpolation of drag curves"""
import math
import random

import pytest

from py_ballisticcalc import *
from py_ballisticcalc.drag_model import BCPoint, make_data_points, linear_interpolation
from py_ballisticcalc.drag_tables import TableG1, TableG7
from py_ballisticcalc.shot import ShotProps
from tests.fixtures_and_helpers import create_23_mm_shot, create_5_56_mm_shot, create_7_62_mm_shot

pytestmark = pytest.mark.engine

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

    def test_bcpoint_validation_errors(self):
        with pytest.raises(ValueError):
            BCPoint(BC=0.0, Mach=1.0)
        with pytest.raises(ValueError):
            BCPoint(BC=0.1, Mach=1.0, V=Unit.MPS(300))
        with pytest.raises(ValueError):
            BCPoint(BC=0.1)

    def test_make_data_points_type_errors(self):
        with pytest.raises(TypeError):
            make_data_points([{"Mach": 1.0}])  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            make_data_points([{"CD": 0.1}])  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            make_data_points(["bad"])  # type: ignore[arg-type]

    def test_drag_model_repr_and_multibc_minimal(self):
        dm = DragModel(0.2, [DragDataPoint(0.5, 0.3), DragDataPoint(1.5, 0.2)])
        s = repr(dm)
        assert s.startswith("DragModel(")

        # Multi-BC with V specified exercises conversion path; weight/diameter default to 0
        m = DragModelMultiBC(
            [BCPoint(BC=0.2, V=Unit.MPS(300)), BCPoint(BC=0.25, V=Unit.MPS(600))],
            [DragDataPoint(0.5, 0.3), DragDataPoint(1.5, 0.2)],
        )
        assert isinstance(m, DragModel)

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
        # Here we'll boost the bc for velocities lower than the baseline's velocity at 200 yards
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
                              drag_table=TableG7, weight=Weight.Grain(285), diameter=Distance.Inch(0.338)
        )
        cds = [p.CD for p in dm.drag_table]
        machs = [p.Mach for p in dm.drag_table]

        try:
            idx = machs.index(mach)
            assert pytest.approx(cds[idx], abs=1e-3) == expected_cd
        except ValueError:
            pytest.fail(f"Mach number {mach} not found in drag table.")


class TestLinearInterpolationValidation:
    def test_xp_must_be_strictly_increasing(self):
        with pytest.raises(ValueError, match="xp must be strictly increasing"):
            _ = linear_interpolation([0.0, 0.5, 1.0], [0.0, 0.0, 1.0], [1.0, 2.0, 3.0])

    def test_xp_unsorted_raises(self):
        with pytest.raises(ValueError, match="xp must be strictly increasing"):
            _ = linear_interpolation([0.0, 0.5, 1.0], [0.0, 2.0, 1.0], [1.0, 2.0, 3.0])


class TestShotPropsDrag:

    @staticmethod
    def _expected_sdf(cd: float, bc: float) -> float:
        # Matches ShotProps.drag_by_mach scaling: cd * 2.08551e-04 / bc
        return cd * 2.08551e-04 / bc

    @staticmethod
    def _mach(dp) -> float:
        return dp["Mach"] if isinstance(dp, dict) else dp.Mach

    @staticmethod
    def _cd(dp) -> float:
        return dp["CD"] if isinstance(dp, dict) else dp.CD

    @staticmethod
    def _segment_pairs(table) -> list[tuple[object, object]]:
        return list(zip(table[:-1], table[1:]))

    @pytest.mark.parametrize(
        "shot_factory, table",
        [
            (create_23_mm_shot, TableG1),
            (create_7_62_mm_shot, TableG7),
            (create_5_56_mm_shot, TableG7),
        ],
    )
    def test_drag_exact_at_knots(self, shot_factory, table):
        # ShotProps.drag_by_mach should reproduce the tabulated value at all knots (after SDF scaling)
        shot = shot_factory()
        sp = ShotProps.from_shot(shot)
        bc = sp.bc
        for dp in table:
            got = sp.drag_by_mach(self._mach(dp))
            exp = self._expected_sdf(self._cd(dp), bc)
            assert math.isfinite(got)
            # allow very small tolerance due to floating math; should typically be exact at knots
            assert abs(got - exp) <= max(1e-10, 1e-10 * abs(exp))

    @pytest.mark.parametrize(
        "shot_factory, table",
        [
            (create_23_mm_shot, TableG1),
            (create_7_62_mm_shot, TableG7),
        ],
    )
    def test_drag_monotone_between_adjacent_knots(self, shot_factory, table):
        # For each adjacent pair (Mach_i, CD_i) -> (Mach_{i+1}, CD_{i+1})
        # the interpolated value at interior points should lie within [min, max] of the segment endpoints.
        shot = shot_factory()
        sp = ShotProps.from_shot(shot)
        bc = sp.bc
        for left, right in self._segment_pairs(table):
            x0, y0 = self._mach(left), self._expected_sdf(self._cd(left), bc)
            x1, y1 = self._mach(right), self._expected_sdf(self._cd(right), bc)
            lo, hi = (y0, y1) if y0 <= y1 else (y1, y0)
            # Sample a few interior points (avoid exact endpoints)
            for w in (0.1, 0.25, 0.5, 0.75, 0.9):
                x = x0 + (x1 - x0) * w
                y = sp.drag_by_mach(x)
                assert math.isfinite(y)
                assert lo - 1e-10 <= y <= hi + 1e-10

    @pytest.mark.parametrize(
        "shot_factory, table",
        [
            (create_23_mm_shot, TableG1),
            (create_7_62_mm_shot, TableG7),
        ],
    )
    def test_drag_continuity_near_knots(self, shot_factory, table):
        # Evaluate just to the left and right of interior knots; expect continuity (small jump tolerance)
        shot = shot_factory()
        sp = ShotProps.from_shot(shot)
        xs = [self._mach(dp) for dp in table]
        # pick a small epsilon relative to local spacing
        for i in range(1, len(xs) - 1):
            h_left = xs[i] - xs[i - 1]
            h_right = xs[i + 1] - xs[i]
            eps = 1e-6 * min(h_left, h_right)
            x_left = xs[i] - eps
            x_right = xs[i] + eps
            y_left = sp.drag_by_mach(x_left)
            y_mid = sp.drag_by_mach(xs[i])
            y_right = sp.drag_by_mach(x_right)
            assert abs(y_left - y_mid) < 1e-4
            assert abs(y_right - y_mid) < 1e-4

    @pytest.mark.parametrize(
        "shot_factory, table",
        [
            (create_23_mm_shot, TableG1),
            (create_7_62_mm_shot, TableG7),
        ],
    )
    def test_drag_random_sampling_within_table_bounds(self, shot_factory, table):
        # Random sampling to stress a variety of segments; check envelope bounds on sampled segment
        random.seed(42)  # Fix random seed for reproducibility
        shot = shot_factory()
        sp = ShotProps.from_shot(shot)
        bc = sp.bc
        xs = [self._mach(dp) for dp in table]
        cds = [self._cd(dp) for dp in table]
        for _ in range(100):
            # pick a random segment
            i = random.randint(0, len(xs) - 2)
            x0, x1 = xs[i], xs[i + 1]
            y0, y1 = self._expected_sdf(cds[i], bc), self._expected_sdf(cds[i + 1], bc)
            lo, hi = (y0, y1) if y0 <= y1 else (y1, y0)
            w = random.random()
            x = x0 + (x1 - x0) * w
            y = sp.drag_by_mach(x)
            assert math.isfinite(y)
            assert lo - 1e-10 <= y <= hi + 1e-10

    @pytest.mark.parametrize("shot_factory", [create_23_mm_shot, create_7_62_mm_shot])
    def test_drag_out_of_range_is_finite_positive(self, shot_factory):
        # Evaluate slightly beyond the table bounds; expect a finite, positive result
        shot = shot_factory()
        sp = ShotProps.from_shot(shot)
        table = shot.ammo.dm.drag_table
        xs = [self._mach(dp) for dp in table]
        x_min, x_max = xs[0], xs[-1]
        for x in (x_min - 0.1, x_min - 1e-3, x_max + 1e-3, x_max + 0.1):
            y = sp.drag_by_mach(x)
            assert math.isfinite(y)
            assert y > 0.0
