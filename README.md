# cachehash

Cachehash is a lightweight Python library for **caching file, directory, and value data in SQLite** using fast xxhash checksums.

It is designed to memoize expensive computations by binding results to the *content hash* of files or directories, so you can skip recomputation when inputs have not changed.

---

## Features
- ⚡ **Fast hashing** with [xxhash](https://github.com/Cyan4973/xxHash)
- 📂 Hash individual files, whole directories (structure + metadata + file content), or arbitrary values
- 💾 Store and retrieve JSON-serializable Python values
- 🗄️ Backed by SQLite, easy to inspect and portable
- 🔑 Get/set by path + hash, or by hash alone
- 🧰 Simple API for integration into data pipelines or caching layers

---

## Installation

```bash
pip install cachehash
```

Requires **Python 3.9 – 3.13**.

---

## Quick Start

```python
from pathlib import Path
from cachehash.main import Cache

cache = Cache()

# Hash a file
file_hash = cache.hash_file(Path("data.csv"))
print(file_hash)

# Store computation result tied to the file
cache.set("data.csv", {"rows": 1234, "checksum": file_hash})

# Later, retrieve result if file unchanged
result = cache.get("data.csv")
print(result)
```

---

## API Overview

### `Cache`
- `hash_file(path)` → str : Hash file contents
- `hash_directory(path)` → str : Hash entire directory tree
- `hash_value(value)` → str : Hash an arbitrary string/bytes
- `get(path)` → Any | None : Retrieve value by file path + hash
- `get_by_hash(path)` → Any | None : Retrieve value by hash only
- `set(path, value, append=False)` : Store a value by file path + hash
- `set_by_hash(key, hash, value, append=False)` : Store a value for precomputed hash
- `set_value(key, value)` : Store a value by key only (not tied to content)
- `get_value(key)` : Get a value by key only

---

## Development

Clone the repo and install with dev dependencies:

```bash
git clone https://github.com/VerinFast/cachehash.git
cd cachehash
pip install -e .[dev]
```

Run tests:

```bash
pytest
```

Format code:

```bash
black src
```

---

## License

Free for **non-commercial use**. See [LICENSE](LICENSE) for details.

---

## Links
- [Homepage](https://github.com/VerinFast/cachehash)
- [Bug Tracker](https://github.com/VerinFast/cachehash/issues)
- [Source](https://github.com/VerinFast/cachehash)
