"""Ballistic Trajectory Data Export to pandas DataFrame.

Integration:
    This module is automatically used by the HitResult.dataframe() method.

Typical Usage:
    ```python
    from py_ballisticcalc import Calculator, Shot
    from py_ballisticcalc.visualize.dataframe import hit_result_as_dataframe
    
    # Calculate trajectory
    calc = Calculator()
    shot = Shot(...)
    hit_result = calc.fire(shot, max_range=1000)
    
    # Convert to DataFrame
    df = hit_result_as_dataframe(hit_result)
    
    # Perform data analysis
    print(df.describe())
    print(df[df['distance'] > 500])
    
    # Export to various formats
    df.to_csv('trajectory_data.csv')
    df.to_excel('trajectory_analysis.xlsx')
    ```

Dependencies:
    This module requires pandas as an optional dependency. Install via:
    pip install py_ballisticcalc[visualize]
    
    If pandas is not available, importing functions from this module will raise
    an informative ImportError with installation instructions.
"""

# pylint: skip-file
# Standard library imports
import warnings

# Local imports
from py_ballisticcalc.trajectory_data import HitResult, TrajectoryData

# Handle optional pandas dependency with graceful degradation
try:
    from pandas import DataFrame
except ImportError as error:
    warnings.warn("Install pandas to convert trajectory to pandas.DataFrame", UserWarning)
    raise error

__all__ = (
    'hit_result_as_dataframe',
)


def hit_result_as_dataframe(hit_result: HitResult, formatted: bool = False) -> DataFrame:
    """Convert HitResult TrajectoryData rows to a pandas DataFrame.
    
    Args:
        hit_result: HitResult object containing trajectory calculation results.
                    Must contain valid HitResult.trajectory data points for conversion.
        formatted: Data format mode selector.
                  - False: Return raw numerical values as floats in default units
                  - True: Return formatted string values in preferred units
                  
    Returns:
        DataFrame with columns corresponding to TrajectoryData fields.
        
    Examples:
        Basic DataFrame conversion:
        ```python
        # Raw numerical data (default)
        df_raw = hit_result_as_dataframe(hit_result, formatted=False)
        print(df_raw['velocity'].mean())  # Average velocity
        
        # Formatted string data with units
        df_formatted = hit_result_as_dataframe(hit_result, formatted=True)
        print(df_formatted.head())  # Human-readable values
        
        # Data analysis operations
        high_velocity = df_raw[df_raw['velocity'] > 2000]
        subsonic_range = df_raw[df_raw['mach'] < 1.0]['distance'].iloc[0]
        ```
        
    Note:
        The formatted=True option is useful for generating human-readable reports and exports,
        while formatted=False is better for numerical analysis and mathematical operations.
    """
    col_names = list(TrajectoryData._fields)
    if formatted:
        trajectory = [p.formatted() for p in hit_result]
    else:
        trajectory = [p.in_def_units() for p in hit_result]
    return DataFrame(trajectory, columns=col_names)
