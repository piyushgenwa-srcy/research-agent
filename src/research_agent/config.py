from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict
import os


def load_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


@dataclass
class Settings:
    serp_api_key: str = ""
    oxylab_username: str = ""
    oxylab_password: str = ""
    tmapi_token: str = ""
    ensemble_api_key: str = ""
    jungle_scout_api_key: str = ""
    jungle_scout_key_name: str = ""
    anthropic_api_key: str = ""

    @classmethod
    def load(cls, env_file: Path | None = None) -> "Settings":
        merged = dict(os.environ)
        if env_file is not None:
            merged.update({k: v for k, v in load_env_file(env_file).items() if v})
        return cls(
            serp_api_key=merged.get("SERP_API_KEY", ""),
            oxylab_username=merged.get("OXYLAB_USERNAME", ""),
            oxylab_password=merged.get("OXYLAB_PASSWORD", ""),
            tmapi_token=merged.get("TMAPI_TOKEN", ""),
            ensemble_api_key=merged.get("ENSEMBLE_API_KEY", ""),
            jungle_scout_api_key=merged.get("JUNGLE_SCOUT_API_KEY", ""),
            jungle_scout_key_name=merged.get("JUNGLE_SCOUT_KEY_NAME", ""),
            anthropic_api_key=merged.get("ANTHROPIC_API_KEY", ""),
        )

    def connector_status(self) -> Dict[str, bool]:
        return {
            "serpapi": bool(self.serp_api_key),
            "oxylabs": bool(self.oxylab_username and self.oxylab_password),
            "tmapi": bool(self.tmapi_token),
            "ensemble": bool(self.ensemble_api_key),
            "jungle_scout": bool(self.jungle_scout_api_key and self.jungle_scout_key_name),
            "anthropic": bool(self.anthropic_api_key),
        }
