from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


TEST_DATABASE_URL = "sqlite:///testing/test.db"

engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(bind=engine)

def get_test_db():
    return TestSessionLocal()
