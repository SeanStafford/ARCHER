import os
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv
from omegaconf import OmegaConf

load_dotenv()
TYPES_PATH = Path(os.getenv("RESUME_COMPONENT_TYPES_PATH"))


class ParseConfigRegistry:
    """
    Registry for loading and caching parsing configurations.

    Parsing configs are stored in archer/contexts/templating/types/{type_name}/parse_config.yaml
    and define regex patterns and extraction rules for converting LaTeX to YAML.
    """

    def __init__(self, types_base_path: Path = None):
        """
        Initialize the parse config registry.

        Args:
            types_base_path: Base path for type directories. Defaults to
                           RESUME_COMPONENT_TYPES_PATH from environment
        """
        if types_base_path is None:
            types_base_path = TYPES_PATH

        self.types_base_path = types_base_path
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_config(self, type_name: str) -> Dict[str, Any]:
        """
        Get a parsing config by type name, loading and caching it if necessary.

        Args:
            type_name: Name of the type (e.g., 'skill_list_pipes')

        Returns:
            Dict containing parsing configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        if type_name in self._cache:
            return self._cache[type_name]

        config_path = self.get_config_path(type_name)

        if not config_path.exists():
            raise FileNotFoundError(
                f"Parse config not found for type '{type_name}' at {config_path}"
            )

        config = OmegaConf.load(config_path)
        config_dict = OmegaConf.to_container(config, resolve=True)

        self._cache[type_name] = config_dict
        return config_dict

    def get_config_path(self, type_name: str) -> Path:
        """
        Get the file path for a type's parsing config.

        Args:
            type_name: Name of the type (e.g., 'skill_list_pipes')

        Returns:
            Path to parse_config.yaml file
        """
        return self.types_base_path / type_name / "parse_config.yaml"

    def clear_cache(self):
        """Clear the parsing config cache."""
        self._cache.clear()

    def is_cached(self, type_name: str) -> bool:
        """
        Check if a parsing config is in the cache.

        Args:
            type_name: Name of the type

        Returns:
            True if cached, False otherwise
        """
        return type_name in self._cache
