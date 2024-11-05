import os
import datetime

from time import sleep

from cachehash.main import Cache

cache = Cache("test.db")
now = str(datetime.datetime.now())
sleep(0.1)
this_file = os.path.abspath(__file__)
cache.set(this_file, {"now": now})
sleep(0.1)
new_now = cache.get(this_file)["now"]
assert now == new_now
