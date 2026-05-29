"""
datalibinitfootthis
createtableendstructandimportseeddata
"""

import os
import json
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.db.session import engine, SessionLocal, Base
from backend.models.user import User
from backend.models.profile import UserProfile
from backend.models.movement import Movement
from backend.models.plan import TrainingPlan
from backend.models.workout import WorkoutLog
from backend.models.knowledge import KnowledgeBase


def init_database():
    """createplace table"""
    print("correct createdatalibtable...")
    Base.metadata.create_all(bind=engine)
    print("datalibtablecreatecomplete")


def seed_movements():
    """importmovementseeddata"""
    db = SessionLocal()
    try:
        # checkYesNoalready data
        existing = db.query(Movement).count()
        if existing > 0:
            print(f"movementlibalready  {existing} itemdata, jumppassimport")
            return

        # readseeddata
        seed_file = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'movements_seed.json')
        if not os.path.exists(seed_file):
            print(f"seedfile store : {seed_file}")
            return

        with open(seed_file, 'r', encoding='utf-8') as f:
            movements_data = json.load(f)

        # importdata
        for data in movements_data:
            movement = Movement(**data)
            db.add(movement)

        db.commit()
        print(f"successimport {len(movements_data)} itemmovement")

    except Exception as e:
        db.rollback()
        print(f"importmovementdatafailed: {e}")
    finally:
        db.close()


def main():
    """mainfunction"""
    print("=" * 50)
    print("  cyber_trainer - datalibinit")
    print("=" * 50)

    # createtable
    init_database()

    # importseeddata
    seed_movements()

    print("=" * 50)
    print("  initcomplete")
    print("=" * 50)


if __name__ == "__main__":
    main()
