"""Config flow for PurpleAir integration."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Final

from aiopurpleair.api import API
from aiopurpleair.endpoints.sensors import NearbySensorResult
from aiopurpleair.errors import (
    InvalidApiKeyError,
    InvalidRequestError,
    NotFoundError,
    PurpleAirError,
    RequestError,
)
from aiopurpleair.models.sensors import GetSensorsResponse, SensorModel
import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.const import (
    CONF_API_KEY,
    CONF_BASE,
    CONF_LATITUDE,
    CONF_LOCATION,
    CONF_LONGITUDE,
    CONF_RADIUS,
    CONF_SHOW_ON_MAP,
    UnitOfLength,
)
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client, config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    LocationSelector,
    LocationSelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.util.unit_conversion import DistanceConverter

from .const import (
    CONF_ADD_MAP_LOCATION,
    CONF_ADD_SENSOR_INDEX,
    CONF_NO_SENSOR_FOUND,
    CONF_SENSOR,
    CONF_SENSOR_INDEX,
    CONF_SENSOR_READ_KEY,
    CONF_UNKNOWN,
    DOMAIN,
    LOGGER,
    SCHEMA_VERSION,
    SENSOR_FIELDS_ALL,
    TITLE,
)

DEFAULT_RADIUS: Final[int] = 2000
LIMIT_RESULTS: Final[int] = 25
SENSOR_FIELDS_NEARBY: Final[list[str]] = ["name", "longitude", "latitude"]

CONF_NEARBY_SENSOR_LIST: Final[str] = "nearby_sensor_list"


class PurpleAirConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PurpleAir."""

    VERSION = SCHEMA_VERSION

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Get config subentries."""
        return {
            CONF_SENSOR: PurpleAirSubentryFlow,
        }

    def _async_get_title(self) -> str:
        """Get instance title."""
        title: str = TITLE
        config_list = self.hass.config_entries.async_loaded_entries(DOMAIN)
        if len(config_list) > 0:
            title = f"{TITLE} ({len(config_list)})"
        return title

    async def _async_validate_api_key(self, api_key: str) -> dict[str, str]:
        """Validate API key."""
        api = API(api_key, session=async_get_clientsession(self.hass))
        try:
            keys_response = await api.async_check_api_key()
        except InvalidApiKeyError:
            return {CONF_API_KEY: "invalid_api_key"}
        except RequestError, InvalidRequestError, NotFoundError, PurpleAirError:
            return {"base": "unknown"}
        except Exception as err:  # noqa: BLE001
            # Catch broad exceptions in config flow for user experience.
            # Any unexpected error should show a generic error message.
            LOGGER.exception("Unexpected error checking API key: %s", err)
            return {"base": "unknown"}

        if not keys_response:
            return {"base": "unknown"}

        return {}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> PurpleAirOptionsFlow:
        """Define the config flow to handle options."""
        return PurpleAirOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle user initialization flow."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match({CONF_API_KEY: user_input[CONF_API_KEY]})
            if not (
                errors := await self._async_validate_api_key(user_input[CONF_API_KEY])
            ):
                if self.source == SOURCE_REAUTH:
                    return self.async_update_reload_and_abort(
                        self._get_reauth_entry(),
                        data_updates={CONF_API_KEY: user_input[CONF_API_KEY]},
                    )
                if self.source == SOURCE_RECONFIGURE:
                    return self.async_update_reload_and_abort(
                        self._get_reconfigure_entry(),
                        data_updates={CONF_API_KEY: user_input[CONF_API_KEY]},
                    )
                return self.async_create_entry(
                    title=self._async_get_title(),
                    data=user_input,
                    options={CONF_SHOW_ON_MAP: False},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): cv.string}),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle configuration by re-auth."""
        return await self.async_step_user()

    async def async_step_reconfigure(
        self, user_input: Mapping[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration."""
        return await self.async_step_user()


class PurpleAirOptionsFlow(OptionsFlow):
    """Options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle user initialization flow."""
        if user_input is not None:
            options = deepcopy(dict(self.config_entry.options))
            options[CONF_SHOW_ON_MAP] = user_input.get(CONF_SHOW_ON_MAP, False)
            return self.async_create_entry(data=options)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({vol.Optional(CONF_SHOW_ON_MAP): bool}),
                self.config_entry.options,
            ),
        )


class PurpleAirSubentryFlow(ConfigSubentryFlow):
    """Handle subentry flow."""

    def __init__(self) -> None:
        """Initialize."""
        self.nearby_sensors: dict[int, SensorModel] = {}
        self._flow_data: dict[str, Any] = {}
        self._errors: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Handle user initialization flow."""
        return self.async_show_menu(
            step_id="user", menu_options=[CONF_ADD_MAP_LOCATION, CONF_ADD_SENSOR_INDEX]
        )

    async def async_step_add_map_location(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Search sensors from map."""
        errors: dict[str, str] = {}
        if user_input is not None:
            api = API(
                self._get_entry().data[CONF_API_KEY],
                session=async_get_clientsession(self.hass),
            )
            nearby_sensor_list: list[NearbySensorResult] = []
            try:
                nearby_sensor_list = await api.sensors.async_get_nearby_sensors(
                    SENSOR_FIELDS_NEARBY,
                    user_input[CONF_LOCATION][CONF_LATITUDE],
                    user_input[CONF_LOCATION][CONF_LONGITUDE],
                    DistanceConverter.convert(
                        user_input[CONF_LOCATION][CONF_RADIUS],
                        UnitOfLength.METERS,
                        UnitOfLength.KILOMETERS,
                    ),
                    limit_results=LIMIT_RESULTS,
                )
            except InvalidApiKeyError:
                self.async_abort(reason="invalid_api_key")
            except (
                RequestError,
                InvalidRequestError,
                NotFoundError,
                PurpleAirError,
            ):
                errors["base"] = "unknown"
            except Exception as err:  # noqa: BLE001
                # Catch broad exceptions in config flow for user experience.
                # Any unexpected error should show a generic error message.
                LOGGER.exception("Unexpected error validating location: %s", err)
                errors["base"] = "unknown"

            else:
                # TODO: Remove entries that are already set up
                if not nearby_sensor_list:
                    errors[CONF_LOCATION] = "no_sensors_found"

            if not errors:
                self.nearby_sensors = {
                    result.sensor.sensor_index: result.sensor
                    for result in nearby_sensor_list
                }
                return await self.async_step_select_sensor()

        location = user_input or {
            CONF_LOCATION: {
                CONF_LATITUDE: self.hass.config.latitude,
                CONF_LONGITUDE: self.hass.config.longitude,
                CONF_RADIUS: float(DEFAULT_RADIUS),
            }
        }
        return self.async_show_form(
            step_id="add_map_location",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_LOCATION): LocationSelector(
                            LocationSelectorConfig(radius=True)
                        )
                    }
                ),
                location,
            ),
        )

    async def async_step_select_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Select sensor from list."""
        if user_input is not None:
            sensor = self.nearby_sensors[int(user_input[CONF_SENSOR_INDEX])]
            return self.async_create_entry(
                title=self._get_title(sensor),
                data={CONF_SENSOR_INDEX: sensor.sensor_index},
                unique_id=str(sensor.sensor_index),
            )
        return self.async_show_form(
            step_id="select_sensor",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SENSOR_INDEX): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(
                                    value=str(sensor_index),
                                    label=self._get_title(sensor),
                                )
                                for sensor_index, sensor in self.nearby_sensors.items()
                            ],
                            mode=SelectSelectorMode.LIST,
                            multiple=False,
                        )
                    )
                }
            ),
        )

    def _get_title(self, sensor: SensorModel) -> str:
        """Get sensor title."""
        return f"{sensor.name} ({sensor.sensor_index})"

    async def _async_validate_sensor(self) -> bool:
        """Validate sensor."""
        self._errors = {}

        sensor_index: int = self._flow_data[CONF_SENSOR_INDEX]
        index_list: list[int] = [sensor_index]

        read_key: str | None = self._flow_data[CONF_SENSOR_READ_KEY]
        read_key_list: list[str] | None = None
        if read_key is not None and len(read_key) > 0:
            read_key_list = [read_key]

        api = API(
            self._flow_data[CONF_API_KEY],
            session=aiohttp_client.async_get_clientsession(self.hass),
        )
        try:
            sensors_response: GetSensorsResponse = await api.sensors.async_get_sensors(
                SENSOR_FIELDS_ALL,
                sensor_indices=index_list,
                read_keys=read_key_list,
            )
        except InvalidApiKeyError as err:
            LOGGER.error("InvalidApiKeyError: %s", err)
            self._errors[CONF_BASE] = "invalid_api_key"
            return False
        except (
            RequestError,
            InvalidRequestError,
            NotFoundError,
            PurpleAirError,
        ) as err:
            LOGGER.error("PurpleAirError: %s", err)
            self._errors[CONF_BASE] = CONF_UNKNOWN
            return False
        except Exception as err:  # noqa: BLE001
            # Catch broad exceptions in config flow for user experience.
            # Any unexpected error should show a generic error message.
            LOGGER.exception("Unexpected error validating sensor: %s", err)
            self._errors[CONF_BASE] = CONF_UNKNOWN
            return False

        if (
            not sensors_response
            or not sensors_response.data
            or sensors_response.data.get(sensor_index) is None
            or sensors_response.data[sensor_index].sensor_index != sensor_index
        ):
            self._errors[CONF_SENSOR_INDEX] = CONF_NO_SENSOR_FOUND
            return False

        # No duplicate sensor indices allowed across all config entries and subentries
        if sensor_index in (
            int(subentry.data[CONF_SENSOR_INDEX])
            for config_entry in self.hass.config_entries.async_loaded_entries(DOMAIN)
            for subentry in config_entry.subentries.values()
        ):
            self._errors[CONF_SENSOR_INDEX] = "already_configured"
            return False

        self._flow_data[CONF_SENSOR] = sensors_response.data[sensor_index]
        return True

    @property
    def select_sensor_schema(self) -> vol.Schema:
        """Selection list schema."""
        nearby_sensor_list: list[NearbySensorResult] = self._flow_data[
            CONF_NEARBY_SENSOR_LIST
        ]
        return vol.Schema(
            {
                vol.Required(CONF_SENSOR_INDEX): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(
                                value=str(result.sensor.sensor_index),
                                label=self._get_title(result.sensor),
                            )
                            for result in nearby_sensor_list
                        ],
                        mode=SelectSelectorMode.LIST,
                        multiple=False,
                    )
                )
            }
        )

    @property
    def sensor_index_schema(self) -> vol.Schema:
        """Add sensor index schema."""
        return vol.Schema(
            {
                vol.Required(
                    CONF_SENSOR_INDEX, default=self._flow_data.get(CONF_SENSOR_INDEX)
                ): cv.positive_int,
                vol.Optional(
                    CONF_SENSOR_READ_KEY,
                    default=vol.UNDEFINED
                    if not self._flow_data.get(CONF_SENSOR_READ_KEY)
                    or len(str(self._flow_data[CONF_SENSOR_READ_KEY])) == 0
                    else self._flow_data[CONF_SENSOR_READ_KEY],
                ): cv.string,
            }
        )

    # Keep in sync with async_step_select_sensor()
    async def async_step_add_sensor_index(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add sensor by index and read key."""
        if user_input is None:
            return self.async_show_form(
                step_id=CONF_ADD_SENSOR_INDEX,
                data_schema=self.sensor_index_schema,
            )

        self._flow_data[CONF_SENSOR_INDEX] = int(user_input[CONF_SENSOR_INDEX])
        self._flow_data[CONF_SENSOR_READ_KEY] = user_input.get(CONF_SENSOR_READ_KEY)
        if not await self._async_validate_sensor():
            return self.async_show_form(
                step_id=CONF_ADD_SENSOR_INDEX,
                data_schema=self.sensor_index_schema,
                errors=self._errors,
            )

        sensor: SensorModel = self._flow_data[CONF_SENSOR]
        if TYPE_CHECKING:
            assert sensor is not None

        data: dict[str, Any] = {CONF_SENSOR_INDEX: sensor.sensor_index}
        read_key: str | None = self._flow_data[CONF_SENSOR_READ_KEY]
        if read_key is not None and len(read_key) > 0:
            data[CONF_SENSOR_READ_KEY] = read_key

        return self.async_create_entry(
            title=self._get_title(sensor),
            data=data,
            unique_id=str(sensor.sensor_index),
        )
