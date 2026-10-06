import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import vk_api

from app.config import VK_TOKEN


def main():
    query = " ".join(sys.argv[1:])
    if not query:
        print('Использование: python scripts\\find_communities.py "SMM блог"')
        return

    vk = vk_api.VkApi(token=VK_TOKEN, api_version="5.199").get_api()
    resp = vk.groups.search(q=query, count=30)
    res = []
    for g in resp["items"]:
        res.append(g.get('screen_name', ''))
    print(*res, sep = ' ')


if __name__ == "__main__":
    main()