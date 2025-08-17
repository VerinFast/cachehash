import os
import datetime
from pathlib import Path
from time import sleep

from cachehash.main import Cache


def test_set_get_value():
    test_db = Path("test.db")
    if test_db.exists():
        os.remove(test_db)
    assert not test_db.exists(), "Test DB exists"
    cache = Cache("test.db")
    now = str(datetime.datetime.now())
    sleep(0.1)
    cache.set_value("foo", {"now": now})
    sleep(0.1)
    result = cache.get("foo")
    assert result is not None, "Cache returned None"
    new_now = result["now"]

    assert test_db.exists(), "Test DB not created"
    assert now == new_now, "Invalid 'now"
    os.remove(test_db)
    assert not test_db.exists(), "Test DB not removed"
