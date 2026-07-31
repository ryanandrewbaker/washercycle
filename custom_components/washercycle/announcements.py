"""Announcement handling for WasherCycle."""

from __future__ import annotations

import logging
from datetime import datetime, timezone, time
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    DEFAULT_COMPLETION_MESSAGE,
    DEFAULT_REWASH_MESSAGE,
    DEFAULT_TTS_ENTITY,
    DEFAULT_TTS_MODE,
    OPT_COMPLETION_ANNOUNCEMENTS_ENABLED,
    OPT_COMPLETION_MESSAGE,
    OPT_COMPLETION_SPEAKERS,
    OPT_QUIET_HOURS_END,
    OPT_QUIET_HOURS_POLICY,
    OPT_QUIET_HOURS_START,
    OPT_REWASH_ANNOUNCEMENTS_ENABLED,
    OPT_REWASH_MESSAGE,
    OPT_REWASH_SPEAKERS,
    OPT_SUPPRESS_IF_DOOR_OPEN,
    OPT_TTS_ENTITY,
    OPT_TTS_MODE,
)

_LOGGER = logging.getLogger(__name__)


class AnnouncementManager:
    """Idempotent TTS announcement dispatch."""

    def __init__(
        self,
        hass: HomeAssistant,
        options: dict[str, Any],
        announcement_state: dict[str, Any],
    ) -> None:
        self.hass = hass
        self.options = options
        self._state = announcement_state

    @property
    def state(self) -> dict[str, Any]:
        return self._state

    def should_suppress_completion(
        self,
        cycle_id: str,
        *,
        door_open: bool,
        immediately_emptied: bool,
    ) -> bool:
        """Check if completion announcement should be suppressed."""
        if immediately_emptied:
            return True
        if self._state.get(f"completion_{cycle_id}"):
            return True
        if self.options.get(OPT_SUPPRESS_IF_DOOR_OPEN, True) and door_open:
            return True
        return False

    def is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours."""
        start_str = self.options.get(OPT_QUIET_HOURS_START)
        end_str = self.options.get(OPT_QUIET_HOURS_END)
        if not start_str or not end_str:
            return False
        try:
            start = time.fromisoformat(start_str)
            end = time.fromisoformat(end_str)
            now = datetime.now().time()
            if start <= end:
                return start <= now <= end
            return now >= start or now <= end
        except ValueError:
            return False

    async def announce_completion(
        self,
        cycle_id: str,
        *,
        door_open: bool = False,
        immediately_emptied: bool = False,
    ) -> bool:
        """Dispatch completion announcement."""
        if not self.options.get(OPT_COMPLETION_ANNOUNCEMENTS_ENABLED, False):
            return False
        if self.should_suppress_completion(
            cycle_id, door_open=door_open, immediately_emptied=immediately_emptied
        ):
            _LOGGER.debug("Suppressing completion announcement for %s", cycle_id)
            return False
        if self.is_quiet_hours():
            policy = self.options.get(OPT_QUIET_HOURS_POLICY, "defer")
            if policy == "skip":
                return False

        message = self.options.get(OPT_COMPLETION_MESSAGE, DEFAULT_COMPLETION_MESSAGE)
        speakers = self.options.get(OPT_COMPLETION_SPEAKERS, [])
        dispatched = await self._speak(message, speakers)
        if dispatched:
            self._state[f"completion_{cycle_id}"] = datetime.now(timezone.utc).isoformat()
        return dispatched

    async def announce_rewash(self, cycle_id: str) -> bool:
        """Dispatch rewash announcement."""
        if not self.options.get(OPT_REWASH_ANNOUNCEMENTS_ENABLED, False):
            return False
        if self._state.get(f"rewash_{cycle_id}"):
            return False

        message = self.options.get(OPT_REWASH_MESSAGE, DEFAULT_REWASH_MESSAGE)
        speakers = self.options.get(OPT_REWASH_SPEAKERS, [])
        dispatched = await self._speak(message, speakers)
        if dispatched:
            self._state[f"rewash_{cycle_id}"] = datetime.now(timezone.utc).isoformat()
        return dispatched

    async def _speak(self, message: str, speakers: list[str]) -> bool:
        """Call TTS for each speaker."""
        if not speakers:
            return False

        tts_mode = self.options.get(OPT_TTS_MODE, DEFAULT_TTS_MODE)
        tts_entity = self.options.get(OPT_TTS_ENTITY, DEFAULT_TTS_ENTITY)
        dispatched = False

        for speaker in speakers:
            try:
                if tts_mode == "cloud_say":
                    await self.hass.services.async_call(
                        "tts",
                        "cloud_say",
                        {"entity_id": speaker, "message": message, "cache": False},
                        blocking=True,
                    )
                else:
                    await self.hass.services.async_call(
                        "tts",
                        "speak",
                        {
                            "entity_id": tts_entity,
                            "media_player_entity_id": speaker,
                            "message": message,
                            "cache": False,
                        },
                        blocking=True,
                    )
                dispatched = True
                _LOGGER.info("Announcement dispatched to %s", speaker)
            except Exception:
                _LOGGER.exception("Failed to dispatch announcement to %s", speaker)

        return dispatched
