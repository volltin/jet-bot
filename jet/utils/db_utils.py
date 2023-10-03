import os
import contextlib
from pathlib import Path

import dotenv
from sqlitedict import SqliteDict

dotenv.load_dotenv()


def get_db_path():
    db_name = os.getenv("DB_NAME", "data")
    db_path = Path(__file__) / ".." / ".." / "data" / f"{db_name}.sqlite"
    db_path = db_path.resolve()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


@contextlib.contextmanager
def get_db():
    db_path = get_db_path()
    db = SqliteDict(db_path, autocommit=False, flag="c")
    yield db
    db.close()


def encode_key_db(username, key):
    return f"{username}::{key}"


def read_user_state(username, key=None, default=None):
    with get_db() as db:
        key_db = encode_key_db(username, key)
        return db.get(key_db, default)


def update_user_state(username, key, value):
    with get_db() as db:
        key_db = encode_key_db(username, key)
        db[key_db] = value
        db.commit()
