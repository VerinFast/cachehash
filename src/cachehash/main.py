"""cachehash: lightweight file/directory hashing + value cache on SQLite.

This module exposes a single class, `Cache`, which can:
  • Compute stable hashes for files, directories, and arbitrary values.
  • Store/retrieve JSON-serializable values keyed by either (hash,key) or by hash only.
  • Persist everything in a single SQLite table (created on first use).

Notes
-----
- SQL statements are loaded from `./sql/*.sql` next to this file unless a raw SQL
  string is provided to `query()`.
- Values are stored as JSON strings; callers pass/receive native Python types.
- Hashing uses `xxhash` (xxh32) for good speed; it is not a cryptographic hash.

"""

from __future__ import annotations

import json
import os
import sqlite3
import stat as _stat
from pathlib import Path
from typing import Any

from xxhash import xxh32 as xh

# Default database path (created on demand)
DEFAULT_DB_PATH = Path("./temp.db")


class Cache:
    """Cache of JSON-serializable values keyed by content hashes (and optional keys).

    Parameters
    ----------
    path:
        Location of the SQLite database. Created if it doesn't exist.
    table:
        SQLite table name to use. A simple schema is created on first use via
        the `make_table.sql` file in the local `sql/` folder.

    Design
    ------
    - Uses a single connection/cursor per instance (thread-unsafe by design).
    - Values are stored as JSON (text). Callers get native Python types back.
    - Hashes are derived from file bytes, directory structure+metadata+file hashes,
      or arbitrary (bytes/str) values.
    """

    # Read files in 64 KiB chunks by default
    BUF_SIZE = 64 * 1024

    def __init__(
        self, path: Path | str = DEFAULT_DB_PATH, table: str = "cachehash"
    ) -> None:
        self.db_path: Path = Path(path)
        self.table_name: str = table

        # `check_same_thread=False` allows use across threads if caller synchronizes.
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = self._dict_factory
        self.cur = self.db.cursor()

        # Ensure table exists (expects `sql/make_table.sql`).
        self.query("make_table")

    # ---------------------------------------------------------------------
    # SQLite helpers
    # ---------------------------------------------------------------------
    @staticmethod
    def _dict_factory(cursor: sqlite3.Cursor, row: sqlite3.Row) -> dict[str, Any]:
        """Return rows as dictionaries keyed by column name."""
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    def close(self) -> None:
        """Close the underlying SQLite connection.

        Safe to call multiple times. After closing, the instance shouldn't be used.
        """
        try:
            self.cur.close()
        finally:
            self.db.close()

    def __enter__(self) -> "Cache":  # context manager support
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def query(
        self,
        file_name: str,
        parameters: dict[str, Any] | None = None,
        query: str | None = None,
    ) -> sqlite3.Cursor:
        """Execute a SQL statement.

        Two modes:
        1) Provide a raw SQL `query` string containing the placeholder
           `<table_name>` which will be replaced with the configured table.
        2) Provide `file_name` (without `.sql`) pointing to a file under `./sql/`.

        Parameters
        ----------
        file_name:
            Base name of the `.sql` file in `sql/` when `query` isn't provided.
        parameters:
            Mapping of parameter names (e.g., `{":id": 1}` or `{"id": 1}`) used
            by SQLite's named placeholders style (`:id`).
        query:
            Raw SQL string (optional). If provided, `file_name` is only used for
            error context.
        """
        base_dir = Path(__file__).parent.resolve()
        sql_text: str

        if query is None:
            sql_path = base_dir / "sql" / f"{file_name}.sql"
            if not sql_path.exists():
                raise FileNotFoundError(f"Missing SQL file: {sql_path}")
            sql_text = sql_path.read_text(encoding="utf-8")
        else:
            sql_text = query

        sql_text = sql_text.replace("<table_name>", f'"{self.table_name}"')
        if parameters is not None:
            return self.cur.execute(sql_text, parameters)
        return self.cur.execute(sql_text)

    # ---------------------------------------------------------------------
    # Filesystem helpers & hashing
    # ---------------------------------------------------------------------
    @staticmethod
    def is_regular_file(path: Path) -> bool:
        """Return True if `path` is a regular file.

        This excludes sockets, FIFOs, device files, and directories.
        """
        try:
            mode = os.stat(path).st_mode
        except (FileNotFoundError, OSError):
            return False
        return _stat.S_ISREG(mode)

    def hash_file(self, fp: Path) -> str:
        """Compute a xxh32 hex digest of a file's contents.

        Raises
        ------
        ValueError
            If `fp` is not a regular file.
        """
        if not self.is_regular_file(fp):
            raise ValueError(f"Unhashable file type: {fp}")

        h = xh()
        with open(fp, "rb") as f:
            while True:
                chunk = f.read(self.BUF_SIZE)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    def hash_directory(self, directory: Path) -> str:
        """Compute a stable hash for an entire directory tree.

        The digest includes:
          - relative directory names + their modification times
          - relative file paths + file sizes + modification times
          - the content hash of each regular file (via `hash_file`)

        Non-regular files (symlinks, sockets, etc.) are ignored.
        """
        h = xh()

        # Stable order for reproducible digests
        for root, dirs, files in sorted(os.walk(directory)):
            root_path = Path(root)

            # Directories (names + mtimes)
            for d in sorted(dirs):
                dir_path = root_path / d
                try:
                    rel = dir_path.relative_to(directory)
                    st = dir_path.stat()
                except FileNotFoundError:
                    continue  # defensive against TOCTOU
                h.update(str(rel).encode())
                h.update(str(st.st_mtime).encode())

            # Files (paths + size + mtime + content digest)
            for fname in sorted(files):
                file_path = root_path / fname
                try:
                    if not self.is_regular_file(file_path):
                        continue
                    rel = file_path.relative_to(directory)
                    st = file_path.stat()
                    h.update(str(rel).encode())
                    h.update(str(st.st_size).encode())
                    h.update(str(st.st_mtime).encode())
                    h.update(self.hash_file(file_path).encode())
                except (FileNotFoundError, ValueError):
                    # Ignore disappeared or unhashable entries
                    continue

        return h.hexdigest()

    def hash_value(self, value: str | bytes) -> str:
        """Compute a xxh32 digest for an arbitrary string/bytes value."""
        h = xh()
        if isinstance(value, str):
            value = value.encode()
        h.update(value)
        return h.hexdigest()

    def get_hash(self, path: Path) -> str:
        """Return the content hash for `path` (file or directory).

        Raises
        ------
        ValueError
            If `path` does not exist or is neither a file nor a directory.
        """
        if path.is_file():
            return self.hash_file(path)
        if path.is_dir():
            return self.hash_directory(path)
        raise ValueError(f"{path} is neither a file nor a directory")

    # ---------------------------------------------------------------------
    # Public API: get / set by path or by precomputed hash
    # ---------------------------------------------------------------------
    @staticmethod
    def _coerce_path(p: str | Path) -> tuple[str, Path]:
        """Return `(as_string, as_path)` ensuring `Path` type and original string."""
        if isinstance(p, str):
            return p, Path(p)
        if isinstance(p, Path):
            return str(p), p
        raise ValueError("Invalid file_path")

    def get(self, file_path: str | Path) -> Any | None:
        """Get a cached value by *current* content hash **and** key=filepath.

        Returns
        -------
        Any | None
            The stored Python value if present and the on-disk content matches
            (hash unchanged). Otherwise `None`.
        """
        key_str, p = self._coerce_path(file_path)
        if not p.exists():
            raise ValueError(f"{p} does not exist")

        hsh = self.get_hash(p)
        row = self.query(
            "get_record_hash_key", {"hash": hsh, "key": key_str}
        ).fetchone()
        return None if row is None else json.loads(row["val"])  # type: ignore[index]

    def get_by_hash(self, file_path: str | Path) -> Any | None:
        """Get a cached value by *current* content hash only (ignores key).

        Useful when the same bytes appear at different paths.
        """
        _, p = self._coerce_path(file_path)
        if not p.exists():
            raise ValueError(f"{p} does not exist")

        hsh = self.get_hash(p)
        row = self.query("get_record", {"hash": hsh}).fetchone()
        return None if row is None else json.loads(row["val"])  # type: ignore[index]

    def set_by_hash(
        self,
        key: str,
        hash: str,
        value: Any,
        *,
        append: bool = False,
    ) -> None:
        """Upsert a value for `(hash, key)`.

        Parameters
        ----------
        key:
            A human-readable key (often a filepath). Stored alongside the hash.
        hash:
            Precomputed content hash for the underlying artifact.
        value:
            Any JSON-serializable Python value to store.
        append:
            If `True`, always insert a new row (if your schema supports history).
            If `False` (default), update the existing row for `(hash, key)` when it
            exists and the value changed; otherwise insert.
        """
        serialized = json.dumps(value)
        existing = self.query(
            "get_record_hash_key", {"hash": hash, "key": key}
        ).fetchone()
        if existing is not None and not append:
            if existing["val"] != serialized:  # type: ignore[index]
                self.query(
                    "update_record", {"key": key, "hash": hash, "value": serialized}
                )
        else:
            self.query("insert_record", {"key": key, "hash": hash, "value": serialized})
        self.db.commit()

    def set(
        self,
        file_path: str | Path,
        value: Any,
        *,
        append: bool = False,
    ) -> None:
        """Compute current hash of `file_path` and store `value` for `(hash, key)`.

        This is the common path when you want the cache tied to the actual file
        or directory contents and also scoped to the path itself.
        """
        key_str, p = self._coerce_path(file_path)
        if not p.exists():
            raise ValueError(f"{p} does not exist")

        hsh = self.get_hash(p)
        self.set_by_hash(key_str, hsh, value, append=append)

    def set_value(self, key: str, value: Any) -> None:
        """Upsert a value by *key only* using a stable sentinel hash.

        We derive a deterministic `key_hash = hash_value(key)` and store rows under
        (key, key_hash) so they work with the existing SQL (`update_record`,
        `insert_record`) that expects both `key` and `hash` parameters.

        This keeps the table schema unchanged while supporting key-only storage.
        """
        serialized = json.dumps(value)
        key_hash = self.hash_value(key)

        # Try update first; if nothing was updated, insert.
        cur = self.query(
            "update_record",
            {"key": key, "hash": key_hash, "value": serialized},
        )

        # sqlite3 returns rowcount for UPDATE; 0 means no existing row matched.
        if getattr(cur, "rowcount", 0) == 0:
            self.query(
                "insert_record",
                {"key": key, "hash": key_hash, "value": serialized},
            )

        self.db.commit()

    def get_value(self, key: str) -> Any | None:
        """Retrieve a value by *key only* (not bound to a content hash).

        This assumes your SQL provides a `get_record` variant that targets
        rows by `key` when `hash` is absent. If not, consider supplying a custom
        query here or changing your schema to include a dedicated key-only table.
        """
        row = self.query("get_record_key", {"key": key}).fetchone()
        return None if row is None else json.loads(row["val"])  # type: ignore[index]
