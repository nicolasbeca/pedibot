"""Social syndication for new guides (free channels first; X only if the operator pays per use).

Providers are optional and fail soft: a missing credential just skips that channel; a failure is
logged and never blocks publication. Texts are plain, honest, no hashtags spam, no price talk.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import httpx
from loguru import logger


@dataclass
class Post:
    title: str
    summary: str
    url: str
    lang: str

    def text(self, max_len: int = 290) -> str:
        body = f"{self.title}\n\n{self.summary}\n\n{self.url}"
        if len(body) <= max_len:
            return body
        room = max_len - len(self.title) - len(self.url) - 6
        return f"{self.title}\n\n{self.summary[: max(0, room)].rstrip()}…\n\n{self.url}"


class Provider(Protocol):
    name: str

    def post(self, p: Post) -> str | None: ...


class BlueskyProvider:
    """Free API. Needs BLUESKY_HANDLE (e.g. pedibot.bsky.social) and BLUESKY_APP_PASSWORD."""

    name = "bluesky"

    def __init__(self, handle: str, app_password: str):
        self.handle, self.app_password = handle, app_password

    def post(self, p: Post) -> str | None:
        from atproto import Client, client_utils

        c = Client()
        c.login(self.handle, self.app_password)
        tb = client_utils.TextBuilder().text(f"{p.title}\n\n{p.summary}\n\n").link(p.url, p.url)
        res = c.send_post(tb, langs=[p.lang])
        return str(res.uri)


class TelegramChannelProvider:
    """Free. Needs the ops/public bot token and a channel id (@pedibot_news or -100…)."""

    name = "telegram"

    def __init__(self, token: str, channel: str):
        self.token, self.channel = token, channel

    def post(self, p: Post) -> str | None:
        r = httpx.post(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            json={"chat_id": self.channel, "text": p.text(3900), "disable_web_page_preview": False},
            timeout=20,
        )
        r.raise_for_status()
        return str(r.json().get("result", {}).get("message_id"))


class XProvider:
    """Pay-per-use X API ($0.015/post, $0.20 with a link). Enabled only with X_POST_ENABLED=true."""

    name = "x"

    def __init__(self, api_key: str, api_secret: str, access_token: str, access_secret: str):
        self.keys = (api_key, api_secret, access_token, access_secret)

    def post(self, p: Post) -> str | None:
        import tweepy

        client = tweepy.Client(
            consumer_key=self.keys[0],
            consumer_secret=self.keys[1],
            access_token=self.keys[2],
            access_token_secret=self.keys[3],
        )
        res = client.create_tweet(text=p.text(275))
        return str(res.data.get("id")) if res and res.data else None


def providers_from_env(env: dict[str, str] | None = None) -> list[Provider]:
    e = env if env is not None else dict(os.environ)
    out: list[Provider] = []
    if e.get("BLUESKY_HANDLE") and e.get("BLUESKY_APP_PASSWORD"):
        out.append(BlueskyProvider(e["BLUESKY_HANDLE"], e["BLUESKY_APP_PASSWORD"]))
    if e.get("TELEGRAM_CHANNEL") and (
        e.get("TELEGRAM_PUBLIC_BOT_TOKEN") or e.get("TELEGRAM_BOT_TOKEN")
    ):
        out.append(
            TelegramChannelProvider(
                e.get("TELEGRAM_PUBLIC_BOT_TOKEN") or e["TELEGRAM_BOT_TOKEN"], e["TELEGRAM_CHANNEL"]
            )
        )
    if e.get("X_POST_ENABLED", "").lower() == "true" and all(
        e.get(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")
    ):
        out.append(
            XProvider(e["X_API_KEY"], e["X_API_SECRET"], e["X_ACCESS_TOKEN"], e["X_ACCESS_SECRET"])
        )
    return out


def syndicate(post: Post, providers: list[Provider]) -> dict[str, str | None]:
    results: dict[str, str | None] = {}
    for prov in providers:
        try:
            results[prov.name] = prov.post(post)
            logger.info("posted to {}: {}", prov.name, results[prov.name])
        except Exception as e:  # noqa: BLE001 — never block publication
            logger.warning("social {} failed: {}", prov.name, e)
            results[prov.name] = None
    return results
