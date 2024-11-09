import os
import datetime

from pathlib import Path
from time import sleep

from cachehash.main import Cache


def test_basics():
    test_db = Path("test.db")
    assert not test_db.exists(), "Test DB exists"
    cache = Cache("test.db")
    now = str(datetime.datetime.now())
    sleep(0.1)
    this_file = os.path.abspath(__file__)
    cache.set(this_file, {"now": now})
    sleep(0.1)
    new_now = cache.get(this_file)["now"]

    assert test_db.exists(), "Test DB not created"
    assert now == new_now, "Invalid 'now"
    os.remove(test_db)
    assert not test_db.exists(), "Test DB not removed"
