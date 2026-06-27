"""Compatibility helpers for Plotly static image export."""

from __future__ import annotations


def disable_kaleido_headers() -> None:
    """Avoid passing Plotly's default HTTP headers to Kaleido's browser.

    Plotly 6.8.0 stores ``{"X-Requested-With": "plotly.py"}`` in
    ``plotly.io.defaults.headers``. With Kaleido 1.2.0 and Choreographer 1.3.0,
    Plotly forwards that value as ``kopts["headers"]`` to ``Kaleido(...)``.
    Choreographer's Chromium implementation does not accept a ``headers``
    browser keyword argument, so image export fails before rendering.
    """
    try:
        import plotly.io as pio
    except Exception:
        return

    try:
        pio.defaults.headers = {}
    except Exception:
        pass
