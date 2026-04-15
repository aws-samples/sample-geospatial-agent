from typing import Optional, Union
from pathlib import Path

from shapely.geometry import Polygon
from numpy.typing import ArrayLike
import matplotlib.pyplot as plt
from matplotlib.colors import Colormap


def generate_overlay(
        overlay_data: ArrayLike,
        overlay_path: Union[str, Path],
        coordinates: list[list[float]],
        cmap: Union[str, Colormap] = 'RdYlGn',
        vmin: Optional[float] = None,
        vmax: Optional[float] = None
) -> tuple[Union[str, Path], list[list[float]]]:
    """
    Generate a PNG image overlay suitable for use with Folium maps.

    Creates a matplotlib figure from the provided 2D data array, saves it as a
    transparent PNG image, and returns the geographic bounds in Folium's expected
    format for use with `folium.raster_layers.ImageOverlay`.

    Parameters
    ----------
    overlay_data : ArrayLike
        2D array-like data to be visualized as an image overlay.
    overlay_path : Union[str, Path]
        File path where the generated PNG image will be saved.
    coordinates : list[list[float]]
        list of [longitude, latitude] coordinate pairs defining the polygon
        boundary. Used to calculate the bounding box for the overlay.
    cmap : Union[str, Colormap], optional
        Matplotlib colormap name or Colormap instance (default: 'RdYlGn').
    vmin : Optional[float], optional
        Minimum data value for colormap normalization. If None, the minimum
        value of `overlay_data` is used (default: None).
    vmax : Optional[float], optional
        Maximum data value for colormap normalization. If None, the maximum
        value of `overlay_data` is used (default: None).

    Returns
    -------
    tuple[Union[str, Path], list[list[float]]]
        A tuple containing:
        - The overlay file path (same as input `overlay_path`).
        - Geographic bounds in Folium format: ``[[south, west], [north, east]]``.
    """
    west, south, east, north = Polygon(coordinates).bounds

    # Calculate the aspect ratio of the bounding box
    width = east - west
    height = north - south
    aspect_ratio = width / height

    # Set figure size to match the bounding box proportions
    base_size = 10
    if aspect_ratio >= 1:
        fig_width = base_size
        fig_height = base_size / aspect_ratio
    else:
        fig_height = base_size
        fig_width = base_size * aspect_ratio

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    ax.imshow(overlay_data, cmap=cmap, vmin=vmin, vmax=vmax, aspect='auto')
    ax.axis('off')

    # Save as PNG with transparency
    plt.savefig(overlay_path, dpi=150, bbox_inches='tight', pad_inches=0, transparent=True)
    plt.close(fig)

    # Folium bounds format: [[south, west], [north, east]]
    return overlay_path, [[south, west], [north, east]]
