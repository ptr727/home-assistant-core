"""Define tests for the PurpleAir config flow."""

from unittest.mock import AsyncMock

from aiopurpleair.errors import InvalidApiKeyError, PurpleAirError
import pytest

from homeassistant.components.purpleair.const import (
    CONF_SENSOR_INDEX,
    CONF_UNKNOWN,
    DOMAIN,
    SUBENTRY_TYPE_SENSOR,
    TITLE,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LOCATION,
    CONF_LONGITUDE,
    CONF_RADIUS,
    CONF_SHOW_ON_MAP,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .const import (
    TEST_API_KEY,
    TEST_LATITUDE,
    TEST_LONGITUDE,
    TEST_NEW_API_KEY,
    TEST_RADIUS,
    TEST_SENSOR_INDEX1,
)

from tests.common import MockConfigEntry


async def test_user_flow(hass: HomeAssistant, mock_aiopurpleair: AsyncMock) -> None:
    """Test user initialization flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: TEST_API_KEY}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_API_KEY: TEST_API_KEY}
    assert result["options"] == {
        CONF_SHOW_ON_MAP: False,
    }
    assert result["title"] == TITLE


@pytest.mark.parametrize(
    ("exception", "errors"),
    [
        (Exception, {"base": CONF_UNKNOWN}),
        (PurpleAirError, {"base": CONF_UNKNOWN}),
        (InvalidApiKeyError, {CONF_API_KEY: "invalid_api_key"}),
    ],
)
async def test_user_init_errors(
    hass: HomeAssistant,
    mock_aiopurpleair: AsyncMock,
    exception: Exception,
    errors: dict[str, str],
) -> None:
    """Test user initialization flow with errors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    mock_aiopurpleair.async_check_api_key.side_effect = exception

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: TEST_API_KEY}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == errors

    mock_aiopurpleair.async_check_api_key.side_effect = None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: TEST_API_KEY}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_init_no_response(
    hass: HomeAssistant, mock_aiopurpleair: AsyncMock
) -> None:
    """Test user initialization flow with errors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    original_response = mock_aiopurpleair.async_check_api_key.return_value

    mock_aiopurpleair.async_check_api_key.return_value = None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: TEST_API_KEY}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": CONF_UNKNOWN}

    mock_aiopurpleair.async_check_api_key.return_value = original_response

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: TEST_API_KEY}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_duplicate_entry(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_aiopurpleair: AsyncMock,
) -> None:
    """Test duplicate API key flow."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: TEST_API_KEY}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_aiopurpleair: AsyncMock,
) -> None:
    """Test reconfigure."""

    result = await config_entry.start_reconfigure_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: TEST_NEW_API_KEY}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    assert config_entry.data[CONF_API_KEY] == TEST_NEW_API_KEY


@pytest.mark.parametrize(
    ("exception", "errors"),
    [
        (Exception, {"base": CONF_UNKNOWN}),
        (PurpleAirError, {"base": CONF_UNKNOWN}),
        (InvalidApiKeyError, {CONF_API_KEY: "invalid_api_key"}),
    ],
)
async def test_reconfigure_errors(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_aiopurpleair: AsyncMock,
    exception: Exception,
    errors: dict[str, str],
) -> None:
    """Test reconfigure."""

    result = await config_entry.start_reconfigure_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    mock_aiopurpleair.async_check_api_key.side_effect = exception

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: TEST_NEW_API_KEY}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == errors

    mock_aiopurpleair.async_check_api_key.side_effect = None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: TEST_NEW_API_KEY}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    assert config_entry.data[CONF_API_KEY] == TEST_NEW_API_KEY


async def test_reconfigure_errors_no_response(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_aiopurpleair: AsyncMock
) -> None:
    """Test user initialization flow with errors."""
    result = await config_entry.start_reconfigure_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    original_response = mock_aiopurpleair.async_check_api_key.return_value

    mock_aiopurpleair.async_check_api_key.return_value = None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: TEST_API_KEY}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": CONF_UNKNOWN}

    mock_aiopurpleair.async_check_api_key.return_value = original_response

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: TEST_API_KEY}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


async def test_reauth(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_aiopurpleair: AsyncMock
) -> None:
    """Test reauth."""

    result = await config_entry.start_reauth_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: TEST_NEW_API_KEY}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"

    assert config_entry.data[CONF_API_KEY] == TEST_NEW_API_KEY


@pytest.mark.parametrize(
    ("exception", "errors"),
    [
        (Exception, {"base": CONF_UNKNOWN}),
        (PurpleAirError, {"base": CONF_UNKNOWN}),
        (InvalidApiKeyError, {CONF_API_KEY: "invalid_api_key"}),
    ],
)
async def test_reauth_errors(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_aiopurpleair: AsyncMock,
    exception: Exception,
    errors: dict[str, str],
) -> None:
    """Test reauth error handling."""

    result = await config_entry.start_reauth_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    mock_aiopurpleair.async_check_api_key.side_effect = exception

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: TEST_NEW_API_KEY}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == errors

    mock_aiopurpleair.async_check_api_key.side_effect = None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: TEST_NEW_API_KEY}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"

    assert config_entry.data[CONF_API_KEY] == TEST_NEW_API_KEY


async def test_reauth_errors_no_response(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_aiopurpleair: AsyncMock
) -> None:
    """Test reauth error handling with no response."""
    result = await config_entry.start_reauth_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    original_response = mock_aiopurpleair.async_check_api_key.return_value

    mock_aiopurpleair.async_check_api_key.return_value = None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: TEST_API_KEY}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": CONF_UNKNOWN}

    mock_aiopurpleair.async_check_api_key.return_value = original_response

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: TEST_API_KEY}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


async def test_options_settings(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Test options setting flow."""

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SHOW_ON_MAP: True}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_SHOW_ON_MAP: True}


async def test_create_from_map(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_aiopurpleair: AsyncMock
) -> None:
    """Test creating subentry from map."""

    result = await hass.config_entries.subentries.async_init(
        (config_entry.entry_id, SUBENTRY_TYPE_SENSOR), context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "user"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "add_map_location"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_map_location"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_LOCATION: {
                CONF_LATITUDE: TEST_LATITUDE,
                CONF_LONGITUDE: TEST_LONGITUDE,
                CONF_RADIUS: TEST_RADIUS,
            }
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_sensor"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_SENSOR_INDEX: str(TEST_SENSOR_INDEX1),
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_SENSOR_INDEX: TEST_SENSOR_INDEX1}
    subentry = list(config_entry.subentries.values())[0]
    assert subentry.unique_id == str(TEST_SENSOR_INDEX1)


# async def test_create_from_index(
#     hass: HomeAssistant, config_entry, setup_config_entry, mock_aiopurpleair, api
# ) -> None:
#     """Test creating subentry from index and read key."""
#
#     # User init
#     result = await hass.config_entries.subentries.async_init(
#         (config_entry.entry_id, CONF_SENSOR), context={"source": SOURCE_USER}
#     )
#     await hass.async_block_till_done()
#     assert result["type"] is FlowResultType.MENU
#     assert result["step_id"] == CONF_ADD_OPTIONS
#
#     # Add by index
#     result = await hass.config_entries.subentries.async_configure(
#         result["flow_id"], user_input={"next_step_id": CONF_ADD_SENSOR_INDEX}
#     )
#     await hass.async_block_till_done()
#     assert result["type"] is FlowResultType.FORM
#     assert result["step_id"] == CONF_ADD_SENSOR_INDEX
#
#     # Enter index and create
#     with patch.object(api, "sensors.async_get_sensors"):
#         result = await hass.config_entries.subentries.async_configure(
#             result["flow_id"],
#             user_input={
#                 CONF_SENSOR_INDEX: TEST_SENSOR_INDEX1,
#                 CONF_SENSOR_READ_KEY: TEST_SENSOR_READ_KEY,
#             },
#         )
#         await hass.async_block_till_done()
#     assert result["type"] is FlowResultType.CREATE_ENTRY
#     assert result["data"] == {
#         CONF_SENSOR_INDEX: TEST_SENSOR_INDEX1,
#         CONF_SENSOR_READ_KEY: TEST_SENSOR_READ_KEY,
#     }
#
#
# async def test_duplicate_sensor(
#     hass: HomeAssistant,
#     config_entry,
#     config_subentry,
#     setup_config_entry,
#     mock_aiopurpleair,
#     api,
# ) -> None:
#     """Test creating subentry from index and read key."""
#     # User init
#     result = await hass.config_entries.subentries.async_init(
#         (config_entry.entry_id, CONF_SENSOR), context={"source": SOURCE_USER}
#     )
#     await hass.async_block_till_done()
#     assert result["type"] is FlowResultType.MENU
#     assert result["step_id"] == CONF_ADD_OPTIONS
#
#     # Add by index
#     result = await hass.config_entries.subentries.async_configure(
#         result["flow_id"], user_input={"next_step_id": CONF_ADD_SENSOR_INDEX}
#     )
#     await hass.async_block_till_done()
#     assert result["type"] is FlowResultType.FORM
#     assert result["step_id"] == CONF_ADD_SENSOR_INDEX
#
#     # Enter index and create
#     with patch.object(api, "sensors.async_get_sensors"):
#         result = await hass.config_entries.subentries.async_configure(
#             result["flow_id"],
#             user_input={
#                 CONF_SENSOR_INDEX: TEST_SENSOR_INDEX1,
#                 CONF_SENSOR_READ_KEY: TEST_SENSOR_READ_KEY,
#             },
#         )
#         await hass.async_block_till_done()
#     assert result["type"] is FlowResultType.FORM
#     assert result["errors"] == {CONF_SENSOR_INDEX: "already_configured"}
#
#     hass.config_entries.subentries.async_abort(result["flow_id"])
#     await hass.async_block_till_done()
#
#
# @pytest.mark.parametrize(
#     ("get_nearby_sensors_mock", "get_nearby_sensors_errors"),
#     [
#         (AsyncMock(side_effect=Exception), {CONF_BASE: CONF_UNKNOWN}),
#         (AsyncMock(side_effect=PurpleAirError), {CONF_BASE: CONF_UNKNOWN}),
#         (AsyncMock(side_effect=InvalidApiKeyError), {CONF_BASE: "invalid_api_key"}),
#         (AsyncMock(return_value=[]), {CONF_LOCATION: CONF_NO_SENSORS_FOUND}),
#         (AsyncMock(return_value=None), {CONF_LOCATION: CONF_NO_SENSORS_FOUND}),
#     ],
# )
# async def test_create_from_map_errors(
#     hass: HomeAssistant,
#     config_entry,
#     setup_config_entry,
#     mock_aiopurpleair,
#     api,
#     get_nearby_sensors_mock,
#     get_nearby_sensors_errors,
# ) -> None:
#     """Test creating subentry from map with errors."""
#
#     # User init
#     result = await hass.config_entries.subentries.async_init(
#         (config_entry.entry_id, CONF_SENSOR), context={"source": SOURCE_USER}
#     )
#     await hass.async_block_till_done()
#     assert result["type"] is FlowResultType.MENU
#     assert result["step_id"] == CONF_ADD_OPTIONS
#
#     # Add by map
#     result = await hass.config_entries.subentries.async_configure(
#         result["flow_id"], user_input={"next_step_id": CONF_ADD_MAP_LOCATION}
#     )
#     await hass.async_block_till_done()
#     assert result["type"] is FlowResultType.FORM
#     assert result["step_id"] == CONF_ADD_MAP_LOCATION
#
#     # Map location
#     with patch.object(api.sensors, "async_get_nearby_sensors", get_nearby_sensors_mock):
#         result = await hass.config_entries.subentries.async_configure(
#             result["flow_id"],
#             user_input={
#                 CONF_LOCATION: {
#                     CONF_LATITUDE: TEST_LATITUDE,
#                     CONF_LONGITUDE: TEST_LONGITUDE,
#                     CONF_RADIUS: TEST_RADIUS,
#                 }
#             },
#         )
#         await hass.async_block_till_done()
#     assert result["type"] is FlowResultType.FORM
#     assert result["errors"] == get_nearby_sensors_errors
#
#     hass.config_entries.subentries.async_abort(result["flow_id"])
#     await hass.async_block_till_done()
#
#
# @pytest.mark.parametrize(
#     ("get_sensors_mock", "get_sensors_errors"),
#     [
#         (AsyncMock(side_effect=Exception), {CONF_BASE: CONF_UNKNOWN}),
#         (AsyncMock(side_effect=PurpleAirError), {CONF_BASE: CONF_UNKNOWN}),
#         (AsyncMock(side_effect=InvalidApiKeyError), {CONF_BASE: "invalid_api_key"}),
#         (AsyncMock(return_value=[]), {CONF_SENSOR_INDEX: CONF_NO_SENSOR_FOUND}),
#         (AsyncMock(return_value=None), {CONF_SENSOR_INDEX: CONF_NO_SENSOR_FOUND}),
#     ],
# )
# async def test_create_from_map_select_errors(
#     hass: HomeAssistant,
#     config_entry,
#     setup_config_entry,
#     mock_aiopurpleair,
#     api,
#     get_sensors_mock,
#     get_sensors_errors,
# ) -> None:
#     """Test creating subentry from map with select errors."""
#
#     # User init
#     result = await hass.config_entries.subentries.async_init(
#         (config_entry.entry_id, CONF_SENSOR), context={"source": SOURCE_USER}
#     )
#     await hass.async_block_till_done()
#     assert result["type"] is FlowResultType.MENU
#     assert result["step_id"] == CONF_ADD_OPTIONS
#
#     # Add by map
#     result = await hass.config_entries.subentries.async_configure(
#         result["flow_id"], user_input={"next_step_id": CONF_ADD_MAP_LOCATION}
#     )
#     await hass.async_block_till_done()
#     assert result["type"] is FlowResultType.FORM
#     assert result["step_id"] == CONF_ADD_MAP_LOCATION
#
#     # Map location
#     with patch.object(api, "sensors.async_get_nearby_sensors"):
#         result = await hass.config_entries.subentries.async_configure(
#             result["flow_id"],
#             user_input={
#                 CONF_LOCATION: {
#                     CONF_LATITUDE: TEST_LATITUDE,
#                     CONF_LONGITUDE: TEST_LONGITUDE,
#                     CONF_RADIUS: TEST_RADIUS,
#                 }
#             },
#         )
#         await hass.async_block_till_done()
#     assert result["type"] is FlowResultType.FORM
#     assert result["step_id"] == CONF_SELECT_SENSOR
#
#     # Select and create
#     with patch.object(api.sensors, "async_get_sensors", get_sensors_mock):
#         result = await hass.config_entries.subentries.async_configure(
#             result["flow_id"],
#             user_input={
#                 CONF_SENSOR_INDEX: str(TEST_SENSOR_INDEX1),
#             },
#         )
#         await hass.async_block_till_done()
#     assert result["type"] is FlowResultType.FORM
#     assert result["errors"] == get_sensors_errors
#
#     hass.config_entries.subentries.async_abort(result["flow_id"])
#     await hass.async_block_till_done()
#
#
# @pytest.mark.parametrize(
#     ("get_sensors_mock", "get_sensors_errors"),
#     [
#         (AsyncMock(side_effect=Exception), {CONF_BASE: CONF_UNKNOWN}),
#         (AsyncMock(side_effect=PurpleAirError), {CONF_BASE: CONF_UNKNOWN}),
#         (AsyncMock(side_effect=InvalidApiKeyError), {CONF_BASE: "invalid_api_key"}),
#         (AsyncMock(return_value=[]), {CONF_SENSOR_INDEX: CONF_NO_SENSOR_FOUND}),
#         (AsyncMock(return_value=None), {CONF_SENSOR_INDEX: CONF_NO_SENSOR_FOUND}),
#     ],
# )
# async def test_create_from_index_errors(
#     hass: HomeAssistant,
#     config_entry,
#     setup_config_entry,
#     mock_aiopurpleair,
#     api,
#     get_sensors_mock,
#     get_sensors_errors,
# ) -> None:
#     """Test creating subentry from index and read key with errors."""
#
#     # User init
#     result = await hass.config_entries.subentries.async_init(
#         (config_entry.entry_id, CONF_SENSOR), context={"source": SOURCE_USER}
#     )
#     await hass.async_block_till_done()
#     assert result["type"] is FlowResultType.MENU
#     assert result["step_id"] == CONF_ADD_OPTIONS
#
#     # Add by index
#     result = await hass.config_entries.subentries.async_configure(
#         result["flow_id"], user_input={"next_step_id": CONF_ADD_SENSOR_INDEX}
#     )
#     await hass.async_block_till_done()
#     assert result["type"] is FlowResultType.FORM
#     assert result["step_id"] == CONF_ADD_SENSOR_INDEX
#
#     # Enter index and create
#     with patch.object(api.sensors, "async_get_sensors", get_sensors_mock):
#         result = await hass.config_entries.subentries.async_configure(
#             result["flow_id"],
#             user_input={
#                 CONF_SENSOR_INDEX: TEST_SENSOR_INDEX1,
#                 CONF_SENSOR_READ_KEY: TEST_SENSOR_READ_KEY,
#             },
#         )
#         await hass.async_block_till_done()
#     assert result["type"] is FlowResultType.FORM
#     assert result["errors"] == get_sensors_errors
#
#     hass.config_entries.subentries.async_abort(result["flow_id"])
#     await hass.async_block_till_done()
