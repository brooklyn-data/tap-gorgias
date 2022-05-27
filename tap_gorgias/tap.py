"""Gorgias tap class."""

from typing import List

from singer_sdk import Tap, Stream
from singer_sdk import typing as th  # JSON schema typing helpers

from tap_gorgias.streams import (
    TicketsStream,
    MessagesStream,
    SatisfactionSurveysStream,
    CustomersStream
)

STREAM_TYPES = [
    TicketsStream,
    MessagesStream,
    SatisfactionSurveysStream,
    # CustomersStream
]


class TapGorgias(Tap):
    """Gorgias tap class."""

    name = "tap-gorgias"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "subdomain",
            th.StringType,
            required=True,
            description="Subdomain (<subdomain>.gorgias.com)",
        ),
        th.Property(
            "email_address",
            th.StringType,
            required=True,
            description="Email address to authenticate with",
        ),
        th.Property(
            "api_key",
            th.StringType,
            required=True,
            description="API key generated by the user",
        ),
        th.Property(
            "start_date",
            th.DateTimeType,
            description="The earliest record date to sync",
        ),
        th.Property(
            "page_size",
            th.IntegerType,
            default=100,
            description="The page size for each list endpoint call",
        ),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]
