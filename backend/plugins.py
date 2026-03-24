"""
Plugin loader and management system
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional, List
import logging

from models import PluginMetadata
from config import settings

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages plugin loading and validation"""
    
    def __init__(self, plugins_dir: str):
        self.plugins_dir = Path(plugins_dir)
        self.plugins: Dict[str, PluginMetadata] = {}
    
    async def load_plugins(self) -> int:
        """
        Load all plugins from the plugins directory.
        
        Returns:
            Number of successfully loaded plugins
        """
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory does not exist: {self.plugins_dir}")
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            return 0
        
        loaded = 0
        
        # Scan for plugin directories
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            
            metadata_file = plugin_dir / "metadata.json"
            if not metadata_file.exists():
                logger.warning(f"No metadata.json found in {plugin_dir}")
                continue
            
            try:
                plugin_meta = await self._load_plugin_metadata(metadata_file)
                
                # Validate plugin
                if await self._validate_plugin(plugin_meta, plugin_dir):
                    self.plugins[plugin_meta.id] = plugin_meta
                    loaded += 1
                    logger.info(f"✓ Loaded plugin: {plugin_meta.name} v{plugin_meta.version}")
                else:
                    logger.error(f"✗ Failed to validate plugin: {plugin_meta.id}")
                    
            except Exception as e:
                logger.error(f"Failed to load plugin from {plugin_dir}: {e}")
        
        logger.info(f"Loaded {loaded} plugins")
        return loaded
    
    async def _load_plugin_metadata(self, metadata_file: Path) -> PluginMetadata:
        """Load and parse plugin metadata JSON"""
        with open(metadata_file, 'r') as f:
            data = json.load(f)
        
        return PluginMetadata(**data)
    
    async def _validate_plugin(self, plugin: PluginMetadata, plugin_dir: Path) -> bool:
        """
        Validate plugin metadata and dependencies.
        
        Args:
            plugin: Plugin metadata
            plugin_dir: Plugin directory path
        
        Returns:
            True if plugin is valid
        """
        # Check required fields
        if not plugin.id or not plugin.name:
            logger.error(f"Plugin missing required fields: id or name")
            return False
        
        # Validate engine type
        if plugin.engine.get("type") not in ["cli", "python", "docker"]:
            logger.error(f"Invalid engine type: {plugin.engine.get('type')}")
            return False
        
        # Check binary exists for CLI plugins
        if plugin.engine.get("type") == "cli":
            binary = plugin.engine.get("binary")
            import shutil
            if binary and not shutil.which(binary):
                logger.warning(f"Binary not found in PATH: {binary}")
                # Don't fail - might be in a non-standard location or added later
        
        # Validate parser exists
        parser_file = plugin_dir / "parser.py"
        if plugin.output.get("parser") == "custom" and not parser_file.exists():
            logger.warning(f"Custom parser specified but parser.py not found")
        
        # Validate safety level
        safety_level = plugin.safety.get("level")
        if safety_level not in ["safe", "intrusive", "exploit"]:
            logger.error(f"Invalid safety level: {safety_level}")
            return False
        
        return True
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginMetadata]:
        """Get plugin by ID"""
        return self.plugins.get(plugin_id)
    
    def list_plugins(self) -> List[Dict]:
        """List all loaded plugins"""
        return [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "safety_level": p.safety.get("level"),
                "enabled": True,
                "icon": p.icon
            }
            for p in self.plugins.values()
        ]
    
    def get_plugin_schema(self, plugin_id: str) -> Optional[Dict]:
        """Get full plugin schema for UI generation"""
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            return None
        
        return {
            "id": plugin.id,
            "name": plugin.name,
            "description": plugin.description,
            "fields": [f.model_dump() for f in plugin.fields],
            "presets": plugin.presets,
            "safety": plugin.safety
        }
    
    def _interpolate(self, token: str, inputs: Dict) -> Optional[str]:
        """Interpolate variables in a token string."""
        if "{" not in token or "}" not in token:
            return token
            
        rendered = token
        matches = re.findall(r"\{(\w+)(?::([^}]+))?\}", token)
        
        for var_name, default_value in matches:
            # Handle empty default value correctly: "" from regex becomes None
            actual_default = default_value or None
            value = inputs.get(var_name, actual_default)
            
            if value is None or value == "":
                return None

            placeholder = "{" + var_name + (f":{default_value}" if default_value else "") + "}"
            rendered = rendered.replace(placeholder, str(value))
            
        return rendered

    def build_command(self, plugin_id: str, inputs: Dict) -> Optional[List[str]]:
        """
        Build command from plugin template and user inputs.
        
        Args:
            plugin_id: Plugin identifier
            inputs: User input values
        
        Returns:
            Command as list of arguments
        """
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            return None
        
        command = []

        for token in plugin.command_template:
            # Handle conditionals:
            # --if:condition:then:value
            # --if:condition:then:value:else:fallback
            if token.startswith("--if:"):
                parts = token.split(":")
                if len(parts) >= 4 and parts[2] == "then":
                    condition_var = parts[1]
                    then_value = parts[3]
                    else_value = ""
                    if len(parts) >= 6 and parts[4] == "else":
                        else_value = parts[5]

                    condition = inputs.get(condition_var, False)
                    # For booleans or non-empty existence
                    if isinstance(condition, str) and condition.lower() == "false":
                        condition = False
                        
                    raw_value = then_value if condition else else_value

                    if raw_value:
                        interpolated = self._interpolate(raw_value, inputs)
                        if interpolated:
                            command.append(interpolated)
                continue

            # Handle regular interpolation
            interpolated = self._interpolate(token, inputs)
            if interpolated:
                command.append(interpolated)

        return command


# Global plugin manager instance
plugin_manager: Optional[PluginManager] = None


async def init_plugins(plugins_dir: str) -> PluginManager:
    """Initialize plugin manager and load plugins"""
    global plugin_manager
    plugin_manager = PluginManager(plugins_dir)
    await plugin_manager.load_plugins()
    return plugin_manager


def get_plugin_manager() -> PluginManager:
    """Get plugin manager instance"""
    if plugin_manager is None:
        raise RuntimeError("Plugin manager not initialized")
    return plugin_manager
