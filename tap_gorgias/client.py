"""REST client handling, including GorgiasStream base class."""

from singer_sdk.streams import RESTStream
from singer_sdk.authenticators import BasicAuthenticator

from typing import Dict


class GorgiasStream(RESTStream):
    """Gorgias stream class."""

    @property
    def url_base(self) -> str:
        """Return the API URL root, configurable via tap settings."""
        return f"https://{self.config['subdomain']}.gorgias.com"

    def get_headers(self) -> Dict:
        headers = self.http_headers
        authenticator = self.authenticator
        headers.update(authenticator.auth_headers)
        return headers

    @property
    def authenticator(self) -> BasicAuthenticator:
        """Return a new authenticator object."""
        return BasicAuthenticator.create_for_stream(
            self,
            username=self.config.get("username"),
            password=self.config.get("password"),
        )

    http_headers = {"Accept": "application/json", "Content-Type": "application/json"}
