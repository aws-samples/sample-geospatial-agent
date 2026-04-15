from typing import List
import numpy as np
import xarray as xr


def safe_divide(
    numerator: np.ndarray, 
    denominator: np.ndarray, 
    fill_value: float = np.nan
) -> np.ndarray:
    """
    Perform safe division, handling division by zero.
    """
    # Ignore errors for divisions containing nan values or zero denominators,
    # we will get (inf, -inf, nan) values in these cases instead of an error.
    with np.errstate(divide='ignore', invalid='ignore'):
        result = numerator / denominator
        # Fill all cells with (inf, -inf, nan) with fill_value
        result[~np.isfinite(result)] = fill_value
    return result


def get_bands(
    data: xr.DataArray, 
    band_names: list[str], 
) -> dict[str, np.ndarray]:
    """
    Extract a band as numpy array.
    
    Args:
        data : xr.DataArray
            Input stacked data
        bands : list[str]
            Standard band names (e.g., ['red', 'nir'])
        
    Returns:
        dict[str, np.ndarray]: band name mapped to its band data as float32 array
    """
    available_bands = set(data.coords["band"].values)
    if not set(band_names).issubset(available_bands):
        raise ValueError(f"Bands {band_names} not found in data. Available bands: {available_bands}")

    bands = {}
    for band_name in band_names:
        band_data = data.sel(band=band_name).values.astype(np.float32)
    
        # Handle potential scaling (Sentinel-2 L2A is typically 0-10000)
        if np.nanmax(band_data) > 100:
            band_data = band_data / 10000.0
        
        bands[band_name] = band_data
    
    return bands


def classify_array(
    data: np.ndarray,
    thresholds: List[float]
) -> np.ndarray:
    """
    Classify array values into discrete classes based on thresholds.
    
    Args:
        data: np.ndarray input array to classify
        thresholds: list of threshold values defining class boundaries
    
    Returns:
        np.ndarray: Integer array with class values (0 to n_classes-1)
    """
    min_val, max_val = data.min(), data.max()
    lower_threshold, upper_threshold = thresholds[0], thresholds[-1] 
    if lower_threshold > min_val:
        raise ValueError(f"The lower threshold ({lower_threshold}) is bigger than some of the data values ({min_val}).")
    if upper_threshold < max_val:
        raise ValueError(f"The upper threshold ({upper_threshold}) is smaller than some of the data values ({max_val}).")
    
    class_values = np.full(data.shape, np.nan, dtype=np.float32)
    for i in range(len(thresholds) - 1):
        mask = (data >= thresholds[i]) & (data <= thresholds[i + 1])
        class_values[mask] = i
    
    return class_values
