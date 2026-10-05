import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.config import RAW_DATA_DIR
from app.database.database import SessionLocal
from app.database.models import Post, Source

BATCH = 500


def read_records(path: Path) -> list[dict]:
    content = path.read_text(encoding="utf-8")
    lines = [line for line in content.splitlines() if line.strip()]
    try:
        rows = [json.loads(line) for line in lines]
    except json.JSONDecodeError:
        rows = []
        decoder = json.JSONDecoder()
        offset = 0
        while offset < len(content):
            while offset < len(content) and content[offset].isspace():
                offset += 1
            if offset == len(content):
                break
            row, offset = decoder.raw_decode(content, offset)
            rows.append(row)

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"Invalid post record in {path}: expected a JSON object")
    return rows


def get_or_create_source(session, row: dict) -> Source:
    source = session.scalar(select(Source).where(Source.vk_id == row["group_id"]))
    if source is None:
        source = Source(
            name=row["group_name"],
            vk_id=row["group_id"],
            domain=row["domain"],
            url=f"https://vk.com/{row['domain']}",
        )
        session.add(source)
        session.flush()
    return source


def load_file(session, path: Path) -> tuple[int, int]:
    rows = read_records(path)
    if not rows:
        return 0, 0

    source = get_or_create_source(session, rows[0])
    inserted = 0

    for i in range(0, len(rows), BATCH):
        batch = [
            {
                "source_id": source.id,
                "vk_post_id": r["post_id"],
                "title": r["title"],
                "text": r["text"],
                "url": r["url"],
                "published_at": datetime.fromisoformat(r["date"]),
                "content_hash": hashlib.sha256(r["text"].encode("utf-8")).hexdigest(),
            }
            for r in rows[i : i + BATCH]
        ]
        stmt = insert(Post).values(batch).on_conflict_do_nothing(
            index_elements=["source_id", "vk_post_id"]
        )
        result = session.execute(stmt)
        inserted += result.rowcount

    return len(rows), inserted


def main():
    with SessionLocal() as session:
        for path in sorted(Path(RAW_DATA_DIR).glob("*.jsonl")):
            total, inserted = load_file(session, path)
            session.commit()
            print(f"[{path.stem}] в файле: {total}, добавлено в БД: {inserted}")


if __name__ == "__main__":
    main()