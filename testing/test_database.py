from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base


TEST_DATABASE_URL = "sqlite:///testing/test.db"

engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(bind=engine)

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

def get_test_db():
    return TestSessionLocal()
