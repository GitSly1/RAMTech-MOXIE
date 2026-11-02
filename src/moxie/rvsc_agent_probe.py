"""RVSC agent probe module for delivery identity check.

This module contains a function to return a delivery identity marker.
"""


def delivery_identity() -> str:
    """Return the exact delivery identity marker.

    Returns:
        str: The delivery identity marker 'RVSC_AA002_DANIEL_DELIVERED'.
    """
    return 'RVSC_AA002_DANIEL_DELIVERED'