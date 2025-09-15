"""Engine protocol module for py_ballisticcalc.

This module defines the EngineProtocol type protocol that all ballistic 
calculation engines must implement. The protocol specifies the interface
for integrating trajectories and finding zeroing angles, enabling 
interchangeable engine implementations throughout the library.

The EngineProtocol uses Python's typing.Protocol to define a structural
type that engine classes must conform to, ensuring consistent behavior
across different engine implementations while allowing for various
computational approaches and optimizations.

Classes:
    EngineProtocol: Type protocol for ballistic calculation engines

Type Variables:
    ConfigT: Configuration type for the engine (covariant)

Note:
    All engine implementations must provide both integrate() and zero_angle()
    methods with the exact signatures specified in this protocol to ensure
    compatibility with the Calculator interface and other library components.
"""

# Standard library imports
from abc import abstractmethod
from typing import Any, Optional, TypeVar, Union

# Third-party imports
from typing_extensions import Protocol, runtime_checkable

# Local imports
from py_ballisticcalc.conditions import Shot
from py_ballisticcalc.trajectory_data import HitResult, TrajFlag
from py_ballisticcalc.unit import Distance, Angular

__all__ = ['EngineProtocol', 'ConfigT']

# Type variable for engine configuration
ConfigT = TypeVar("ConfigT", covariant=True)


@runtime_checkable
class EngineProtocol(Protocol[ConfigT]):
    """Protocol defining the interface for ballistic trajectory calculation engines.

    This protocol outlines the methods that any concrete ballistic engine
    implementation should provide to perform trajectory calculations,
    retrieve drag model information, and determine zeroing angles for firearms.
    
    All engines implementing this protocol can be used interchangeably with
    the Calculator interface, enabling a modular architecture for different
    numerical integration methods and calculation approaches.

    Type Parameters:
        ConfigT: The configuration type used by this engine implementation.
                 Must be covariant to support configuration inheritance.

    Required Methods:
        - integrate: Perform ballistic trajectory calculation.
        - zero_angle: Calculate zero angle for given distance.

    Examples:
        ```python
        from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict

        class MyEngine(EngineProtocol[BaseEngineConfigDict]):
            def __init__(self, config: BaseEngineConfigDict):
                self.config = config

            def integrate(self, shot_info, max_range, **kwargs):
                # Implementation here
                pass

            def zero_angle(self, shot_info, distance):
                # Implementation here
                pass

        config = BaseEngineConfigDict(cStepMultiplier=1.0)
        engine = MyEngine(config)
        isinstance(engine, EngineProtocol)  # True
        ```

    See Also:
        - py_ballisticcalc.engines.base_engine.BaseIntegrationEngine: Base implementation
        - py_ballisticcalc.interface.Calculator: Uses EngineProtocol implementations

    Note:
        This protocol uses structural subtyping (duck typing) which means any class
        that implements the required methods will be considered compatible, even if
        it doesn't explicitly inherit from EngineProtocol. The @runtime_checkable
        decorator enables isinstance() checks at runtime.
    """
    
    def __init__(self, config: Optional[ConfigT] = None) -> None:
        ...

    @abstractmethod
    def integrate(
        self,
        shot_info: Shot,
        max_range: Distance,
        dist_step: Optional[Distance] = None,
        time_step: float = 0.0,
        filter_flags: Union[TrajFlag, int] = TrajFlag.NONE,
        dense_output: bool = False,
        **kwargs: Any,
    ) -> HitResult:
        """Perform ballistic trajectory calculation from shot parameters to maximum range.
        
        This method integrates the projectile's equations of motion to generate
        a complete trajectory from muzzle to the specified maximum range, accounting
        for gravitational acceleration, atmospheric drag, and environmental conditions.
        
        Args:
            shot_info: Complete shot configuration containing projectile data,
                      environmental conditions, sight configuration, and firing
                      parameters. Must include muzzle velocity, ballistic coefficient,
                      atmospheric conditions, and sight height information.
            max_range: Maximum distance for trajectory calculation. The integration
                      continues until the projectile reaches this range or impacts the ground.
            dist_step: Distance interval between trajectory data points. If None,
                      engine uses default step size for optimal accuracy/performance balance.
            time_step: Time interval for integration steps. Zero means engine
                      determines optimal step size automatically.
            filter_flags: Trajectory flags to control which data points are included
                         in the output. Use TrajFlag values to filter specific conditions.
            dense_output: If True, return trajectory data at every integration step.
                         If False, return data only at specified distance intervals.
            **kwargs: Additional engine-specific parameters for specialized calculations.
        
        Returns:
            HitResult: Complete trajectory calculation parameters and results.
        
        Raises:
            ValueError: If shot_info contains invalid or inconsistent parameters.
            RuntimeError: If the numerical integration fails to converge.
            OutOfRangeError: If the requested max_range exceeds computational limits.
        
        Mathematical Background:
            The integration solves the vector differential equation for projectile
            motion under the influence of gravity and atmospheric drag:
            ```
            dV/dt = D * |V| * (V - W) - g

            Where:
            - V = (v_x, v_y, v_z) is velocity relative to the ground
            - W = (w_x, w_y, w_z) is wind velocity vector relative to the ground
            - D = drag factor, which is a function of velocity, atmosphere, and
                    projectile characteristics that include shape and mass
            - g is gravitational acceleration
            ```

        Typical implementation steps:
            1. Initialize state vectors from shot_info parameters
            2. Set up integration bounds and step size parameters
            3. Begin numerical integration loop using chosen method
            4. At each step, calculate drag forces from atmospheric conditions
            5. Update position and velocity using integration formulae
            6. Check termination conditions (range limit, ground impact)
            7. Store trajectory points at specified intervals
            8. Return complete trajectory data structure
        """
        ...

    @abstractmethod
    def zero_angle(self, shot_info: Shot, distance: Distance) -> Angular:
        """Calculate launch angle required to hit target at specified distance.
        
        Args:
            shot_info: Complete shot configuration containing projectile data,
                      environmental conditions, sight configuration, and target
                      information. Must include muzzle velocity, ballistic coefficient,
                      atmospheric conditions, sight height, and target height.
            distance: Horizontal distance to target. Must be within the effective
                     range of the projectile under the given conditions.
        
        Returns:
            Angular: Launch angle required to hit the target.
        
        Raises:
            ValueError: If shot_info contains invalid parameters or distance
                       is negative or unreasonably large.
            ZeroFindingError: If the iterative algorithm fails to converge.
            OutOfRangeError: If the target distance exceeds maximum effective range.
        
        Note:
            This method returns the lower of the two ballistic solutions hit a target point.
            To get the higher ("lofted") solution we have been adding a .find_zero_angle()
            method that offers a `lofted: bool` parameter to select between the two.

        Mathematical Background:
            The method solves the equation `f(θ) = 0` where:
            ```
            f(θ) = y(target_distance, θ) - target_height

            Where y(x, θ) is the trajectory height function at distance x for
            launch angle θ. This requires iterative solution since the trajectory
            equation cannot be solved analytically for arbitrary drag functions.
            ```

        Typical implementation approach:
            1. Establish reasonable bounds for elevation angle search
            2. Define target function: trajectory_height(distance) - target_height
            3. Use root-finding algorithm (bisection, Newton, etc.)
            4. For each iteration, calculate trajectory to target distance
            5. Evaluate height difference at target distance
            6. Adjust angle estimate based on convergence strategy
            7. Continue until convergence tolerance is met
            8. Return final angle estimate
        """
        ...
