from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .base import append_query, http_get


@dataclass
class EnsembleClient:
    api_key: str
    base_url: str = "https://ensembledata.com"

    def get(self, path: str, **params: str) -> Dict[str, Any]:
        url = append_query(f"{self.base_url.rstrip('/')}/{path.lstrip('/')}", {"token": self.api_key, **params})
        return http_get(url).json()

    def tiktok_keyword_search(self, keyword: str, period: int = 180, cursor: int = 0) -> Dict[str, Any]:
        return self.get("/apis/tt/keyword/search", name=keyword, period=str(period), cursor=str(cursor))

    def tiktok_keyword_search_all(self, keyword: str, period: int = 90, max_pages: int = 3) -> List[Dict[str, Any]]:
        """Paginate keyword search until max_pages or no nextCursor."""
        all_posts: List[Dict[str, Any]] = []
        cursor = 0
        for _ in range(max_pages):
            resp = self.tiktok_keyword_search(keyword, period=period, cursor=cursor)
            data = resp.get("data", {})
            posts = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            all_posts.extend(p for p in posts if isinstance(p, dict))
            next_cursor = data.get("nextCursor") if isinstance(data, dict) else None
            if not next_cursor:
                break
            cursor = next_cursor
        return all_posts

    def tiktok_hashtag_posts(self, hashtag: str, cursor: int = 0) -> Dict[str, Any]:
        """Fetch posts for a TikTok hashtag."""
        return self.get("/apis/tt/hashtag/posts", name=hashtag, cursor=str(cursor))

    def tiktok_post_comments(self, aweme_id: str, cursor: int = 0) -> Dict[str, Any]:
        """Fetch comments for a TikTok post by aweme_id."""
        return self.get("/apis/tt/post/comments", aweme_id=aweme_id, cursor=str(cursor))
