"""API client for the Elco Remocon-Net cloud service."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import quote

import requests

from .const import (
    MODE_AUTOMATIC,
    MODE_COMFORT,
    MODE_PROTECTION,
    MODE_REDUCTION,
)

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.remocon-net.remotethermo.com"
REQUEST_TIMEOUT = 30

FEATURES_PAYLOAD = {
    "gatewayId": "",
    "zones": [{"num": 1, "name": "", "roomSens": False, "geofenceDeroga": False,
               "virtInfo": None, "isHidden": False}],
    "solar": False, "convBoiler": False, "commBoiler": False, "hpSys": True,
    "hybridSys": False, "cascadeSys": False, "dhwProgSupported": True,
    "virtualZones": False, "hasVmc": False, "extendedTimeProg": False,
    "hasBoiler": False, "pilotSupported": True, "isVmcR2": False,
    "isEvo2": False, "dhwHidden": False, "dhwBoilerPresent": True,
    "dhwModeChangeable": True, "hvInputOff": False, "autoThermoReg": True,
    "hasMetering": True, "hasFireplace": False, "hasSlp": False,
    "hasEm20": True, "hasEm30": False, "systemServices": None,
    "hasTwoCoolingTemp": True, "bmsActive": False, "hpCascadeSys": False,
    "hpCascadeSysPcm5": False, "hpCascadeConfig": -1, "bufferTimeProgAvailable": True,
    "distinctHeatCoolSetpoints": True, "hasZoneNames": True,
    "zoneManagerStandAlone": False, "hydraulicScheme": 5,
    "preHeatingSupported": False, "hasGahp": False, "zigbeeActive": False,
    "hasSlpAloneOnBus": False, "isSlpCascade": False,
    "hasZeroColdWaterProg": False, "weatherProvider": 0,
    "hasDhwTimeProgTemperatures": 1, "isGSWHCommercialAloneOnBus": False,
}

AJAX_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Ajax-Request": "json",
    "X-Requested-With": "XMLHttpRequest",
}


class RemoconApiError(Exception):
    """Base exception for API errors."""


class RemoconAuthError(RemoconApiError):
    """Authentication failed."""


class RemoconConnectionError(RemoconApiError):
    """Connection error."""


class RemoconDataError(RemoconApiError):
    """Data error."""


@dataclass
class RemoconData:
    """All data from the heating system."""

    # Zone
    comfort_temp: float = 0.0
    comfort_temp_min: float = 5.0
    comfort_temp_max: float = 35.0
    comfort_temp_step: float = 0.5
    reduced_temp: float = 0.0
    cooling_comfort_temp: float = 0.0
    cooling_reduced_temp: float = 0.0
    desired_temp: float = 0.0
    room_temp: float = 0.0
    zone_mode: int = MODE_AUTOMATIC
    zone_mode_text: str = "Unknown"
    zone_mode_texts: list[str] = field(default_factory=list)
    heating_active: bool = False
    cooling_active: bool = False
    heat_or_cool_request: bool = False
    # Plant
    outside_temp: float = 0.0
    plant_mode: int = 0
    plant_mode_text: str = "Unknown"
    automatic_thermoregulation: bool = False
    holiday: bool = False
    dhw_temp: float = 0.0
    dhw_target_temp: float = 0.0
    dhw_comfort_temp: float = 0.0
    dhw_reduced_temp: float = 0.0
    dhw_mode: int = 0
    dhw_enabled: bool = False
    heat_pump_on: bool = False
    flame_sensor: bool = False
    # System
    system_pressure: Optional[float] = None
    flow_setpoint_temperature: Optional[float] = None
    zone_pilot_on: bool = False
    # Meta
    has_room_sensor: bool = False
    plant_address: str | None = None
    appliance_model: str | None = None
    error_text: str | None = None
    error_present: bool = False
    quiet_mode_start: str | None = None
    quiet_mode_end: str | None = None
    quiet_mode_active: bool = False


class RemoconClient:
    """Synchronous API client for Elco Remocon-Net."""

    def __init__(self, email: str, password: str, gateway_id: str, zone: str = "1") -> None:
        self._email = email
        self._password = password
        self._gateway_id = gateway_id
        self._zone = zone
        self._session: Optional[requests.Session] = None

    def login(self) -> None:
        """Authenticate and store session cookie."""
        s = requests.Session()
        url = f"{BASE_URL}/R2/Account/Login?returnUrl=HTTP/2"
        payload = (
            f"Email={quote(self._email, safe='')}"
            f"&Password={quote(self._password, safe='')}"
            f"&RememberMe=false"
        )
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": "browserUtcOffset=-120",
        }
        try:
            resp = s.post(url, headers=headers, data=payload, timeout=15)
        except requests.RequestException as err:
            raise RemoconConnectionError(str(err)) from err

        if resp.status_code in (401, 403):
            raise RemoconAuthError("Invalid credentials")
        try:
            resp.raise_for_status()
        except requests.HTTPError as err:
            raise RemoconConnectionError(str(err)) from err

        try:
            data = resp.json()
        except ValueError as err:
            raise RemoconAuthError("Could not parse login response") from err

        if not data.get("ok"):
            raise RemoconAuthError(data.get("message", "Login failed"))

        self._session = s

    def _get_session(self) -> requests.Session:
        if self._session is None:
            self.login()
        return self._session  # type: ignore[return-value]

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        s = self._get_session()
        url = f"{BASE_URL}{path}"
        kwargs.setdefault("timeout", REQUEST_TIMEOUT)
        retry_read = method.upper() == "GET" or path.startswith(
            ("/R2/PlantHome/GetData/", "/R2/PlantAdvancedSettings/Refresh/")
        )
        for attempt in range(2 if retry_read else 1):
            try:
                resp = s.request(method, url, **kwargs)
                if resp.status_code in (401, 403):
                    raise RemoconAuthError("Session expired")
                resp.raise_for_status()
                break
            except requests.exceptions.ReadTimeout as err:
                if attempt == 0 and retry_read:
                    _LOGGER.warning(
                        "API read timed out after %ss, retrying: %s",
                        REQUEST_TIMEOUT,
                        path,
                    )
                    continue
                err_msg = str(err)
                _LOGGER.error("API Request failed: %s", err_msg)
                raise RemoconConnectionError(err_msg) from err
            except requests.RequestException as err:
                err_msg = str(err)
                response = err.response
                if response is not None:
                    err_msg += f" - Response: {response.text}"
                _LOGGER.error("API Request failed: %s", err_msg)
                raise RemoconConnectionError(err_msg) from err
        
        try:
            return resp.json()
        except ValueError as err:
            _LOGGER.error("Invalid JSON response from API: %s", resp.text)
            raise RemoconDataError("Could not parse API response") from err

    def _features(self) -> dict[str, Any]:
        """Return a gateway-specific copy of the web UI feature profile."""
        features = dict(FEATURES_PAYLOAD)
        features["gatewayId"] = self._gateway_id
        features["zones"] = [{
            "num": int(self._zone),
            "name": "",
            "roomSens": False,
            "geofenceDeroga": False,
            "virtInfo": None,
            "isHidden": False,
        }]
        return features

    @staticmethod
    def _as_bool(value: Any) -> bool:
        """Convert API boolean values, including numeric strings, safely."""
        if isinstance(value, str):
            return value.strip().lower() not in {"", "0", "false", "off", "no"}
        return bool(value)

    def _submit_plant_menu(self, items: list[dict[str, Any]]) -> None:
        """Submit one or more web UI PlantMenu values."""
        path = f"/R2/PlantMenu/Submit/{self._gateway_id}?userActivity=SaveOtherSettings"
        self._request("POST", path, headers=AJAX_HEADERS, json=items)

    def _get_raw(self) -> dict:
        path = f"/R2/PlantHome/GetData/{self._gateway_id}?umsys=si"
        payload = {
            "useCache": True,
            "zone": int(self._zone),
            "filter": {"notEssentials": False, "plant": True, "zone": True, "dhw": True},
            "features": self._features(),
        }
        data = self._request("POST", path, headers=AJAX_HEADERS, json=payload)
        if not data:
            raise RemoconDataError("Empty data received from API")
        if isinstance(data, dict) and not data.get("ok", True):
            _LOGGER.error("API returned error: %s", data)
            raise RemoconDataError(data.get("message", "API returned error"))
        raw = data.get("data", data) if isinstance(data, dict) else data
        if not isinstance(raw, dict):
            raise RemoconDataError(f"Unexpected data format from API: {type(raw)}")

        _LOGGER.debug(
            "Plant data response for gateway %s: top-level keys=%s, data keys=%s",
            self._gateway_id,
            sorted(data) if isinstance(data, dict) else type(data).__name__,
            sorted(raw),
        )
        if "items" not in raw and (
            "plantData" not in raw or "zoneData" not in raw
        ):
            raise RemoconDataError(
                "API response does not contain items or plantData/zoneData "
                f"(keys: {sorted(raw)})"
            )
        return raw

    def get_data(self) -> RemoconData:
        """Fetch all data and return a RemoconData object."""
        raw = self._get_raw()
        try:
            header = self._get_header()
        except RemoconApiError as err:
            _LOGGER.debug("Could not fetch plant header: %s", err)
            header = {}
        try:
            advanced = self._get_advanced_settings(raw.get("features", FEATURES_PAYLOAD))
        except RemoconApiError as err:
            _LOGGER.debug("Could not fetch advanced settings: %s", err)
            advanced = {}
        if "items" in raw:
            data = self._parse_items(raw["items"])
            data = self._add_header_data(data, header)
            return self._add_advanced_data(data, advanced)

        plant = raw.get("plantData") or {}
        zone = raw.get("zoneData") or {}

        ch_comfort = zone.get("chComfortTemp") or {}
        ch_reduced = zone.get("chReducedTemp") or {}
        mode_info = zone.get("mode") or {}

        dhw_comfort = plant.get("dhwComfortTemp") or {}
        dhw_reduced = plant.get("dhwReducedTemp") or {}
        dhw_mode_info = plant.get("dhwMode") or {}

        data = RemoconData(
            comfort_temp=float(ch_comfort.get("value", 0)),
            comfort_temp_min=float(ch_comfort.get("min", 5)),
            comfort_temp_max=float(ch_comfort.get("max", 35)),
            comfort_temp_step=float(ch_comfort.get("step", 0.5)),
            reduced_temp=float(ch_reduced.get("value", 0)),
            desired_temp=float(zone.get("desiredRoomTemp", 0)),
            room_temp=float(zone.get("roomTemp", 0)),
            zone_mode=mode_info.get("value", MODE_AUTOMATIC),
            zone_mode_texts=mode_info.get("allowedOptionTexts", []),
            heating_active=RemoconClient._as_bool(zone.get("isHeatingActive", 0)),
            cooling_active=RemoconClient._as_bool(zone.get("isCoolingActive", 0)),
            heat_or_cool_request=RemoconClient._as_bool(
                zone.get("heatOrCoolRequest", 0)
            ),
            outside_temp=float(plant.get("outsideTemp", 0)),
            dhw_temp=float(plant.get("dhwStorageTemp", 0)),
            dhw_comfort_temp=float(dhw_comfort.get("value", 0)),
            dhw_reduced_temp=float(dhw_reduced.get("value", 0)),
            dhw_mode=dhw_mode_info.get("value", 0),
            dhw_enabled=RemoconClient._as_bool(plant.get("dhwEnabled", 0)),
            heat_pump_on=RemoconClient._as_bool(plant.get("heatPumpOn", 0)),
            flame_sensor=RemoconClient._as_bool(plant.get("flameSensor", 0)),
            system_pressure=None,
            has_room_sensor=RemoconClient._as_bool(zone.get("hasRoomSensor", 0)),
        )
        data = self._add_header_data(data, header)
        return self._add_advanced_data(data, advanced)

    def _get_header(self) -> dict[str, Any]:
        """Fetch plant identity and gateway status shown in the web UI."""
        path = f"/R2/Plant/PlantHeader/{self._gateway_id}?rnd=0"
        data = self._request("GET", path)
        return data.get("data", {}) if isinstance(data, dict) else {}

    def _get_advanced_settings(self, features: dict[str, Any]) -> dict[str, Any]:
        """Fetch advanced settings using the same AJAX contract as the web UI."""
        path = f"/R2/PlantAdvancedSettings/Refresh/{self._gateway_id}"
        advanced_features = dict(features)
        advanced_features["gatewayId"] = self._gateway_id
        response = self._request(
            "POST",
            path,
            headers=AJAX_HEADERS,
            json={"features": advanced_features},
        )
        data = response.get("data", {}) if isinstance(response, dict) else {}
        return {item["id"]: item for item in data.get("dataItems", []) if item.get("id")}

    @staticmethod
    def _add_header_data(data: RemoconData, header: dict[str, Any]) -> RemoconData:
        """Add web UI plant-header data to the common data model."""
        data.plant_address = header.get("plantAddress")
        data.appliance_model = header.get("applianceModel")
        data.error_text = header.get("errorText")
        data.error_present = RemoconClient._as_bool(header.get("errorType", 0))
        return data

    @staticmethod
    def _add_advanced_data(
        data: RemoconData, advanced: dict[str, Any]
    ) -> RemoconData:
        """Add advanced settings returned by the Plant web UI."""
        start = advanced.get("QuietModeStart", {}).get("value")
        end = advanced.get("QuietModeEnd", {}).get("value")
        data.quiet_mode_start = RemoconClient._format_time_value(start)
        data.quiet_mode_end = RemoconClient._format_time_value(end)
        data.quiet_mode_active = RemoconClient._as_bool(
            advanced.get("IsQuite", {}).get("value", 0)
        )
        return data

    @staticmethod
    def _format_time_value(value: Any) -> str | None:
        """Convert the API's fixed-point time value to HH:MM."""
        if value is None:
            return None
        try:
            total_minutes = round(float(value) / 256 * 60)
            hours, minutes = divmod(total_minutes, 60)
            return f"{hours % 24:02d}:{minutes:02d}"
        except (TypeError, ValueError):
            return None

    def _parse_items(
        self, items: list[dict[str, Any]]
    ) -> RemoconData:
        """Convert the current flat R2 data-item response to RemoconData."""
        values = self._item_values(items)

        def item_value(item_id: str, default: Any = 0) -> Any:
            return values.get(item_id, {}).get("value", default)

        def item_float(item_id: str, default: float = 0.0) -> float:
            try:
                return float(item_value(item_id, default))
            except (TypeError, ValueError):
                return default

        mode_item = values.get("ZoneMode", {})
        mode_texts = mode_item.get("optTexts") or []
        plant_mode_item = values.get("PlantMode", {})
        plant_mode = int(item_float("PlantMode"))
        plant_options = plant_mode_item.get("options") or []
        plant_texts = plant_mode_item.get("optTexts") or []
        plant_mode_text = RemoconClient._enum_text(
            plant_mode, plant_options, plant_texts
        )
        raw_zone_mode = int(item_float("ZoneMode"))
        zone_mode_text = RemoconClient._enum_text(
            raw_zone_mode, mode_item.get("options") or [], mode_texts
        )
        zone_mode = {
            0: MODE_PROTECTION,
            2: MODE_COMFORT,
            3: MODE_AUTOMATIC,
        }.get(raw_zone_mode, MODE_AUTOMATIC)
        zone_mode_texts = [str(text) for text in mode_texts]

        return RemoconData(
            comfort_temp=item_float("ZoneComfortTemp"),
            comfort_temp_min=item_float("ZoneComfortTemp", 5.0)
            if "ZoneComfortTemp" not in values
            else float(values["ZoneComfortTemp"].get("min", 5.0)),
            comfort_temp_max=item_float("ZoneComfortTemp", 35.0)
            if "ZoneComfortTemp" not in values
            else float(values["ZoneComfortTemp"].get("max", 35.0)),
            comfort_temp_step=item_float("ZoneComfortTemp", 0.5)
            if "ZoneComfortTemp" not in values
            else float(values["ZoneComfortTemp"].get("step", 0.5)),
            reduced_temp=item_float("ZoneEconomyTemp"),
            cooling_comfort_temp=item_float("ZoneComfortCoolingTemp"),
            cooling_reduced_temp=item_float("ZoneEconomyCoolingTemp"),
            desired_temp=item_float("ZoneDesiredTemp"),
            room_temp=item_float("ZoneMeasuredTemp"),
            zone_mode=zone_mode,
            zone_mode_text=zone_mode_text,
            zone_mode_texts=zone_mode_texts,
            heating_active=False,
            cooling_active=int(item_float("PlantMode")) == 3,
            heat_or_cool_request=False,
            outside_temp=item_float("OutsideTemp"),
            plant_mode=plant_mode,
            plant_mode_text=plant_mode_text,
            automatic_thermoregulation=RemoconClient._as_bool(
                item_value("AutomaticThermoregulation", 0)
            ),
            holiday=RemoconClient._as_bool(item_value("Holiday", 0)),
            dhw_temp=item_float("DhwStorageTemperature"),
            dhw_target_temp=item_float("DhwTemp"),
            dhw_comfort_temp=item_float("DhwTimeProgComfortTemp"),
            dhw_reduced_temp=item_float("DhwTimeProgEconomyTemp"),
            dhw_mode=int(item_float("DhwMode")),
            dhw_enabled=int(item_float("DhwMode")) != 0,
            heat_pump_on=int(item_float("PlantMode")) in (1, 2, 3),
            system_pressure=(
                item_float("HeatingCircuitPressure")
                if "HeatingCircuitPressure" in values
                else None
            ),
            flow_setpoint_temperature=item_float("ChFlowSetpointTemp")
            if "ChFlowSetpointTemp" in values
            else None,
            zone_pilot_on=RemoconClient._as_bool(item_value("IsZonePilotOn", 0)),
            has_room_sensor="ZoneMeasuredTemp" in values,
        )

    @staticmethod
    def _item_values(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Index data items by ID."""
        return {item["id"]: item for item in items if item.get("id")}

    @staticmethod
    def _enum_text(value: int, options: list[Any], texts: list[Any]) -> str:
        """Resolve an API enum value using its parallel options/text arrays."""
        try:
            index = options.index(value)
            return str(texts[index])
        except (ValueError, IndexError):
            return "Unknown"

    @classmethod
    def _raw_item_values(cls, raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Return indexed items when the current response schema is used."""
        items = raw.get("items")
        return cls._item_values(items) if isinstance(items, list) else {}

    def set_dhw_temperature(self, temperature: float) -> None:
        """Set DHW target temperature using the PlantDhw save contract."""
        raw = self._get_raw()
        items = self._raw_item_values(raw)
        item_ids = (
            "DhwTemp",
            "DhwMode",
            "DhwStorageTemperature",
            "IsDhwBoost",
        )
        values = {
            "DhwTemp": temperature,
            "DhwMode": items.get("DhwMode", {}).get("value", 0),
            "DhwStorageTemperature": items.get(
                "DhwStorageTemperature", {}
            ).get("value", 0),
            "IsDhwBoost": items.get("IsDhwBoost", {}).get("value", 0),
        }
        prev_items = []
        for item_id in item_ids:
            item = dict(items.get(item_id, {}))
            item.setdefault("gatewayId", self._gateway_id)
            item.setdefault("zone", 0)
            item.setdefault("id", item_id)
            prev_items.append(item)

        path = f"/R2/PlantDhw/Save/{self._gateway_id}"
        self._request(
            "POST",
            path,
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Ajax-Request": "json",
                "X-Requested-With": "XMLHttpRequest",
            },
            json={
                "features": self._features(),
                "requestItems": [
                    {"itemId": item_id, "value": values[item_id]}
                    for item_id in item_ids
                ],
                "prevDataItems": prev_items,
            },
        )

    def set_dhw_comfort_temperature(self, temperature: float) -> None:
        """Set DHW comfort temperature using the PlantMenu contract."""
        raw = self._get_raw()
        items = self._raw_item_values(raw)
        comfort = items.get("DhwTimeProgComfortTemp", {}).get("value", 0)
        economy = items.get("DhwTimeProgEconomyTemp", {}).get("value", 0)
        path = f"/R2/PlantMenu/Submit/{self._gateway_id}?userActivity=SaveOtherSettings"
        self._request(
            "POST",
            path,
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Ajax-Request": "json",
                "X-Requested-With": "XMLHttpRequest",
            },
            json=[
                {"id": "U6_9_1_0_0", "value": temperature, "prevValue": comfort},
                {"id": "U6_9_1_0_1", "value": economy, "prevValue": economy},
            ],
        )

    def set_dhw_economy_temperature(self, temperature: float) -> None:
        """Set DHW economy temperature using the PlantMenu contract."""
        raw = self._get_raw()
        items = self._raw_item_values(raw)
        comfort = items.get("DhwTimeProgComfortTemp", {}).get("value", 0)
        economy = items.get("DhwTimeProgEconomyTemp", {}).get("value", 0)
        path = f"/R2/PlantMenu/Submit/{self._gateway_id}?userActivity=SaveOtherSettings"
        self._request(
            "POST",
            path,
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Ajax-Request": "json",
                "X-Requested-With": "XMLHttpRequest",
            },
            json=[
                {"id": "U6_9_1_0_0", "value": comfort, "prevValue": comfort},
                {
                    "id": "U6_9_1_0_1",
                    "value": temperature,
                    "prevValue": economy,
                },
            ],
        )

    def set_dhw_mode(self, mode: int) -> None:
        """Set DHW mode using the PlantDhw save contract."""
        raw = self._get_raw()
        items = self._raw_item_values(raw)
        item_ids = (
            "DhwTemp",
            "DhwMode",
            "DhwStorageTemperature",
            "IsDhwBoost",
        )
        values = {
            "DhwTemp": items.get("DhwTemp", {}).get("value", 0),
            "DhwMode": mode,
            "DhwStorageTemperature": items.get(
                "DhwStorageTemperature", {}
            ).get("value", 0),
            "IsDhwBoost": items.get("IsDhwBoost", {}).get("value", 0),
        }
        prev_items = []
        for item_id in item_ids:
            item = dict(items.get(item_id, {}))
            item.setdefault("gatewayId", self._gateway_id)
            item.setdefault("zone", 0)
            item.setdefault("id", item_id)
            item["value"] = values[item_id] if item_id != "DhwMode" else items.get(
                "DhwMode", {}
            ).get("value", 0)
            prev_items.append(item)

        path = f"/R2/PlantDhw/Save/{self._gateway_id}"
        self._request(
            "POST",
            path,
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Ajax-Request": "json",
                "X-Requested-With": "XMLHttpRequest",
            },
            json={
                "features": self._features(),
                "requestItems": [
                    {"itemId": item_id, "value": values[item_id]}
                    for item_id in item_ids
                ],
                "prevDataItems": prev_items,
            },
        )

    def set_plant_mode(self, mode: int) -> None:
        """Set plant operation mode using the PlantMenu contract."""
        raw = self._get_raw()
        items = self._raw_item_values(raw)
        old_mode = int(items.get("PlantMode", {}).get("value", 0))
        self._submit_plant_menu(
            [{"id": "U3", "value": str(mode), "prevValue": old_mode}]
        )

    def set_zone_mode_value(self, mode: int) -> None:
        """Set the raw zone operation mode using the PlantMenu contract."""
        items = self._raw_item_values(self._get_raw())
        old_mode = int(items.get("ZoneMode", {}).get("value", 0))
        self._submit_plant_menu(
            [{"id": "U0_0", "value": str(mode), "prevValue": old_mode}]
        )

    def set_zone_comfort_temperature(self, temperature: float) -> None:
        """Set zone comfort temperature using the PlantMenu contract."""
        items = self._raw_item_values(self._get_raw())
        old_value = items.get("ZoneComfortTemp", {}).get("value", 0)
        self._submit_plant_menu([{
            "id": "U6_3_1_0_0",
            "value": temperature,
            "prevValue": old_value,
        }])

    def set_zone_economy_temperature(self, temperature: float) -> None:
        """Set zone economy temperature using the PlantMenu contract."""
        items = self._raw_item_values(self._get_raw())
        old_value = items.get("ZoneEconomyTemp", {}).get("value", 0)
        self._submit_plant_menu([{
            "id": "U6_3_1_0_1",
            "value": temperature,
            "prevValue": old_value,
        }])

    def set_zone_cooling_comfort_temperature(self, temperature: float) -> None:
        """Set zone cooling comfort temperature using PlantMenu."""
        items = self._raw_item_values(self._get_raw())
        old_value = items.get("ZoneComfortCoolingTemp", {}).get("value", 0)
        economy = items.get("ZoneEconomyCoolingTemp", {}).get("value", 0)
        self._submit_plant_menu([
            {"id": "U6_6_1_0_0", "value": temperature, "prevValue": old_value},
            {"id": "U6_6_1_0_2", "value": economy, "prevValue": economy},
        ])

    def set_zone_cooling_economy_temperature(self, temperature: float) -> None:
        """Set zone cooling economy temperature using PlantMenu."""
        items = self._raw_item_values(self._get_raw())
        comfort = items.get("ZoneComfortCoolingTemp", {}).get("value", 0)
        old_value = items.get("ZoneEconomyCoolingTemp", {}).get("value", 0)
        self._submit_plant_menu([
            {"id": "U6_6_1_0_0", "value": comfort, "prevValue": comfort},
            {"id": "U6_6_1_0_2", "value": temperature, "prevValue": old_value},
        ])

    def set_automatic_thermoregulation(self, enabled: bool) -> None:
        """Set automatic thermoregulation using the PlantMenu contract."""
        raw = self._get_raw()
        items = self._raw_item_values(raw)
        old_value = int(items.get("AutomaticThermoregulation", {}).get("value", 0))
        value = int(enabled)
        self._submit_plant_menu(
            [{"id": "U6_3_3", "value": str(value), "prevValue": old_value}]
        )

    def reauth(self) -> None:
        """Force re-authentication."""
        self._session = None
        self.login()
