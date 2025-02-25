import os
import datetime
import tempfile
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


def test_close_and_reopen():
    test_db = Path("test.db")
    assert not test_db.exists(), "Test DB exists"
    cache = Cache("test.db")
    now = str(datetime.datetime.now())
    sleep(0.1)
    this_file = os.path.abspath(__file__)
    cache.set(this_file, {"now": now})
    sleep(0.1)
    cache.db.close()
    del cache
    cache = Cache("test.db")
    new_now = cache.get(this_file)["now"]
    assert test_db.exists(), "Test DB not created"
    assert now == new_now, "Invalid 'now"
    os.remove(test_db)
    assert not test_db.exists(), "Test DB not removed"


def test_second_connection():
    test_db = Path("test.db")
    assert not test_db.exists(), "Test DB exists"
    cache = Cache("test.db")
    now = str(datetime.datetime.now())
    sleep(0.1)
    this_file = os.path.abspath(__file__)
    cache.set(this_file, {"now": now})
    sleep(0.1)
    cache2 = Cache("test.db")
    new_now = cache2.get(this_file)["now"]
    assert test_db.exists(), "Test DB not created"
    assert now == new_now, "Invalid 'now"
    os.remove(test_db)
    assert not test_db.exists(), "Test DB not removed"


def test_two_writes():
    test_db = Path("test.db")
    assert not test_db.exists(), "Test DB exists"
    cache = Cache("test.db")
    now = str(datetime.datetime.now())
    sleep(0.1)
    this_file = os.path.abspath(__file__)
    cache.set(this_file, {"now": now})
    sleep(0.1)
    new_now = str(datetime.datetime.now())
    cache.set(this_file, {"now": new_now})
    sleep(0.1)
    pulled_now = cache.get(this_file)["now"]
    assert test_db.exists(), "Test DB not created"
    assert new_now == pulled_now, "Invalid 'now"
    os.remove(test_db)
    assert not test_db.exists(), "Test DB not removed"


def test_directory_hash():
    # Clean up any leftover test DB from previous runs
    test_db = Path("test_dir.db")
    if test_db.exists():
        os.remove(test_db)

    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test DB
        assert not test_db.exists(), "Test DB exists"
        cache = Cache("test_dir.db")

        # Create some test files
        (temp_path / "file1.txt").write_text("content1")
        (temp_path / "file2.txt").write_text("content2")
        subdir = temp_path / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content3")

        # Test initial cache
        now = str(datetime.datetime.now())
        cache.set(temp_path, {"now": now})
        cached_value = cache.get(temp_path)
        assert cached_value["now"] == now, "Initial cache failed"

        # Modify a file and verify cache invalidation
        sleep(0.1)  # Ensure modification time changes
        (temp_path / "file1.txt").write_text("modified content")
        cached_value = cache.get(temp_path)
        assert cached_value is None, "Cache should be invalid after file modification"

        os.remove(test_db)
        assert not test_db.exists(), "Test DB not removed"


def test_valid_types():
    test_db = Path("test.db")
    assert not test_db.exists(), "Test DB exists"
    cache = Cache("test.db")
    this_file = os.path.abspath(__file__)

    # Test a Dict
    test_dict = {"key": "value"}
    sleep(0.1)
    cache.set(this_file, test_dict)
    sleep(0.1)
    cache_value = cache.get(this_file)
    value = cache_value["key"]
    assert value == "value", "Invalid Dict value"
    assert isinstance(cache_value, dict), "Invalid Dict value type"

    # Test a List
    test_list = ["value1", "value2"]
    print("here")
    print(type(test_list))
    sleep(0.1)
    cache.set(this_file, test_list)
    sleep(0.1)
    cache_value_list = cache.get(this_file)
    print("HERE")
    print(type(cache_value_list))
    value2 = cache_value_list[1]
    assert value2 == "value2", "Invalid List value"
    assert isinstance(cache_value_list, list), "Invalid List value type"

    # Test a String
    test_string = "string_value"
    sleep(0.1)
    cache.set(this_file, test_string)
    sleep(0.1)
    cache_value_string = cache.get(this_file)
    assert cache_value_string == "string_value", "Invalid String value"
    assert isinstance(cache_value_string, str), "Invalid String value type"

    # Test an Integer
    test_int = 42
    sleep(0.1)
    cache.set(this_file, test_int)
    sleep(0.1)
    cache_value_int = cache.get(this_file)
    assert cache_value_int == 42, "Invalid Integer value"
    assert isinstance(cache_value_int, int), "Invalid Integer value type"

    # Test a Float
    test_float = 42.42
    sleep(0.1)
    cache.set(this_file, test_float)
    sleep(0.1)
    cache_value_float = cache.get(this_file)
    assert cache_value_float == 42.42, "Invalid Float value"
    assert isinstance(cache_value_float, float), "Invalid Float value type"

    # Test a Complex
    test_complex = 42 + 42j
    sleep(0.1)
    cache.set(this_file, test_complex)
    sleep(0.1)
    cache_value_complex = cache.get(this_file)
    assert cache_value_complex == 42 + 42j, "Invalid Complex value"
    assert isinstance(cache_value_complex, complex), "Invalid Complex value type"

    assert test_db.exists(), "Test DB not created"
    os.remove(test_db)
    assert not test_db.exists(), "Test DB not removed"


def test_invalid_type():
    test_db = Path("test.db")
    assert not test_db.exists(), "Test DB exists"
    cache = Cache("test.db")
    this_file = os.path.abspath(__file__)

    # Test an invalid date type
    test_date = datetime.datetime.now()
    sleep(0.1)
    error_caught = False
    # Should throw a ValueError for invalid type
    try:
        cache.set(this_file, test_date)
    except ValueError:
        error_caught = True
    assert error_caught, "Invalid Date type not caught"

    assert test_db.exists(), "Test DB not created"
    os.remove(test_db)
    assert not test_db.exists(), "Test DB not removed"
