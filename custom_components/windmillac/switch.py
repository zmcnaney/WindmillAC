import logging

from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import WindmillAutofadeSwitch

_LOGGER = logging.getLogger(__name__)

ENTITY_DESCRIPTIONS = [
    SwitchEntityDescription(
        key="windmill_fan_led_autofade",
        name="LED Autofade",
        icon="mdi:lightbulb-auto",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Windmill Fan switch entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        WindmillAutofadeSwitch(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )
