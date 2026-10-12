"""
Create testing/test.db: an empty SQLite database with the same tables as the real database.

Run it from the project root:
    python -m testing.create_test_db

Run it again whenever backend/models.py changes, to rebuild the file with the new schema.
"""
from pathlib import Path

from sqlalchemy import create_engine, inspect

from backend import models


TEST_DATABASE_PATH = Path(__file__).parent / "test.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DATABASE_PATH}"


def create_test_database():
    TEST_DATABASE_PATH.unlink(missing_ok=True)

    engine = create_engine(TEST_DATABASE_URL)
    models.Base.metadata.create_all(engine)

    table_names = inspect(engine).get_table_names()
    engine.dispose()
    return table_names


if __name__ == "__main__":
    tables = create_test_database()
    print(f"Created {TEST_DATABASE_PATH} with tables: {', '.join(tables)}")
