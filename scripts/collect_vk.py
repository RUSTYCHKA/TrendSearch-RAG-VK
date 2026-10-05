import argparse
import json
import sys
from pathlib import Path
from dataclasses import asdict

# чтобы скрипт видел пакет app при запуске из корня проекта
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import VK_TOKEN, RAW_DATA_DIR
from app.parsers.vk import VKClient, normalize_domain


def load_known_ids(path: Path) -> set[int]:
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as f:
        return {json.loads(line)["post_id"] for line in f if line.strip()}


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