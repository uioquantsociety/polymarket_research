"""
Plotting helpers, so all figures in the project look the same.

Usage:
    setup_style()
    plt.plot(...)
    save_fig("my_figure")
"""

import os

import matplotlib.pyplot as plt

# figures/ is next to src/, one folder up from this file.
FIGURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures")


def setup_style():
    """Set one clean matplotlib style for all figures."""
    plt.rcParams.update({
        "figure.figsize": (8, 4.5),
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.3,
    })


def save_fig(name):
    """Save the current figure as figures/<name>.png."""
    os.makedirs(FIGURES_DIR, exist_ok=True)
    plt.savefig(os.path.join(FIGURES_DIR, name + ".png"), dpi=300, bbox_inches="tight")
