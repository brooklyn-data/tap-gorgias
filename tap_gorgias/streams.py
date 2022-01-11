"""Stream type classes for tap-gorgias."""

from datetime import datetime
from pathlib import Path
import logging
import requests
from typing import Any, Dict, Optional, Iterable, cast

from tap_gorgias.client import GorgiasStream

SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


class TicketsStream(GorgiasStream):
    """Define custom stream."""

    name = "tickets"
    path = "/api/views/{view_id}/items"
    records_jsonpath = "$.data[*]"
    next_page_token_jsonpath = "$.meta.next_items"
    primary_keys = ["id"]
    replication_key = "updated_datetime"
    schema_filepath = SCHEMAS_DIR / "tickets.json"
    is_sorted = True

    def prepare_request(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> requests.PreparedRequest:
        """Prepare a request object.

        If partitioning is supported, the `context` object will contain the partition
        definitions. Pagination information can be parsed from `next_page_token` if
        `next_page_token` is not None.

        Args:
            context: Stream partition or context dictionary.
            next_page_token: Token, page number or any request argument to request the
                next page of data.

        Returns:
            Build a request with the stream's URL, path, query parameters,
            HTTP headers and authenticator.
        """
        http_method = self.rest_method
        url: str = ""
        params: dict = {}
        # The next page token is actually a url path returned
        # by the API, so append it to the url base
        if not next_page_token:
            url = (
                self.get_url(context) + f"?limit={self.config['ticket_view_page_size']}"
            )
        else:
            url = (
                self.url_base
                + next_page_token
                + f"&limit={self.config['ticket_view_page_size']}"
            )
        request_data = self.prepare_request_payload(context, next_page_token)

        headers = self.get_headers()

        request = cast(
            requests.PreparedRequest,
            self.requests_session.prepare_request(
                requests.Request(
                    method=http_method,
                    url=url,
                    params=params,
                    headers=headers,
                    json=request_data,
                )
            ),
        )
        return request

    def get_current_user_id(self) -> int:
        headers = self.get_headers()
        resp = requests.get(self.url_base + "/api/users/0", headers=headers)
        resp.raise_for_status()
        return resp.json()["id"]

    def create_ticket_view(self, sync_start_datetime: datetime) -> int:
        headers = self.get_headers()
        current_user_id = self.get_current_user_id()
        payload = {
            "category": "user",
            "order_by": "updated_datetime",
            "order_dir": "asc",
            "visibility": "private",
            "shared_with_users": [current_user_id],
            "type": "ticket-list",
            "slug": "could-be-anything",
        }
        if sync_start_datetime:
            payload.update(
                {
                    "filters": f"gte(ticket.updated_datetime, '{sync_start_datetime.isoformat()}')"
                }
            )
        logging.info(f"Creating ticket view with parameters {payload}")
        resp = requests.post(
            self.url_base + "/api/views", headers=headers, json=payload
        )
        resp.raise_for_status()
        logging.info("View successfully created.")
        view_id = resp.json()["id"]
        return view_id

    def delete_ticket_view(self, view_id: int) -> None:
        headers = self.get_headers()
        resp = requests.delete(
            self.url_base + f"/api/views/{view_id}/", headers=headers
        )
        resp.raise_for_status()
        logging.info(f"Deleted ticket view {view_id}")

    def get_records(self, context: Optional[dict]) -> Iterable[Dict[str, Any]]:
        """Return a generator of row-type dictionary objects.

        Each row emitted should be a dictionary of property names to their values.

        Args:
            context: Stream partition or context dictionary.

        Yields:
            One item per (possibly processed) record in the API.
        """
        sync_start_datetime = self.get_starting_timestamp(context)
        logging.info(f"Starting timestamp: {sync_start_datetime}")
        view_id = self.create_ticket_view(sync_start_datetime)
        context = context or {}
        context["view_id"] = view_id
        try:
            for record in self.request_records(context):
                transformed_record = self.post_process(record, context)
                if transformed_record is None:
                    # Record filtered out during post_process()
                    continue
                yield transformed_record
        finally:
            # Always delete the ticket view even if an exception is raised
            self.delete_ticket_view(view_id)

    def get_child_context(self, record: dict, context: Optional[dict]) -> dict:
        """Return the ticket_id for use by child streams."""
        return {"ticket_id": record["id"]}


class PaginatedGorgiasStream(GorgiasStream):
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
        return {"page": next_page_token}

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
        num_pages = response.json()["meta"]["nb_pages"]
        page = response.json()["meta"]["page"]
        if num_pages > page:
            return page + 1


class MessagesStream(PaginatedGorgiasStream):
    """Messages stream.

    Uses tickets as a parent stream. Consequently, only retrieves
    messages for tickets included in the ticket view. The ticket
    view contains filters for last_message_datetime and
    last_received_message_datetime to capture all new messages.
    """

    name = "messages"
    parent_stream_type = TicketsStream
    path = "/api/tickets/{ticket_id}/messages"
    records_jsonpath = "$.data[*]"
    primary_keys = ["id"]
    schema_filepath = SCHEMAS_DIR / "messages.json"
    state_partitioning_keys = []


class SatisfactionSurveysStream(PaginatedGorgiasStream):
    """Satisfaction surveys.

    The satisfaction survey API endpoint does not allow any filtering or
    custom ordering of the results. It also has no cursor, so if records
    are added while paging through the results, records will be missed.
    This has to be run as a full refresh for each extraction, due to the
    inability to filter and lack of clear updated_datetime field on the
    survey object.
    https://developers.gorgias.com/reference/the-satisfactionsurvey-object
    https://developers.gorgias.com/reference/get_api-satisfaction-surveys
    """

    name = "satisfaction_surveys"
    path = "/api/satisfaction-surveys"
    records_jsonpath = "$.data[*]"
    primary_keys = ["id"]
    schema_filepath = SCHEMAS_DIR / "satisfaction_surveys.json"
