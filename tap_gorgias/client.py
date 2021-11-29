"""REST client handling, including GorgiasStream base class."""

import time
from typing import Dict

import requests

from singer_sdk.streams import RESTStream
from singer_sdk.authenticators import BasicAuthenticator
from singer_sdk.exceptions import FatalAPIError, RetriableAPIError

class GorgiasStream(RESTStream):
    """Gorgias stream class."""

    http_headers = {"Accept": "application/json", "Content-Type": "application/json"}

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

    def validate_response(self, response: requests.Response) -> None:
        """Validate HTTP response.

        By default, checks for error status codes (>400) and raises a
        :class:`singer_sdk.exceptions.FatalAPIError`.

        Tap developers are encouraged to override this method if their APIs use HTTP
        status codes in non-conventional ways, or if they communicate errors
        differently (e.g. in the response body).

        .. image:: ../images/200.png


        In case an error is deemed transient and can be safely retried, then this
        method should raise an :class:`singer_sdk.exceptions.RetriableAPIError`.

        Args:
            response: A `requests.Response`_ object.

        Raises:
            FatalAPIError: If the request is not retriable.
            RetriableAPIError: If the request is retriable.

        .. _requests.Response:
            https://docs.python-requests.org/en/latest/api/#requests.Response
        """
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-after", 0))
            msg = (
                f"{response.status_code} Server Error: "
                f"{response.reason} for path: {self.path}. "
                f"Waiting for 'Retry-after' value of {retry_after}."
            )
            time.sleep(retry_after)
            raise RetriableAPIError(msg)
        elif 400 <= response.status_code < 500:
            msg = (
                f"{response.status_code} Client Error: "
                f"{response.reason} for path: {self.path}"
            )
            raise FatalAPIError(msg)
        elif 500 <= response.status_code < 600:
            msg = (
                f"{response.status_code} Server Error: "
                f"{response.reason} for path: {self.path}"
            )
            raise RetriableAPIError(msg)
