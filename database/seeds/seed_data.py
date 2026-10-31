"""CLI script to initialize database schema and seed development sample data."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

from app.core.database import Base, SessionLocal, engine
from app.core.seeder import seed_demo_data
import app.models  # noqa: F401


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        result = seed_demo_data(db)
        print(result["message"])


if __name__ == "__main__":
    main()

