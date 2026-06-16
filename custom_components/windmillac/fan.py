#fan.py

import logging
from homeassistant.components.fan import FanEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN
from .entity import WindmillFan

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)


ENTITY_DESCRIPTIONS = [
    FanEntityDescription(
        key="windmill_fan",
        name="Windmill Fan",
        icon="mdi:fan",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Windmill Fan entity."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities(
        WindmillFan(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )
