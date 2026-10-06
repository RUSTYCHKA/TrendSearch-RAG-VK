import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vk_api.exceptions import ApiError

from app.config import VK_TOKEN
from app.parsers.vk import VKClient, normalize_domain


def main():
    domains = sys.argv[1:]
    if not domains:
        print("Использование: python scripts\\probe_vk.py domain1 domain2 ...")
        return

    client = VKClient(VK_TOKEN)
    print(f"{'сообщество':<28}{'постов':>7}{'сред.слов':>10}{'медиана':>9}{'>150 слов':>10}")

    for raw in domains:
        domain = normalize_domain(raw)
        try:
            words = [len(p.text.split()) for p in client.fetch_posts(domain, max_posts=100)]
        except ApiError as e:
            print(f"{domain:<28} пропущено: {e}")
            continue
        if not words:
            print(f"{domain:<28} нет текстовых постов")
            continue
        long_share = sum(w > 150 for w in words) / len(words)
        print(
            f"{domain:<28}{len(words):>7}{statistics.mean(words):>10.0f}"
            f"{statistics.median(words):>9.0f}{long_share:>10.0%}"
        )


if __name__ == "__main__":
    main()