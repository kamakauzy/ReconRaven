"""
Bearing Map Visualization Module
Creates compass plots showing signal bearings.
"""

import matplotlib as mpl
import numpy as np


mpl.use('Agg')  # Non-interactive backend
import base64
import io
from typing import Any, Optional

import matplotlib.pyplot as plt


class BearingMapper:
    """Creates visual representations of signal bearings."""

    def __init__(self, config: Optional[dict] = None):
        """Initialize bearing mapper."""
        self.config = config or {}
        self.figure_size = (8, 8)

    def create_compass_plot(
        self,
        bearings: list[dict[str, Any]],
        title: str = 'Signal Bearings',
        save_path: Optional[str] = None,
    ) -> Optional[str]:
        """Create a compass plot showing signal bearings.

        Args:
            bearings: List of bearing dictionaries with 'bearing_degrees', 'frequency_hz', 'confidence'
            title: Plot title
            save_path: Optional path to save figure

        Returns:
            Path to saved figure or base64 encoded image
        """
        try:
            fig, ax = plt.subplots(figsize=self.figure_size, subplot_kw={'projection': 'polar'})

            # Set up polar plot (0° = North, clockwise)
            ax.set_theta_zero_location('N')
            ax.set_theta_direction(-1)  # Clockwise

            # Plot each bearing
            for bearing_data in bearings:
                bearing_deg = bearing_data.get('bearing_degrees', 0)
                confidence = bearing_data.get('confidence', 1.0)
                freq_mhz = bearing_data.get('frequency_hz', 0) / 1e6

                # Convert to radians
                bearing_rad = np.deg2rad(bearing_deg)

                # Plot arrow showing bearing
                arrow_length = confidence  # Length proportional to confidence
                ax.arrow(
                    bearing_rad,
                    0,
                    0,
                    arrow_length,
                    head_width=0.15,
                    head_length=0.1,
                    fc='red',
                    ec='darkred',
                    linewidth=2,
                    alpha=0.7,
                )

                # Add label with frequency
                label_distance = arrow_length + 0.15
                ax.text(
                    bearing_rad,
                    label_distance,
                    f'{freq_mhz:.2f} MHz\n{bearing_deg:.0f}°',
                    ha='center',
                    va='center',
                    fontsize=9,
                    bbox={'boxstyle': 'round', 'facecolor': 'wheat', 'alpha': 0.7},
                )

            # Customize plot
            ax.set_ylim(0, 1.3)
            ax.set_title(title, pad=20, fontsize=14, fontweight='bold')
            ax.grid(True, linestyle='--', alpha=0.5)

            # Add cardinal directions
            ax.set_xticks(np.deg2rad([0, 45, 90, 135, 180, 225, 270, 315]))
            ax.set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])

            # Save or return base64
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
                plt.close(fig)
                self.log_info(f'Compass plot saved to {save_path}')
                return save_path
            # Return as base64 for embedding in HTML
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            return f'data:image/png;base64,{img_base64}'

        except Exception as e:
            self.log_error(f'Error creating compass plot: {e}')
            return None

    def create_spectrum_plot(
        self,
        frequencies: np.ndarray,
        power_dbm: np.ndarray,
        title: str = 'Spectrum',
        save_path: Optional[str] = None,
    ) -> Optional[str]:
        """Create a spectrum plot.

        Args:
            frequencies: Frequency array in Hz
            power_dbm: Power array in dBm
            title: Plot title
            save_path: Optional path to save

        Returns:
            Path to saved figure or base64 encoded image
        """
        try:
            fig, ax = plt.subplots(figsize=(12, 6))

            # Convert frequencies to MHz for display
            freq_mhz = frequencies / 1e6

            # Plot spectrum
            ax.plot(freq_mhz, power_dbm, linewidth=1, color='blue')
            ax.fill_between(freq_mhz, power_dbm, -120, alpha=0.3)

            # Customize
            ax.set_xlabel('Frequency (MHz)', fontsize=12)
            ax.set_ylabel('Power (dBm)', fontsize=12)
            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.grid(True, linestyle='--', alpha=0.5)
            ax.set_ylim(-120, max(power_dbm) + 10)

            # Save or return base64
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
                plt.close(fig)
                return save_path
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            return f'data:image/png;base64,{img_base64}'

        except Exception as e:
            self.log_error(f'Error creating spectrum plot: {e}')
            return None

    def create_waterfall(
        self,
        data: np.ndarray,
        extent: list[float],
        title: str = 'Waterfall',
        save_path: Optional[str] = None,
    ) -> Optional[str]:
        """Create a waterfall plot.

        Args:
            data: 2D array of power data [time, frequency]
            extent: [freq_start, freq_end, time_start, time_end]
            title: Plot title
            save_path: Optional path to save

        Returns:
            Path to saved figure or base64 encoded image
        """
        try:
            fig, ax = plt.subplots(figsize=(12, 8))

            # Plot waterfall
            im = ax.imshow(
                data,
                aspect='auto',
                extent=extent,
                origin='lower',
                cmap='viridis',
                interpolation='bilinear',
            )

            # Add colorbar
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label('Power (dBm)', fontsize=12)

            # Customize
            ax.set_xlabel('Frequency (MHz)', fontsize=12)
            ax.set_ylabel('Time (s)', fontsize=12)
            ax.set_title(title, fontsize=14, fontweight='bold')

            # Save or return base64
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
                plt.close(fig)
                return save_path
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            return f'data:image/png;base64,{img_base64}'

        except Exception as e:
            self.log_error(f'Error creating waterfall plot: {e}')
            return None
