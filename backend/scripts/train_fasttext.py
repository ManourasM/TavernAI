"""Placeholder script for training FastText model from NLP samples.

Reads samples from the database and prints basic training stats.
"""

from collections import Counter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import NLPTrainingSample


def main() -> None:
    """Load samples and print training stats (placeholder)."""
    # TODO: Wire in proper database URL/config
    db_url = "sqlite:///data/default.db"
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        samples = session.query(NLPTrainingSample).all()
        total = len(samples)
        raw_lengths = [len(s.raw_text) for s in samples]
        user_counts = Counter(s.corrected_by_user_id for s in samples)

        print("FastText training placeholder")
        print(f"Samples: {total}")
        if raw_lengths:
            print(f"Avg length: {sum(raw_lengths) / len(raw_lengths):.2f}")
            print(f"Min length: {min(raw_lengths)}")
            print(f"Max length: {max(raw_lengths)}")
        if user_counts:
            print(f"Unique users: {len(user_counts)}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
