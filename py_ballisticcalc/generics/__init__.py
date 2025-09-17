"""Generic type definitions for ballistic calculation engines.

This package provides protocol definitions and type interfaces that establish
the contract for ballistic calculation engines within the py_ballisticcalc
library ecosystem.

The generic protocols defined here enable type-safe interoperability between
different engine implementations while maintaining flexibility for various
numerical integration approaches and calculation strategies.

Protocol Definitions:
    EngineProtocol: Core interface for ballistic trajectory calculation engines

Type Variables:
    ConfigT: Generic configuration type for engine parameters

Examples:
    >>> from py_ballisticcalc.generics import EngineProtocol
    >>> from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict
    >>> 
    >>> # Type checking with protocol
    >>> engine: EngineProtocol[BaseEngineConfigDict]
    >>> result = engine.integrate(shot_info, max_range)

Architecture:
    The generics package serves as the foundation for the engine system,
    defining interfaces that all concrete engine implementations must follow.
    This design enables:
    
    * Type-safe engine interchangeability
    * Consistent API across different integration methods
    * Runtime protocol compliance checking
    * Generic type support for configuration objects

See Also:
    py_ballisticcalc.engines: Concrete engine implementations
    py_ballisticcalc.interface.Calculator: Main calculator interface
    py_ballisticcalc.trajectory_data: Data structures for results

Note:
    This package uses Python's typing system with protocols to enable
    structural subtyping (duck typing) while maintaining type safety.
    Engines that implement the required methods will be compatible
    regardless of inheritance hierarchy.
"""

# Local imports
from .engine import ConfigT, EngineProtocol

__all__ = (
    'ConfigT',
    'EngineProtocol',
)