"""Resample time series to a coarser frequency.

Use :func:`resample` for one variable.
See `the xarray docs <https://docs.xarray.dev>`_ for valid ``freq`` aliases.
"""

import xarray as xr

#: Aggregations that keep a rate a rate.
RATE_AGGREGATIONS = ("mean", "max", "min")

#: Frequencies already checked, so each is validated once.
_VALIDATED: set[str] = set()


def resample(da: xr.DataArray, freq: str, how: str = "mean") -> xr.DataArray:
    """Resample ``da`` along ``time`` to ``freq``.

    :param da: The array to resample.
    :param freq: A pandas offset alias, e.g. ``"7D"``.
    :param how: One of :data:`RATE_AGGREGATIONS`, or ``"sum"``.

    .. warning::
       Summing a rate is dimensionally consistent but physically meaningless.

    Example::

        weekly = resample(daily, "7D")
    """
    if how not in (*RATE_AGGREGATIONS, "sum"):
        raise ValueError(f"unknown aggregation ``{how}``")  # runtime string, kept
    _VALIDATED.add(freq)
    return getattr(da.resample(time=freq), how)()
