"""MailWizz routing module - maps categories to MailWizz lists."""

import json
import os
import logging

logger = logging.getLogger(__name__)

_config = None


def _load_config() -> dict:
    global _config
    if _config is None:
        config_path = os.getenv(
            "MAILWIZZ_ROUTING_CONFIG",
            os.path.join(os.path.dirname(__file__), "../../config/mailwizz_routing.json"),
        )
        with open(config_path, "r") as f:
            _config = json.load(f)
    return _config


def get_routing_info(category: str, platform: str) -> dict:
    """
    Get MailWizz routing info for a contact.

    Returns:
        dict with keys: list_id, list_name, auto_tags, template_default
    """
    config = _load_config()

    platform_config = config["platforms"].get(platform)
    if not platform_config:
        logger.warning(f"Unknown platform: {platform}, falling back to sos-expat")
        platform_config = config["platforms"]["sos-expat"]

    list_config = platform_config["lists"].get(category)
    if not list_config:
        list_config = platform_config["lists"].get("default", {
            "list_id": 1,
            "list_name": "Contacts Divers",
            "auto_tags": [],
            "template_default": None,
        })

    return {
        "list_id": list_config["list_id"],
        "list_name": list_config["list_name"],
        "auto_tags": list_config.get("auto_tags", []),
        "template_default": list_config.get("template_default"),
    }
