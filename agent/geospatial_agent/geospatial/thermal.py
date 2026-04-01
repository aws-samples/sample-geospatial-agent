import xarray as xr
import numpy as np


def convert_lwir11_to_celsius(data: xr.DataArray) -> np.ndarray:
    """Convert the LandSat 'lwir11' band from the provided xarray DataArray
    from Kelvin to Celsius.

    Args:
        data : xr.DataArray
            A multi-band xarray DataArray that must contain a 'band' dimension
            with a 'lwir11' coordinate.
    
    Returns:
        np.ndarray
            A NumPy array of temperature values converted to degrees Celsius.
    """
    thermal_band = data.sel(band='lwir11').values.squeeze()
    return thermal_band - 273.15
