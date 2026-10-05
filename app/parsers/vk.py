import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator

import requests
import vk_api
from vk_api.exceptions import ApiError

API_VERSION = "5.199"
PAGE_SIZE = 100
RETRY_CODES = {6, 9, 10}
MAX_RETRIES = 5


@dataclass
class VKPost:
    group_id: int
    group_name: str
    domain: str
    post_id: int
    date: str          # ISO 8601, UTC
    title: str
    text: str
    url: str


def normalize_domain(value: str) -> str:
    value = value.strip().lstrip("@")
    for prefix in ("https://", "http://"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    for host in ("m.vk.com/", "vk.com/"):
        if value.startswith(host):
            value = value[len(host):]
    return value.split("?")[0].strip("/")

class VKClient:
    def __init__(self, token: str):
        if not token:
            raise ValueError("VK_TOKEN is empty")
        session = vk_api.VkApi(token=token, api_version=API_VERSION)
        self._vk = session.get_api()

    def _request(self, method, **params):
        for attempt in range(MAX_RETRIES):
            try:
                return method(**params)
            except ApiError as e:
                if e.code in RETRY_CODES:
                    time.sleep(2 ** attempt)
                    continue
                raise
            except requests.exceptions.RequestException:
                time.sleep(2 ** attempt)
        raise RuntimeError(f"VK request failed after {MAX_RETRIES} retries")

    def get_group(self, domain: str) -> dict:
        domain = normalize_domain(domain)
        resp = self._request(self._vk.groups.getById, group_ids=domain)
        groups = resp["groups"] if isinstance(resp, dict) else resp
        if not groups:
            raise ValueError(f"Сообщество '{domain}' не найдено")
        return groups[0]

    def fetch_posts(self, domain: str, max_posts: int = 1000) -> Iterator[VKPost]:
        domain = normalize_domain(domain)
        group = self.get_group(domain)
        group_id = group["id"]
        group_name = group["name"]

        offset = 0
        yielded = 0
        while yielded < max_posts:
            resp = self._request(
                self._vk.wall.get,
                owner_id=-group_id,
                count=PAGE_SIZE,
                offset=offset,
            )
            items = resp.get("items", [])
            if not items:
                break

            for item in items:
                post = _to_post(item, group_id, group_name, domain)
                if post is None:
                    continue
                yield post
                yielded += 1
                if yielded >= max_posts:
                    return

            offset += PAGE_SIZE
            if offset >= resp.get("count", 0):
                break


def _make_title(text: str, limit: int = 80) -> str:
    first_line = text.split("\n", 1)[0].strip()
    return first_line if len(first_line) <= limit else first_line[:limit].rstrip() + "…"


def _to_post(item: dict, group_id: int, group_name: str, domain: str) -> VKPost | None:
    if item.get("marked_as_ads"):
        return None
    text = (item.get("text") or "").strip()
    if not text:
        return None

    post_id = item["id"]
    return VKPost(
        group_id=group_id,
        group_name=group_name,
        domain=domain,
        post_id=post_id,
        date=datetime.fromtimestamp(item["date"], tz=timezone.utc).isoformat(),
        title=_make_title(text),
        text=text,
        url=f"https://vk.com/wall-{group_id}_{post_id}",
    )