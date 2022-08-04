"""Stream type classes for tap-gorgias."""
from urllib import parse
from datetime import datetime
import logging
import requests
from typing import Any, Dict, Optional, Iterable, cast
from singer_sdk import typing as th  # JSON Schema typing helpers

from tap_gorgias.client import GorgiasStream

logger = logging.getLogger(__name__)

CUSTOMER_SCHEMA = [
    th.ObjectType(
        th.Property("id", th.IntegerType),
        th.Property("email", th.StringType),
        th.Property("name", th.StringType),
        th.Property("firstname", th.StringType),
        th.Property("lastname", th.StringType),
    )
]


class TicketsStream(GorgiasStream):
    """Define custom stream."""

    name = "tickets"
    path = "/api/views/{view_id}/items"
    primary_keys = ["id"]
    replication_key = "updated_datetime"
    is_sorted = True

    # Link to the next items, if any.
    next_page_token_jsonpath = "$.meta.next_items"

    schema = th.PropertiesList(
        th.Property(
            "id",
            th.IntegerType
        ),
        th.Property(
            "uri",
            th.StringType
        ),
        th.Property(
            "external_id",
            th.StringType
        ),
        th.Property(
            "language",
            th.StringType
        ),
        th.Property(
            "status",
            th.StringType
        ),
        th.Property(
            "priority",
            th.StringType
        ),
        th.Property(
            "channel",
            th.StringType
        ),
        th.Property(
            "via",
            th.StringType
        ),
        th.Property(
            "from_agent",
            th.BooleanType
        ),
        th.Property(
            "requester",
            *CUSTOMER_SCHEMA
        ),
        th.Property(
            "customer",
            *CUSTOMER_SCHEMA
        ),
        th.Property(
            "assignee_user",
            *CUSTOMER_SCHEMA
        ),
        th.Property(
            "assignee_team",
            th.ObjectType(
                th.Property(
                    "id",
                    th.IntegerType
                ),
                th.Property(
                    "name",
                    th.StringType
                ),
                th.Property(
                    "decoration",
                    th.ObjectType(
                        th.Property(
                            "emoji",
                            th.ObjectType(
                                th.Property(
                                    "id",
                                    th.StringType
                                ),
                                th.Property(
                                    "name",
                                    th.StringType
                                ),
                                th.Property(
                                    "skin",
                                    th.IntegerType
                                ),
                                th.Property(
                                    "colons",
                                    th.StringType
                                ),
                                th.Property(
                                    "native",
                                    th.StringType
                                ),
                                th.Property(
                                    "unified",
                                    th.StringType
                                ),
                            )
                        )
                    )
                )
            )
        ),
        th.Property(
            "subject",
            th.StringType
        ),
        th.Property(
            "excerpt",
            th.StringType
        ),
        th.Property(
            "integrations",
            th.ArrayType(
                th.ObjectType(
                    th.Property(
                        "name",
                        th.StringType
                    ),
                    th.Property(
                        "address",
                        th.StringType
                    ),
                    th.Property(
                        "type",
                        th.StringType
                    ),
                )
            )
        ),
        th.Property(
            "tags",
            th.ArrayType(
                th.ObjectType(
                    th.Property(
                        "id",
                        th.IntegerType
                    ),
                    th.Property(
                        "name",
                        th.StringType
                    ),
                    th.Property(
                        "uri",
                        th.StringType
                    ),
                )
            )
        ),
        th.Property(
            "messages_count",
            th.IntegerType
        ),
        th.Property(
            "is_unread",
            th.BooleanType
        ),
        th.Property(
            "spam",
            th.BooleanType
        ),
        th.Property(
            "created_datetime",
            th.DateTimeType
        ),
        th.Property(
            "opened_datetime",
            th.DateTimeType
        ),
        th.Property(
            "last_received_message_datetime",
            th.DateTimeType
        ),
        th.Property(
            "last_message_datetime",
            th.DateTimeType
        ),
        th.Property(
            "updated_datetime",
            th.DateTimeType
        ),
        th.Property(
            "closed_datetime",
            th.DateTimeType
        ),
        th.Property(
            "snooze_datetime",
            th.DateTimeType
        ),
        th.Property(
            "trashed_datetime",
            th.DateTimeType
        ),
    ).to_dict()

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
        params = self.get_url_params(context, next_page_token)

        request_data = self.prepare_request_payload(context, next_page_token)

        headers = self.get_headers()

        request = cast(
            requests.PreparedRequest,
            self.requests_session.prepare_request(
                requests.Request(
                    method=http_method,
                    url=self.get_url(context),
                    params=params,
                    headers=headers,
                    json=request_data,
                )
            ),
        )
        return request

    def get_current_user_id(self) -> int:
        headers = self.get_headers()
        decorated_request = self.request_decorator(self._request)
        prepared_request = cast(
            requests.PreparedRequest,
            self.requests_session.prepare_request(
                requests.Request(
                    method="get",
                    url=self.url_base + "/api/users/0",
                    headers=headers,
                ),
            ),
        )
        resp = decorated_request(prepared_request, None)
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
        logger.info(f"Creating ticket view with parameters {payload}")
        decorated_request = self.request_decorator(self._request)
        prepared_request = cast(
            requests.PreparedRequest,
            self.requests_session.prepare_request(
                requests.Request(
                    method="post",
                    url=self.url_base + "/api/views",
                    headers=headers,
                    json=payload,
                ),
            ),
        )
        resp = decorated_request(prepared_request, None)
        logger.info("View successfully created.")
        view_id = resp.json()["id"]
        return view_id

    def delete_ticket_view(self, view_id: int) -> None:
        headers = self.get_headers()
        decorated_request = self.request_decorator(self._request)
        prepared_request = cast(
            requests.PreparedRequest,
            self.requests_session.prepare_request(
                requests.Request(
                    method="delete",
                    url=self.url_base + f"/api/views/{view_id}/",
                    headers=headers,
                ),
            ),
        )
        resp = decorated_request(prepared_request, None)
        logger.info(f"Deleted ticket view {view_id}")

    def get_records(self, context: Optional[dict]) -> Iterable[Dict[str, Any]]:
        """Return a generator of row-type dictionary objects.

        Each row emitted should be a dictionary of property names to their values.

        Args:
            context: Stream partition or context dictionary.

        Yields:
            One item per (possibly processed) record in the API.
        """
        sync_start_datetime = self.get_starting_timestamp(context)
        logger.info(f"Starting timestamp: {sync_start_datetime}")
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

    def get_url_params(
            self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return the URL parameters for the request.

        For the Tickets stream, the next cursor is returned in a querystring parameter under the path $.meta.next_items
        so here we parse the whole url query string in order to extract the cursor.

        """
        next_page_url_query = parse.parse_qs(next_page_token)
        if not next_page_url_query:
            return {"limit": self.config["page_size"]}
        else:
            return {"limit": self.config["page_size"], "cursor": next_page_url_query["cursor"][0], "direction": "next"}


class MessagesStream(GorgiasStream):
    """Messages stream.

    Uses tickets as a parent stream. Consequently, only retrieves
    messages for tickets included in the ticket view. The ticket
    view contains filters for last_message_datetime and
    last_received_message_datetime to capture all new messages.
    """

    name = "messages"
    parent_stream_type = TicketsStream
    path = "/api/tickets/{ticket_id}/messages"
    primary_keys = ["id"]
    state_partitioning_keys = []

    schema = th.PropertiesList(
        th.Property(
            "id",
            th.IntegerType,
        ),
        th.Property(
            "uri",
            th.StringType,
        ),
        th.Property(
            "message_id",
            th.StringType,
        ),
        th.Property(
            "ticket_id",
            th.IntegerType,
        ),
        th.Property(
            "external_id",
            th.StringType,
        ),
        th.Property(
            "public",
            th.BooleanType
        ),
        th.Property(
            "channel",
            th.StringType,
        ),
        th.Property(
            "via",
            th.StringType,
        ),
        th.Property(
            "source",
            th.ObjectType(
                th.Property(
                    "type",
                    th.StringType
                ),
                th.Property(
                    "to",
                    th.ArrayType(
                        th.ObjectType(
                            th.Property(
                                "name",
                                th.StringType
                            ),
                            th.Property(
                                "address",
                                th.StringType
                            )
                        )
                    ),
                ),
                th.Property(
                    "from",
                    th.ObjectType(
                        th.Property(
                            "name",
                            th.StringType
                        ),
                        th.Property(
                            "address",
                            th.StringType
                        ),
                    ),
                ),
            )
        ),
        th.Property(
            "sender",
            *CUSTOMER_SCHEMA
        ),
        th.Property(
            "integration_id",
            th.IntegerType,
        ),
        th.Property(
            "rule_id",
            th.IntegerType,
        ),
        th.Property(
            "from_agent",
            th.BooleanType
        ),
        th.Property(
            "receiver",
            *CUSTOMER_SCHEMA
        ),
        th.Property(
            "subject",
            th.StringType,
        ),
        th.Property(
            "body_text",
            th.StringType,
        ),
        th.Property(
            "body_html",
            th.StringType,
        ),
        th.Property(
            "stripped_text",
            th.StringType,
        ),
        th.Property(
            "stripped_html",
            th.StringType,
        ),
        th.Property(
            "stripped_signature",
            th.StringType,
        ),
        # th.Property(
        #     "actions",
        #     th.ArrayType(
        #         th.ObjectType()
        #     ),
        # ),
        th.Property(
            "created_datetime",
            th.DateTimeType,
        ),
        th.Property(
            "sent_datetime",
            th.DateTimeType
        ),
        th.Property(
            "failed_datetime",
            th.DateTimeType
        ),
        th.Property(
            "deleted_datetime",
            th.DateTimeType
        ),
        th.Property(
            "opened_datetime",
            th.DateTimeType
        )
    ).to_dict()


class SatisfactionSurveysStream(GorgiasStream):
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

    primary_keys = ["id"]
    schema = th.PropertiesList(
        th.Property(
            "id",
            th.IntegerType
        ),
        th.Property(
            "body_text",
            th.StringType
        ),
        th.Property(
            "created_datetime",
            th.DateTimeType
        ),
        th.Property(
            "customer_id",
            th.IntegerType
        ),
        th.Property(
            "score",
            th.IntegerType
        ),
        th.Property(
            "scored_datetime",
            th.DateTimeType
        ),
        th.Property(
            "sent_datetime",
            th.DateTimeType
        ),
        th.Property(
            "should_send_datetime",
            th.DateTimeType
        ),
        th.Property(
            "ticket_id",
            th.IntegerType
        ),
        th.Property(
            "uri",
            th.StringType
        )
    ).to_dict()


class CustomersStream(GorgiasStream):
    """Customers.

    The customers API endpoint does not allow any filtering or
    custom ordering of the results, only on created datetime.
    This has to be run as a full refresh for each extraction, due to the
    inability to filter and lack of ordering by updated_datetime..
    https://developers.gorgias.com/reference/get_api-customers
    """

    name = "customers"
    path = "/api/customers"
    primary_keys = ["id"]

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType),
        th.Property("created_datetime", th.DateTimeType),
        th.Property("email", th.StringType),
        th.Property("external_id", th.StringType),
        th.Property("firstname", th.StringType),
        th.Property("language", th.StringType),
        th.Property("lastname", th.StringType),
        th.Property("name", th.StringType),
        th.Property("timezone", th.StringType),
        th.Property("updated_datetime", th.DateTimeType),
        th.Property("note", th.StringType),
        th.Property("active", th.BooleanType),
        th.Property(
            "meta",
            th.ObjectType(
                th.Property("name_set_via", th.StringType),
            ),
        ),
        th.Property("error", th.StringType),
    ).to_dict()
