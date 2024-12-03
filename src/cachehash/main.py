import json
import sqlite3

from pathlib import Path
from typing import Union

from xxhash import xxh32 as xh

default_path = Path('./temp.db')


class Cache:
    # BUF_SIZE is totally arbitrary
    BUF_SIZE = 65536  # default 64kb chunks

    def __init__(self, path: Path = default_path, table: str = "cachehash"):
        self.db_path = path
        self.db = sqlite3.connect(path)

        def dict_factory(cursor, row):
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d

        self.db.row_factory = dict_factory
        self.cur = self.db.cursor()
        self.table_name = table
        self.query("make_table")

    def query(self, file_name: str, parameters=None):
        cur_path = Path(__file__).parent.resolve().absolute()
        path = Path(f'{cur_path}/sql/{file_name}.sql')
        with open(path, "r") as f:
            query = f.read()
            query = query.replace("<table_name>", f'"{self.table_name}"')
            if parameters is not None:
                return self.cur.execute(query, parameters)
            else:
                return self.cur.execute(query)

    def hash_file(self, fp: Path) -> str:
        h = xh()
        with open(fp, 'rb') as f:
            while True:
                data = f.read(self.BUF_SIZE)
                if not data:
                    break
                h.update(data)
        return h.hexdigest()

    def get(
            self, file_path: Union[str, Path],
            only_valid: bool = True
            ) -> Union[str, None]:
        fp: str
        if type(file_path) is str:
            fp = file_path
            file_path = Path(file_path)
        else:
            fp = str(file_path)

        if not file_path.exists():
            raise ValueError(f"{file_path} does not exist")
        hash = self.hash_file(file_path)
        row = self.query(
            'get_record',
            {
                "key": fp,
            }).fetchone()
        if row is None:
            return None
        else:
            if row["hash"] == hash or not only_valid:
                return json.loads(row["val"])
            else:
                return None

    def set(self, file_path: Union[str, Path], values: dict):
        fp: str
        if type(file_path) is str:
            fp = file_path
            file_path = Path(file_path)
        elif type(file_path) is Path:
            fp = str(file_path)
        else:
            raise ValueError("Invalid file_path")
        if not file_path.exists():
            raise ValueError(f"{file_path} does not exist")

        if isinstance(values, dict):
            values = json.dumps(values, indent=4)
        else:
            raise ValueError("Must pass values as a dict")

        hash = self.hash_file(file_path)
        self.query(
            "insert_record",
            {
                "key": fp,
                "hash": str(hash),
                "value": values,
            }
        )
