import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from dataclasses import asdict

# чтобы скрипт видел пакет app при запуске из корня проекта
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import VK_TOKEN, RAW_DATA_DIR
from app.parsers.vk import VKClient, normalize_domain


def load_known_ids(path: Path) -> set[int]:
    if not path.exists():
        return set()

    content = path.read_text(encoding="utf-8")
    lines = [line for line in content.splitlines() if line.strip()]
    needs_migration = False
    try:
        records = [json.loads(line) for line in lines]
    except json.JSONDecodeError:
        records = []
        needs_migration = True
        decoder = json.JSONDecoder()
        offset = 0
        while offset < len(content):
            while offset < len(content) and content[offset].isspace():
                offset += 1
            if offset == len(content):
                break
            record, offset = decoder.raw_decode(content, offset)
            records.append(record)

    known = set()
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("post_id"), int):
            raise ValueError(f"Invalid post record in {path}: expected an integer post_id")
        known.add(record["post_id"])
    if needs_migration:
        _write_jsonl(path, records)
    return known


def _write_jsonl(path: Path, records: list[dict]) -> None:
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
            for record in records:
                temp_file.write(json.dumps(record, ensure_ascii=False) + "\n")
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def main():
    parser = argparse.ArgumentParser(description="Collect posts from VK communities")
    parser.add_argument("domains", nargs="+", help="домены сообществ, например: vk_business")
    parser.add_argument("--max-posts", type=int, default=1000)
    args = parser.parse_args()

    out_dir = Path(RAW_DATA_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    client = VKClient(VK_TOKEN)

    for raw_domain in args.domains:
        domain = normalize_domain(raw_domain)
        path = out_dir / f"{domain}.jsonl"
        known = load_known_ids(path)
        new_count = 0
        print(f"[{domain}] уже в файле: {len(known)}")

        with path.open("a", encoding="utf-8") as f:
            for post in client.fetch_posts(domain, args.max_posts):
                if post.post_id in known:
                    continue
                f.write(json.dumps(asdict(post), ensure_ascii=False) + "\n")
                known.add(post.post_id)
                new_count += 1

        print(f"[{domain}] добавлено новых: {new_count}")


if __name__ == "__main__":
    main()