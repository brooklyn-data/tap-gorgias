"""Gorgias tap class."""

from typing import List

from singer_sdk import Tap, Stream
from singer_sdk import typing as th  # JSON schema typing helpers

from tap_gorgias.streams import (
    TicketsStream,
    MessagesStream,
    SatisfactionSurveysStream,
)

STREAM_TYPES = [
    TicketsStream,
    MessagesStream,
    SatisfactionSurveysStream,
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
            "username",
            th.StringType,
            required=True,
            description="Username to authenticate with",
        ),
        th.Property(
            "password",
            th.StringType,
            required=True,
            description="Password for the user",
        ),
        th.Property(
            "start_date",
            th.DateTimeType,
            description="The earliest record date to sync",
        ),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]
