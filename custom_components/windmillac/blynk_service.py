import json
import logging
from urllib.parse import urlencode

import aiohttp
from homeassistant.components.climate.const import HVACMode, ClimateEntityFeature
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import PRODUCT_AC, PRODUCT_FAN

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)


class BlynkService:
    def __init__(self, hass, server, token):
        self.hass = hass
        self.server = server
        self.token = token
        self._product_type = None
        self._session = async_get_clientsession(hass)
        # Mapping of string values to pin values
        self.fan_speed_mapping = {
            "Auto": "0",
            "Low": "1",
            "Medium": "2",
            "High": "3"
        }
        self.mode_mapping = {
            HVACMode.AUTO: "2",
            HVACMode.COOL: "1",
            HVACMode.FAN_ONLY: "0"
        }
        self.power_mapping = {
            False: 0,
            True: 1
        }

    def _get_request_url(self, endpoint, params):
        query = urlencode(params)
        return f"{self.server}/{endpoint}?{query}"

    async def async_get_pin_value(self, pin):
        params = {'token': self.token}
        url = self._get_request_url('external/api/get', params) + f"&{pin}"
        _LOGGER.debug(f"GET {url}")

        try:
            async with self._session.get(url, timeout=REQUEST_TIMEOUT) as response:
                text = await response.text()
                _LOGGER.debug(f"Response {response.status}: {text!r}")
                if response.status != 200:
                    raise Exception(f"Failed to get pin value for {pin}: HTTP {response.status}")
        except aiohttp.ClientError as exc:
            raise Exception(f"Failed to get pin value for {pin}: {exc}") from exc

        try:
            if text.isdigit():
                return int(text)
            if text.isalpha():
                return text.strip()
            return json.loads(text)[0]
        except (ValueError, IndexError) as exc:
            raise Exception(f"Failed to parse response for {pin}: {exc}") from exc

    async def async_set_pin_value(self, pin, value):
        params = {'token': self.token, pin: value}
        url = self._get_request_url('external/api/update', params)
        _LOGGER.debug(f"GET {url}")

        try:
            async with self._session.get(url, timeout=REQUEST_TIMEOUT) as response:
                text = (await response.text()).strip()
                _LOGGER.debug(f"Response {response.status}: {text!r}")
                if response.status != 200:
                    raise Exception(f"Failed to set pin value for {pin}: HTTP {response.status}")
                return text
        except aiohttp.ClientError as exc:
            raise Exception(f"Failed to set pin value for {pin}: {exc}") from exc

    async def async_set_power(self, value):
        _LOGGER.debug(f"Setting Raw Power: {value}")
        pin_value = self.power_mapping.get(value, "0")
        _LOGGER.debug(f"Setting Power: {pin_value}")
        await self.async_set_pin_value('V0', pin_value)

    async def async_set_current_temp(self, value):
        await self.async_set_pin_value('V1', str(value))

    async def async_set_target_temp(self, value):
        await self.async_set_pin_value('V2', str(value))

    async def async_set_mode(self, value):
        value = value.lower()  # Ensure consistent casing
        pin_value = self.mode_mapping.get(value, "0")
        _LOGGER.debug(f"Setting mode {value} to pin {pin_value}")
        await self.async_set_pin_value('V3', pin_value)

    async def async_set_fan(self, value):
        if self._product_type == PRODUCT_FAN:
            _LOGGER.debug(f"Setting fan speed {value} (numeric)")
            await self.async_set_pin_value('V2', str(value))
            return
        pin_value = self.fan_speed_mapping.get(value, "0")
        _LOGGER.debug(f"Setting fan {value} to pin {pin_value}")
        await self.async_set_pin_value('V4', pin_value)

    async def async_get_power(self) -> bool:
        pin_value = await self.async_get_pin_value('V0')
        _LOGGER.debug(f"Pin value received for power: {pin_value} (type: {type(pin_value)})")
        if pin_value == 1:
            return True
        else:
            return False

    async def async_get_mode(self):
        pin_value = await self.async_get_pin_value('V3')
        pin_value = str(pin_value).lower()
        current_power_state = await self.async_get_power()
        if current_power_state != False:
            match pin_value:
                case "cool":
                    return HVACMode.COOL
                case "fan":
                    return HVACMode.FAN_ONLY
                case "eco":
                    return HVACMode.AUTO
                case _:
                    return HVACMode.OFF
        else:
            return HVACMode.OFF


    async def async_get_fan(self):
        if self._product_type == PRODUCT_FAN:
            pin_value = await self.async_get_pin_value('V2')
            speed = str(pin_value).strip()
            _LOGGER.debug(f"Fan speed pin value: {speed}")
            return speed
        pin_value = await self.async_get_pin_value('V4')
        pin_value = str(pin_value).lower()
        fan_mode = "Auto"

        match pin_value:
            case "low":
                fan_mode = "Low"
            case "medium":
                fan_mode = "Medium"
            case "high":
                fan_mode = "High"
        _LOGGER.debug(f"Pin value: {pin_value} is mapped mode mapped to: {fan_mode}")
        return fan_mode

    async def async_get_autofade(self) -> bool:
        pin_value = await self.async_get_pin_value('V1')
        _LOGGER.debug(f"Autofade pin value: {pin_value}")
        return pin_value == 1

    async def async_set_autofade(self, value: bool):
        pin_value = self.power_mapping.get(value, 0)
        _LOGGER.debug(f"Setting autofade to {value} (pin {pin_value})")
        await self.async_set_pin_value('V1', pin_value)

    async def async_get_product_type(self):
        """Detect whether this device is an AC or a Fan.

        Primary signal: V6 returns a product name string (e.g. "Fan").
        Fallback: probe V3 (HVAC mode pin) — exists on AC, absent on Fan.
        """
        if self._product_type is not None:
            return self._product_type

        try:
            v6 = await self.async_get_pin_value('V6')
            if isinstance(v6, str):
                v6_lower = v6.lower()
                if "fan" in v6_lower:
                    _LOGGER.debug("V6 reports product 'Fan'")
                    self._product_type = PRODUCT_FAN
                    return self._product_type
                if "ac" in v6_lower or "air" in v6_lower:
                    _LOGGER.debug(f"V6 reports product '{v6}' -> AC")
                    self._product_type = PRODUCT_AC
                    return self._product_type
        except Exception as e:
            _LOGGER.debug(f"V6 product probe failed, falling back to V3 probe: {e}")

        try:
            await self.async_get_pin_value('V3')
            _LOGGER.debug("V3 mode pin present -> AC")
            self._product_type = PRODUCT_AC
        except Exception as e:
            _LOGGER.debug(f"V3 mode pin absent, defaulting to Fan: {e}")
            self._product_type = PRODUCT_FAN

        return self._product_type
