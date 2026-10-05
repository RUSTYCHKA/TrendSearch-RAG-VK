import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.database import Base, engine
from app.database import models  # noqa: F401  (регистрирует модели в Base)


def main():
    Base.metadata.create_all(engine)
    print("Таблицы созданы:", ", ".join(Base.metadata.tables))


if __name__ == "__main__":
    main()