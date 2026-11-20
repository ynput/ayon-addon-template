"""Server package."""

from typing import Type, cast

from ayon_server.addons import BaseServerAddon
from ayon_server.api.dependencies import CurrentUser
from ayon_server.types import OPModel

from .settings import DEFAULT_VALUES, MySettings


class HelloModel(OPModel):
    """What the studio page shows."""

    message: str


class MyAddon(BaseServerAddon):
    """Add-on class for the server."""

    settings_model: Type[MySettings] = MySettings
    # The web UI part: frontend/src/manifest.ts, built into
    # frontend/dist/modules/my_addon. The key is the federation remote
    # (ayonAddon({ name }) in frontend/vite.config.ts).
    frontend_modules = {"my_addon": ["manifest"]}  # noqa: RUF012

    def initialize(self) -> None:
        """Register the addon's endpoints.

        They are served under /api/addons/{name}/{version}/. In frontend/,
        `yarn generate-rest` turns them into RTK Query endpoints named
        after the method with the addon name in front: `get_hello` becomes
        `useMyAddonGetHelloQuery`.
        """
        self.add_endpoint("/hello", self.get_hello, method="GET")

    async def get_default_settings(self) -> MySettings:
        """Return default settings."""
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_VALUES)

    async def get_hello(self, user: CurrentUser) -> HelloModel:
        """Greet the current user with the greeting from the settings.

        Returns:
            HelloModel: The message the studio page shows.

        """
        settings = cast("MySettings", await self.get_studio_settings())
        return HelloModel(message=f"{settings.greeting}, {user.name}!")
