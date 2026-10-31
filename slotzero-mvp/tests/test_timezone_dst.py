import pytest
from datetime import datetime
import app as slotzero

def test_london_dst_gap():
    """London spring DST gap (2022‑03‑27 01:30 does not exist)."""
    local = datetime(2022, 3, 27, 1, 30)  # naive local time
    with pytest.raises(ValueError, match="does not exist"):
        slotzero.local_to_utc_strict(local, "Europe/London")

def test_newyork_dst_ambiguous():
    """New York fall DST ambiguous time (2022‑11‑06 01:30 occurs twice)."""
    local = datetime(2022, 11, 6, 1, 30)  # naive local time
    with pytest.raises(ValueError, match="ambiguous"):
        slotzero.local_to_utc_strict(local, "America/New_York")
