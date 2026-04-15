"""
Spectral Index Analysis Module for Satellite Imagery.

This module provides tools for calculating and analyzing spectral indices
from multi-band satellite imagery. Spectral indices are mathematical
combinations of spectral bands that highlight specific surface properties
such as vegetation health, water presence, or built-up areas.
"""
from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
import xarray as xr
from matplotlib import colors

from .data_manipulation import safe_divide, get_bands, classify_array


@dataclass 
class Index:
    """
    A spectral index calculated from satellite imagery bands.

    A spectral index is a mathematical combination of spectral bands that
    highlights particular features or properties of the Earth's surface,
    such as vegetation health, water presence, or built-up areas.

    Args:
        name : str
            The name or identifier of the spectral index (e.g., 'NDVI', 'NDWI', 'NDBI').
        bands : list[str]
            List of spectral band names required to compute the index
            (e.g., ['red', 'nir'] for NDVI).
        valid_range : Tuple[float, float]
            A tuple containing the (minimum, maximum) valid values for the index.
            Values outside this range are typically considered invalid or masked.
        index_cmap: str
            The Colormap instance or registered colormap name used to map the index data to colors.
        classes : list[Tuple[str, Tuple[float, float], str]]
            List of classes for the index value. For each class we have a tuple of:
            - label: descriptive label for the classification category
            - thresholds: threshold values (min, max) used to classify the continuous index into this class.
            - color : color value (hex codes or named colors) for visualizing this class

    Examples
    --------
    >>> NDVI = Index(
    ...     name="NDVI (Normalized Difference Vegetation Index)",
    ...     bands=["red", "nir"],
    ...     valid_range=(-1.0, 1.0),
    ...     index_cmap='RdYlGn',
    ...     classes=[
    ...         ("Water/No Data",         (-1.00, 0.00), "#0000FF"),
    ...         ("Bare Soil/Rock",        ( 0.00, 0.15), "#8B4513"),
    ...         ("Sparse Vegetation",     ( 0.15, 0.33), "#DEB887"),
    ...         ("Moderate Vegetation",   ( 0.33, 0.50), "#90EE90"),
    ...         ("Dense Vegetation",      ( 0.50, 0.66), "#228B22"),
    ...         ("Very Dense Vegetation", ( 0.66, 1.00), "#006400")
    ...     ]
    ... )
    """
    name: str
    bands: list[str]
    valid_range: Tuple[float, float]
    index_cmap: str
    classes: list[Tuple[str, Tuple[float, float], str]]


class ComputedIndex:
    """
    Store and analyze computed spectral index values from satellite imagery.

    This class encapsulates the results of computing a spectral index on
    satellite image bands. It provides functionality for statistical analysis,
    classification, and visualization of the index values.

    Attributes:
        index : Index
            Reference to the index definition used for classification and labeling.
        values : np.ndarray
            The index values clipped to the valid range defined by the index.
        classified_data : np.ndarray
            Integer array where each pixel is assigned a class based on the
            index's threshold values.

    Examples:
    >>> computed = compute_ndvi(data)
    >>> stats = computed.get_statistics()
    >>> print(f"Mean NDVI: {stats['mean']:.3f}")
    """
    
    def __init__(self, index: Index, values: np.ndarray):
        """
        Initialize a ComputedIndex with index metadata and raw values.

        The raw values are automatically clipped to the index's valid range
        and classified according to the index's defined thresholds.

        Args:
            index : Index
                The index definition containing valid_range, thresholds, labels,
                and colors for classification and visualization.
            values : np.ndarray
                Raw computed index values. Can contain NaN or infinite values,
                which will be preserved for nodata handling. Shape should be
                (height, width) matching the source imagery dimensions.
        """
        self.index = index

        min_v, max_v = index.valid_range
        self.values =  np.clip(values, min_v, max_v)

        self.class_thresholds = []
        self.class_labels = []
        self.class_colors = []
        for label, (min_t, max_t), color in index.classes:
            if not self.class_thresholds:
                self.class_thresholds.append(min_t)
            elif min_t != self.class_thresholds[-1]:
                raise ValueError("The classes thresholds should be contigous")

            self.class_thresholds.append(max_t)
            self.class_labels.append(label)
            self.class_colors.append(color)

        self.class_values = classify_array(self.values, self.class_thresholds)

    def get_classified_data(self) -> np.ndarray:
        """
        Grid data with discrete classes based on thresholds.
        Returns:
            np.ndarray: Integer array with class values (0 to n_classes-1)
        """
        return self.class_values

    def get_statistics(self) -> Dict[str, float]:
        """
        Calculate descriptive statistics for the index values.

        Computes common statistical measures on finite (non-NaN, non-infinite)
        values only. Useful for summarizing the distribution of index values
        across the image.

        Returns:
            Dict[str, float]
                Dictionary containing the following statistics:
                - 'min' : float - Minimum value
                - 'max' : float - Maximum value
                - 'mean' : float - Arithmetic mean
                - 'median' : float - Median (50th percentile)
                - 'std' : float - Standard deviation
                - 'count' : int - Number of valid (finite) pixels
                - 'percentile_5' : float - 5th percentile value
                - 'percentile_95' : float - 95th percentile value

        Examples:
        >>> stats = computed_index.get_statistics()
        >>> print(f"NDVI range: [{stats['min']:.2f}, {stats['max']:.2f}]")
        >>> print(f"Mean ± Std: {stats['mean']:.2f} ± {stats['std']:.2f}")
        """
        valid_data = self.values[np.isfinite(self.values)]
        
        if len(valid_data) == 0:
            return {k: np.nan for k in ["min", "max", "mean", "median", "std", "count"]}
        
        return {
            "min": float(np.nanmin(valid_data)),
            "max": float(np.nanmax(valid_data)),
            "mean": float(np.nanmean(valid_data)),
            "median": float(np.nanmedian(valid_data)),
            "std": float(np.nanstd(valid_data)),
            "count": int(np.sum(np.isfinite(valid_data))),
            "percentile_5": float(np.nanpercentile(valid_data, 5)),
            "percentile_95": float(np.nanpercentile(valid_data, 95)),
        }

    def _get_class_counts(self) -> Dict[str, int]:
        """
        Get the pixel count for each classification category.

        Counts the number of pixels assigned to each class based on the
        classified data. Only finite values are considered.

        Returns:
            Dict[str, int]
                Dictionary mapping class labels (from index.labels) to the
                number of pixels in that class. Classes with zero pixels
                may be omitted from the result.

        Examples:
        >>> counts = computed_index.get_class_counts()
        >>> for label, count in counts.items():
        ...     print(f"{label}: {count:,} pixels")
        Dense Vegetation: 45,230 pixels
        Moderate Vegetation: 28,150 pixels
        Sparse Vegetation: 12,890 pixels
        """
        unique, counts = np.unique(self.class_values[np.isfinite(self.class_values)], return_counts=True)
        return {
            self.class_labels[int(u)]: int(c)
            for u, c in zip(unique, counts) 
            if int(u) < len(self.class_labels)
        }
    
    def get_class_percentages(self) -> Dict[str, float]:
        """
        Get the percentage of pixels in each classification category.

        Calculates the proportion of valid pixels belonging to each class,
        expressed as a percentage (0-100).

        Returns:
            Dict[str, float]
                Dictionary mapping class labels to their percentage of total
                valid pixels. Values sum to 100.0 (approximately, due to
                floating-point precision). If no valid pixels exist, all
                percentages will be 0.0.

        Examples:
        >>> percentages = computed_index.get_class_percentages()
        >>> for label, pct in percentages.items():
        ...     print(f"{label}: {pct:.1f}%")
        Dense Vegetation: 52.3%
        Moderate Vegetation: 32.6%
        Sparse Vegetation: 15.1%
        """
        counts = self._get_class_counts()
        total = sum(counts.values())
        if total == 0:
            return {label: 0.0 for label in self.class_labels}
        return {label: (count / total) * 100 for label, count in counts.items()}
    
    def class_to_rgba(self) -> np.ndarray:
        """
        Convert classified index data to an RGBA array for visualization.

        Maps each classification category to its corresponding color defined
        in the index, producing a 4-channel image suitable for display or
        export. Nodata pixels are rendered as fully transparent.

        Returns:
            np.ndarray
                RGBA array with shape (height, width, 4) and dtype float32.
                Values are in the range [0.0, 1.0] for each channel:
                - Channel 0: Red
                - Channel 1: Green
                - Channel 2: Blue
                - Channel 3: Alpha (transparency, 0=transparent, 1=opaque)

        Examples:
        >>> rgba = computed_index.class_to_rgba()
        >>> plt.imshow(rgba)
        """
        rgba = np.zeros((*self.class_values.shape, 4), dtype=np.float32)
        for i, color in enumerate(self.class_colors):
            mask = self.class_values == i
            rgba[mask] = colors.to_rgba(color)
        
        # Set nodata to transparent
        nodata_mask = ~np.isfinite(self.class_values) | (self.class_values < 0)
        rgba[nodata_mask] = [0, 0, 0, 0]
        
        return rgba


NDVI = Index(
    name="NDVI (Normalized Difference Vegetation Index)",
    bands=["red", "nir"],
    valid_range=(-1.0, 1.0),
    index_cmap='RdYlGn',
    classes=[
        ("Water/No Data",         (-1.00, 0.00), "#0000FF"),
        ("Bare Soil/Rock",        ( 0.00, 0.15), "#8B4513"),
        ("Sparse Vegetation",     ( 0.15, 0.33), "#DEB887"),
        ("Moderate Vegetation",   ( 0.33, 0.50), "#90EE90"),
        ("Dense Vegetation",      ( 0.50, 0.66), "#228B22"),
        ("Very Dense Vegetation", ( 0.66, 1.00), "#006400")
    ]
)


def compute_NDVI(data: xr.DataArray) -> ComputedIndex:
    """
    Compute Normalized Difference Vegetation Index (NDVI).
    
    NDVI = (NIR - Red) / (NIR + Red)
    
    The most widely used vegetation index for assessing vegetation
    greenness, vigor, and photosynthetic capacity. Values range from
    -1 to 1, with typical healthy vegetation showing values between
    0.2 and 0.8.
    
    Reference: “Monitoring vegetation systems in the great plains with ERTS.”
    Rouse, John Wilson, Robert H. Haas, John A. Schell and D. W. Deering. (1973)
    
    Args:
        data : xr.DataArray array containing the 'red' and 'nir' bands.
    
    Returns:
        ComputedIndex: the computed NDVI index
    """
    bands = get_bands(data, NDVI.bands)
    return ComputedIndex(
        NDVI, safe_divide(bands['nir'] - bands['red'], bands['nir'] + bands['red'])
    )


NDWI = Index(
    name="NDWI (Normalized Difference Water Index)",
    bands=["green", "nir"],
    valid_range=(-1.0, 1.0),
    index_cmap='RdBu_r',
    classes=[
        ("Dry Vegetation",    (-1.0, -0.3), "#228B22"),
        ("Low Moisture",      (-0.3,  0.0), "#DEB887"),
        ("Moderate Moisture", ( 0.0,  0.2), "#87CEEB"),
        ("Wet/Shallow Water", ( 0.2,  0.4), "#4169E1"),
        ("Water",             ( 0.4,  1.0), "#00008B"),
    ],
)


def compute_NDWI(data: xr.DataArray) -> ComputedIndex:
    """
    Compute Normalized Difference Water Index (NDWI).

    NDWI = (Green - NIR) / (Green + NIR)

    Used for delineating open water features and enhancing their presence
    in remotely sensed digital imagery. Water bodies typically show
    positive values, while vegetation and soil show negative values.

    Reference: "The use of the Normalized Difference Water Index (NDWI) in the
    delineation of open water features". McFeeters, S.K. (1996)

    Args:
        data : xr.DataArray array containing the 'green' and 'nir' bands.

    Returns:
        ComputedIndex: the computed NDWI index
    """
    bands = get_bands(data, NDWI.bands)
    return ComputedIndex(
        NDWI, safe_divide(bands['green'] - bands['nir'], bands['green'] + bands['nir'])
    )


NBR = Index(
    name="NBR (Normalized Burn Ratio)",
    bands=["nir", "swir22"],
    valid_range=(-1.0, 1.0),
    index_cmap='RdYlGn',
    classes=[
        ("Active Burn/Bare",         (-1.0, -0.2 ), "#8B0000"),
        ("Recently Burned",          (-0.2,  0.0 ), "#FF4500"),
        ("Low Vegetation/Bare Soil", ( 0.0,  0.1 ), "#DEB887"),
        ("Sparse Vegetation",        ( 0.1,  0.27), "#FFFF00"),
        ("Moderate Vegetation",      ( 0.27, 0.44), "#90EE90"),
        ("Healthy Vegetation",       ( 0.44, 1.0 ), "#006400"),
    ],
)


def compute_NBR(data: xr.DataArray) -> ComputedIndex:
    """
    Compute Normalized Burn Ratio (NBR).

    NBR = (NIR - SWIR2) / (NIR + SWIR2)

    Used for identifying burned areas and assessing burn severity.
    Healthy vegetation shows high NBR values, while recently burned
    areas show low or negative values. Often used in differenced form
    (dNBR = pre-fire NBR - post-fire NBR) for burn severity mapping.

    Reference: "FireMon: Fire Effects Monitoring and Inventory System"
    Key, C.H., and Benson, N.C. (2006)

    Args:
        data : xr.DataArray array containing the 'nir' and 'swir22' bands.

    Returns:
        ComputedIndex: the computed NBR index
    """
    bands = get_bands(data, NBR.bands)
    return ComputedIndex(
        NBR, safe_divide(bands['nir'] - bands['swir22'], bands['nir'] + bands['swir22'])
    )


dNBR = Index(
    name="dNBR (differenced Normalized Burn Ratio)",
    bands=["nir", "swir22"],
    valid_range=(-2.0, 2.0),
    index_cmap='RdYlGn_r',
    classes=[
        ("Enhanced Regrowth (High)", (-2.00, -0.25), "#2166ac"),
        ("Enhanced Regrowth (Low)",  (-0.25, -0.10), "#67a9cf"),
        ("Unburned",                 (-0.10,  0.10), "#d1e5f0"),
        ("Low Severity",             ( 0.10,  0.27), "#f7f7f7"),
        ("Moderate-Low Severity",    ( 0.27,  0.44), "#fddbc7"),
        ("Moderate-High Severity",   ( 0.44,  0.66), "#ef8a62"),
        ("High Severity",            ( 0.66,  2.00), "#b2182b"),
    ],
)


def compute_dNBR(nmr_before: ComputedIndex, nmr_after: ComputedIndex):
    """
    Compute differenced NBR (dNBR) for burn severity assessment.

    dNBR = pre-fire NBR - post-fire NBR

    Higher dNBR values indicate more severe burns
    """
    return ComputedIndex(
        dNBR, nmr_before.values - nmr_after.values
    )