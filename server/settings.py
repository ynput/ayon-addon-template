"""Settings for the addon."""

from typing import Any

from ayon_server.settings import BaseSettingsModel, SettingsField

DEFAULT_VALUES: dict[str, Any] = {
    "greeting": "Hello",
}


class MySettings(BaseSettingsModel):
    """Settings for the addon."""

    greeting: str = SettingsField(
        "Hello",
        title="Greeting",
        description="The first word of the studio page's message.",
    )
