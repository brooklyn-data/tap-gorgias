"""Tests standard tap features using the built-in SDK tests library."""

import datetime
import io
import os
from contextlib import redirect_stderr, redirect_stdout

import singer
from singer_sdk.testing import get_standard_tap_tests

from tap_gorgias.tap import TapGorgias

SAMPLE_CONFIG = {
    "start_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
    "subdomain": os.getenv("SUBDOMAIN", default=None),
    "email_address": os.getenv("EMAIL_ADDRESS", default=None),
    "api_key": os.getenv("API_KEY", default=None),
}

# Edit these values to match your environment:
EXPECTED_RECORD_COUNT = 363
PAGE_SIZE = 50
EXPECTED_PAGE_COUNT = EXPECTED_RECORD_COUNT // PAGE_SIZE + 1


# Run standard built-in tap tests from the SDK:
def test_standard_tap_tests():
    """Run standard tap tests from the SDK."""

    tests = get_standard_tap_tests(
        TapGorgias,
        config=SAMPLE_CONFIG
    )
    for test in tests:
        test()


def test_if_getting_all_records():
    """Test if we get All Record from the Satisfaction Surveys endpoint."""
    tap = TapGorgias(config={**SAMPLE_CONFIG, "page_size": PAGE_SIZE}, parse_env_config=True)

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
        streams = tap.load_streams()
        for stream in streams:
            if stream.tap_stream_id == "satisfaction_surveys":
                stream.sync()
    stdout_buf.seek(0)
    stderr_buf.seek(0)

    record_count = 0
    for message in stdout_buf:
        o = singer.parse_message(message).asdict()
        if o['type'] == 'RECORD':
            record_count += 1

    assert record_count == EXPECTED_RECORD_COUNT


def test_paging():
    tap = TapGorgias(config={**SAMPLE_CONFIG, "page_size": PAGE_SIZE}, parse_env_config=True)

    page_count = 0

    def counter(fn):
        def inner(*args, **kwargs):
            nonlocal page_count
            page_count += 1
            return fn(*args, **kwargs)

        return inner

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
        streams = tap.load_streams()
        for stream in streams:
            # Restrict to the Satisfaction Surveys stream as this usually is small to query and has multiple pages.
            if stream.tap_stream_id == "satisfaction_surveys":
                stream.prepare_request = counter(stream.prepare_request)
                stream.sync()
    stdout_buf.seek(0)
    stderr_buf.seek(0)

    assert page_count == EXPECTED_PAGE_COUNT
