"""Constants for WasherCycle integration."""

from __future__ import annotations

DOMAIN = "washercycle"
MANUFACTURER = "Samsung"
MODEL = "WW75J54E0IW/SA"
DEFAULT_DEVICE_NAME = "WasherCycle"

STORAGE_VERSION = 2
STORAGE_KEY = f"{DOMAIN}.storage"

# Default source entity IDs (preselect in config flow)
DEFAULT_POWER_SENSOR = "sensor.laundry_washerplug_power"
DEFAULT_ENERGY_SENSOR = "sensor.laundry_washerplug_energy"
DEFAULT_PLUG_SWITCH = "switch.laundry_washerplug"
DEFAULT_DOOR_SENSOR = "binary_sensor.laundry_washerdoor_contact"
DEFAULT_MOVEMENT_SENSOR = "binary_sensor.laundry_washerdoor_moving"
DEFAULT_TEMPERATURE_SENSOR = "sensor.laundry_washerdoor_temperature"
DEFAULT_PLUG_LQI_SENSOR = "sensor.laundry_washerplug_linkquality"
DEFAULT_DOOR_LQI_SENSOR = "sensor.laundry_washerdoor_linkquality"
DEFAULT_DOOR_BATTERY_SENSOR = "sensor.laundry_washerdoor_battery"
DEFAULT_DOOR_BATTERY_LOW_SENSOR = "binary_sensor.laundry_washerdoor_battery_low"

# Detection defaults (provisional until training refines)
DEFAULT_START_POWER_W = 19.0
DEFAULT_STANDBY_POWER_W = 5.0
DEFAULT_START_SUSTAIN_SECONDS = 30
DEFAULT_START_MIN_ENERGY_WH = 1.0
DEFAULT_FALLBACK_COMPLETION_SECONDS = 300
DEFAULT_EARLY_COMPLETION_ENABLED = True
DEFAULT_EARLY_COMPLETION_MIN_SCORE = 0.75
DEFAULT_DOOR_CORRELATION_SECONDS = 30
DEFAULT_MOVEMENT_ENABLED = True
DEFAULT_TARGET_LATENCY_SECONDS = 10
DEFAULT_MAX_STALE_SECONDS = 120
DEFAULT_SHADOW_MODE = True
DEFAULT_LEGACY_STATUS_MIRROR = False
DEFAULT_EARLY_CONFIRM_SECONDS = 8
DEFAULT_IMPOSSIBLE_SPIKE_W = 3000.0
DEFAULT_PROVISIONAL_MIN_DURATION_SECONDS = 900

# Training defaults
DEFAULT_MIN_RUNS_RECOGNITION = 3
DEFAULT_MIN_RUNS_ROBUST = 5
DEFAULT_RESAMPLE_INTERVAL_SECONDS = 15
DEFAULT_RAW_RUN_RETENTION = 50
DEFAULT_COMPLETED_HISTORY_RETENTION = 20
DEFAULT_END_SIGNATURE_PRE_SECONDS = 300
DEFAULT_END_SIGNATURE_POST_SECONDS = 30
DEFAULT_AUTO_INCLUDE_TRAINING_RUNS = True
DEFAULT_MATCHER_MARGIN = 0.12

# Announcement defaults
DEFAULT_COMPLETION_ANNOUNCEMENTS_ENABLED = False
DEFAULT_REWASH_ANNOUNCEMENTS_ENABLED = False
DEFAULT_COMPLETION_SPEAKERS = ["media_player.familyroom_havoice_mediaplayer"]
DEFAULT_REWASH_SPEAKERS = ["media_player.familyroom_havoice_mediaplayer"]
DEFAULT_REWASH_DELAY_MINUTES = 120
DEFAULT_COMPLETION_MESSAGE = "The washing machine is finished. Please empty it."
DEFAULT_REWASH_MESSAGE = "The washing still has not been emptied. It may need to be rewashed."
DEFAULT_SUPPRESS_IF_DOOR_OPEN = True
DEFAULT_DOOR_SUPPRESSION_WINDOW_SECONDS = 30
DEFAULT_TTS_ENTITY = "tts.home_assistant_cloud"
DEFAULT_TTS_MODE = "speak"
DEFAULT_QUIET_HOURS_POLICY = "defer"
DEFAULT_ANNOUNCEMENT_RETRY_COUNT = 0

# Program catalogue
PROGRAM_CATALOGUE: dict[str, str] = {
    "quick_wash": "Quick Wash",
    "daily_wash": "Daily Wash",
    "bedding": "Bedding",
    "drum_clean": "Drum Clean",
}

PROGRAM_SELECT_OPTIONS = ["auto"] + list(PROGRAM_CATALOGUE.keys())

# Events
EVENT_CYCLE_STARTED = f"{DOMAIN}_cycle_started"
EVENT_PROGRAM_IDENTIFIED = f"{DOMAIN}_program_identified"
EVENT_CYCLE_COMPLETED = f"{DOMAIN}_cycle_completed"
EVENT_CYCLE_EMPTIED = f"{DOMAIN}_cycle_emptied"
EVENT_NEEDS_REWASH = f"{DOMAIN}_needs_rewash"
EVENT_TRAINING_STARTED = f"{DOMAIN}_training_started"
EVENT_TRAINING_SAVED = f"{DOMAIN}_training_saved"
EVENT_TRAINING_CANCELLED = f"{DOMAIN}_training_cancelled"
EVENT_DATA_QUALITY_WARNING = f"{DOMAIN}_data_quality_warning"
EVENT_SHADOW_COMPARISON = f"{DOMAIN}_shadow_comparison"

# Config entry data keys
CONF_POWER_SENSOR = "power_sensor"
CONF_ENERGY_SENSOR = "energy_sensor"
CONF_PLUG_SWITCH = "plug_switch"
CONF_DOOR_SENSOR = "door_sensor"
CONF_MOVEMENT_SENSOR = "movement_sensor"
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_PLUG_LQI_SENSOR = "plug_lqi_sensor"
CONF_DOOR_LQI_SENSOR = "door_lqi_sensor"
CONF_DOOR_BATTERY_SENSOR = "door_battery_sensor"
CONF_DOOR_BATTERY_LOW_SENSOR = "door_battery_low_sensor"

# Options keys
OPT_START_POWER_W = "start_power_w"
OPT_START_SUSTAIN_SECONDS = "start_sustain_seconds"
OPT_START_MIN_ENERGY_WH = "start_min_energy_wh"
OPT_STANDBY_POWER_W = "standby_power_w"
OPT_FALLBACK_COMPLETION_SECONDS = "fallback_completion_seconds"
OPT_EARLY_COMPLETION_ENABLED = "early_completion_enabled"
OPT_EARLY_COMPLETION_MIN_SCORE = "early_completion_min_score"
OPT_DOOR_CORRELATION_SECONDS = "door_correlation_seconds"
OPT_MOVEMENT_ENABLED = "movement_enabled"
OPT_TARGET_LATENCY_SECONDS = "target_latency_seconds"
OPT_MAX_STALE_SECONDS = "max_stale_seconds"
OPT_SHADOW_MODE = "shadow_mode"
OPT_LEGACY_STATUS_MIRROR = "legacy_status_mirror"
OPT_REWASH_DELAY_MINUTES = "rewash_delay_minutes"
OPT_ADVANCED_DIAGNOSTICS = "advanced_diagnostics"
OPT_MIN_RUNS_RECOGNITION = "min_runs_recognition"
OPT_MIN_RUNS_ROBUST = "min_runs_robust"
OPT_RESAMPLE_INTERVAL_SECONDS = "resample_interval_seconds"
OPT_RAW_RUN_RETENTION = "raw_run_retention"
OPT_COMPLETED_HISTORY_RETENTION = "completed_history_retention"
OPT_END_SIGNATURE_PRE_SECONDS = "end_signature_pre_seconds"
OPT_END_SIGNATURE_POST_SECONDS = "end_signature_post_seconds"
OPT_AUTO_INCLUDE_TRAINING_RUNS = "auto_include_training_runs"
OPT_MATCHER_MARGIN = "matcher_margin"
OPT_COMPLETION_ANNOUNCEMENTS_ENABLED = "completion_announcements_enabled"
OPT_REWASH_ANNOUNCEMENTS_ENABLED = "rewash_announcements_enabled"
OPT_COMPLETION_SPEAKERS = "completion_speakers"
OPT_REWASH_SPEAKERS = "rewash_speakers"
OPT_COMPLETION_MESSAGE = "completion_message"
OPT_REWASH_MESSAGE = "rewash_message"
OPT_SUPPRESS_IF_DOOR_OPEN = "suppress_if_door_open"
OPT_DOOR_SUPPRESSION_WINDOW_SECONDS = "door_suppression_window_seconds"
OPT_TTS_ENTITY = "tts_entity"
OPT_TTS_MODE = "tts_mode"
OPT_QUIET_HOURS_START = "quiet_hours_start"
OPT_QUIET_HOURS_END = "quiet_hours_end"
OPT_QUIET_HOURS_POLICY = "quiet_hours_policy"
OPT_ANNOUNCEMENT_RETRY_COUNT = "announcement_retry_count"

PLATFORMS = ["sensor", "binary_sensor", "select"]

SERVICE_START_RECORDING = "start_recording"
SERVICE_MARK_COMPLETE = "mark_complete"
SERVICE_CANCEL_RECORDING = "cancel_recording"
SERVICE_EXCLUDE_RUN = "exclude_run"
SERVICE_INCLUDE_RUN = "include_run"
SERVICE_RELABEL_RUN = "relabel_run"
SERVICE_ADJUST_RUN_START = "adjust_run_start"
SERVICE_ADJUST_RUN_COMPLETE = "adjust_run_complete"
SERVICE_REBUILD_PROFILES = "rebuild_profiles"
SERVICE_EXPORT_RUN = "export_run"
SERVICE_DELETE_RUN = "delete_run"
SERVICE_RELABEL_LAST_CYCLE = "relabel_last_cycle"
SERVICE_FORCE_EMPTY = "force_empty"
SERVICE_EXPORT_DIAGNOSTICS = "export_diagnostics"

ATTR_WASHERCYCLE = "washercycle"
