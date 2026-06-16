import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_TOKEN,
    BASE_URL,
    PLATFORMS_BY_PRODUCT,
    PRODUCT_AC,
)
from .blynk_service import BlynkService
from .coordinator import WindmillDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Windmill AC / Fan from a config entry."""
    _LOGGER.debug("Setting up Windmill config entry")

    server = BASE_URL
    token = entry.data[CONF_TOKEN]

    blynk_service = BlynkService(hass, server, token)
    product_type = await blynk_service.async_get_product_type()
    _LOGGER.debug(f"Detected Windmill product type: {product_type}")

    coordinator = WindmillDataUpdateCoordinator(hass, blynk_service)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "product_type": product_type,
    }

    await coordinator.async_config_entry_first_refresh()

    platforms = PLATFORMS_BY_PRODUCT.get(product_type, PLATFORMS_BY_PRODUCT[PRODUCT_AC])
    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    product_type = entry_data.get("product_type", PRODUCT_AC)
    platforms = PLATFORMS_BY_PRODUCT.get(product_type, PLATFORMS_BY_PRODUCT[PRODUCT_AC])

    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    return unload_ok
