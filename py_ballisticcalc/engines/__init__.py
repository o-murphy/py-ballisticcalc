"""Integration engines for ballistic trajectory calculations.

This package provides multiple numerical integration engines for computing ballistic
trajectories with different trade-offs between accuracy, performance, and dependencies.
All engines implement the EngineProtocol interface.

Available Engines:
    - BaseIntegrationEngine: Abstract base class for all integration engines
    - EulerIntegrationEngine: First-order Euler method (simple but less accurate)
    - RK4IntegrationEngine: Fourth-order Runge-Kutta method (default, good balance)
    - VelocityVerletIntegrationEngine: Velocity Verlet method (energy conservative)
    - SciPyIntegrationEngine: Advanced SciPy solvers (high accuracy, requires scipy)

Engine Selection Guidelines:
    - Default: RK4IntegrationEngine (rk4_engine) - Good balance of speed and accuracy
    - Research: SciPyIntegrationEngine (scipy_engine) - Requires scipy installation
    - Educational: EulerIntegrationEngine (euler_engine) - Simple to understand
    - Speed: cythonized_rk4_engine - requires py_ballisticcalc[exts])

Configuration:
    - All engines accept BaseEngineConfigDict for configuration.
    - SciPyIntegrationEngine additionally supports SciPyEngineConfigDict for advanced options
         like integration method selection and error tolerance settings.

Examples:
    >>> from py_ballisticcalc.engines import RK4IntegrationEngine, BaseEngineConfigDict
    >>> custom_config = BaseEngineConfigDict(cMinimumVelocity=50.0)
    
    >>> # Using with Calculator
    >>> from py_ballisticcalc import Calculator
    >>> calc = Calculator(engine="scipy_engine")  # By name
    >>> calc = Calculator(config=custom_config, engine=RK4IntegrationEngine)  # By class

See Also:
    - py_ballisticcalc.generics.engine.EngineProtocol: Base protocol for engines
    - py_ballisticcalc.interface.Calculator: Main interface using engines
    - py_ballisticcalc.trajectory_data: Data structures for trajectory results
    - docs/concepts/benchmarks.md: Performance comparison of engines
"""

from .base_engine import *
from .euler import *
from .rk4 import *
from .scipy_engine import *
from .velocity_verlet import *

__all__ = (
    # Base engine infrastructure
    'create_base_engine_config',
    'BaseEngineConfig',
    'BaseEngineConfigDict',
    'DEFAULT_BASE_ENGINE_CONFIG',
    'BaseIntegrationEngine',
    'TrajectoryDataFilter',
    '_WindSock',
    '_ZeroCalcStatus',
    'with_no_minimum_velocity',
    'with_max_drop_zero',
    
    # Integration engines
    'EulerIntegrationEngine',
    'RK4IntegrationEngine',
    'VelocityVerletIntegrationEngine',
    'SciPyIntegrationEngine',
    
    # SciPy engine configuration
    'SciPyEngineConfig',
    'SciPyEngineConfigDict',
    'DEFAULT_SCIPY_ENGINE_CONFIG',
    'create_scipy_engine_config',
    'WindSock',
)
