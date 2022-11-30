"""REST client handling, including GorgiasStream base class."""

import time
from typing import Dict, Optional, Any

import requests
from singer_sdk.helpers.jsonpath import extract_jsonpath

from singer_sdk.streams import RESTStream
from singer_sdk.authenticators import BasicAuthenticator
from singer_sdk.exceptions import FatalAPIError, RetriableAPIError


class GorgiasStream(RESTStream):
    """Gorgias stream class."""

    # Most of the endpoints of the API returning a large number of resources are paginated.
    # Cursor-based pagination provides lower latency when listing resources.
    # Views use a custom path for the cursor value.
    # https://developers.gorgias.com/reference/pagination
    next_page_token_jsonpath = "$.meta.next_cursor"

    # Generic jsonpath, a list of resources. E.g: a list of tickets.
    # https://developers.gorgias.com/reference/pagination#response-attributes
    records_jsonpath = "$.data[*]"

    http_headers = {"Accept": "application/json", "Content-Type": "application/json"}
    _LOG_REQUEST_METRIC_URLS = True

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
            username=self.config.get("email_address"),
            password=self.config.get("api_key"),
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

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization.

        If paging is supported, developers may override with specific paging logic.

        Args:
            context: Stream partition or context dictionary.
            next_page_token: Token, page number or any request argument to request the
                next page of data.

        Returns:
            Dictionary of URL query parameters to use in the request.
        """
        return {"cursor": next_page_token, "limit": self.config["page_size"]}

    def get_next_page_token(
        self, response: requests.Response, previous_token: Optional[Any]
    ) -> Any:
        """Return token identifying next page or None if all records have been read.

        Args:
            response: A raw `requests.Response`_ object.
            previous_token: Previous pagination reference.

        Returns:
            Reference value to retrieve next page.

        .. _requests.Response:
            https://docs.python-requests.org/en/latest/api/#requests.Response
        """
        all_matches = extract_jsonpath(self.next_page_token_jsonpath, response.json())
        first_match = next(iter(all_matches), None)
        next_page_token = first_match
        return next_page_token

    def response_error_message(self, response: requests.Response) -> str:
            """Build error message for invalid http statuses.
            WARNING - Override this method when the URL path may contain secrets or PII
            Args:
                response: A `requests.Response`_ object.
            Returns:
                str: The error message
            """
            full_path = response.url
            if 400 <= response.status_code < 500:
                error_type = "Client"
            else:
                error_type = "Server"

            return (
                f"{response.__dict__}"
                f"full path:{full_path}"
                f"{response.status_code} {error_type} Error: "
                f"{response.reason} for path: {full_path}"
            )