from __future__ import annotations
from typing import Any, Dict, List, Optional
import json
import os


class PluginRegistry:
    def __init__(self, plugins_dir: str) -> None:
        self.plugins_dir = plugins_dir
        self._plugins: Dict[str, Dict[str, Any]] = {}

    async def load_all(self) -> None:
        if not os.path.isdir(self.plugins_dir):
            os.makedirs(self.plugins_dir, exist_ok=True)
        for root, dirs, files in os.walk(self.plugins_dir):
            if "metadata.json" in files:
                path = os.path.join(root, "metadata.json")
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    plugin_id = meta.get("plugin", {}).get("id") or meta.get("id")
                    if not plugin_id:
                        continue
                    self._plugins[plugin_id] = meta
                except Exception:
                    continue

    def get(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        return self._plugins.get(plugin_id)

    def count(self) -> int:
        return len(self._plugins)

    def list_plugins(self, category: Optional[str] = None, safety_level: Optional[str] = None) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for meta in self._plugins.values():
            plugin_meta = meta.get("plugin", {})
            item = {
                "id": plugin_meta.get("id"),
                "name": plugin_meta.get("name"),
                "category": plugin_meta.get("category"),
                "version": plugin_meta.get("version"),
                "safety_level": (meta.get("safety", {}) or {}).get("level"),
                "description": plugin_meta.get("description"),
                "icon": plugin_meta.get("icon"),
            }
            if category and item["category"] != category:
                continue
            if safety_level and item["safety_level"] != safety_level:
                continue
            items.append(item)
        items.sort(key=lambda x: x.get("id") or "")
        return items

    def all_presets(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for meta in self._plugins.values():
            plugin_meta = meta.get("plugin", {})
            plugin_id = plugin_meta.get("id")
            if not plugin_id:
                continue
            out[plugin_id] = meta.get("presets", {})
        return out

