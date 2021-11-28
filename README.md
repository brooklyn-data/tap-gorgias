# tap-gorgias

`tap-gorgias` is a Singer tap for Gorgias.

Built with the [Meltano Tap SDK](https://sdk.meltano.com) for Singer Taps.

## Resources

This tap extracts:
- Tickets (incremental based on the ticket's `updated_datetime`, `last_message_datetime`, or `last_received_message_datetime`)
- Ticket messages (incremental, extracts messages for all tickets retrieved in the ticket parent stream per above conditions)
- Satisfactions surveys (full sync only due to lack of filtering in the API)

## Installation

```bash
pipx install tap-gorgias
```

## Configuration

### Accepted Config Options

- `subdomain` (\<subdomain>.gorgias.com)
- `username` (Login email address)
- `password` (Login password)
- `start_date` (Date to start syncing tickets and corresponding messages from based on the ticket's `updated_datetime`, `last_message_datetime`, or `last_received_message_datetime`)

A full list of supported settings and capabilities for this
tap is available by running:

```bash
tap-gorgias --about
```

## Usage

You can easily run `tap-gorgias` by itself or in a pipeline using [Meltano](https://meltano.com/).

### Executing the Tap Directly

```bash
tap-gorgias --version
tap-gorgias --help
tap-gorgias --config CONFIG --discover > ./catalog.json
```

## Developer Resources

### Initialize your Development Environment

```bash
pipx install poetry
poetry install
```

### Testing with [Meltano](https://www.meltano.com)

_**Note:** This tap will work in any Singer environment and does not require Meltano.
Examples here are for convenience and to streamline end-to-end orchestration scenarios._

Install Meltano (if you haven't already) and any needed plugins:

```bash
# Install meltano
pipx install meltano
# Initialize meltano within this directory
cd tap-gorgias
meltano install
```

Now you can test and orchestrate using Meltano:

```bash
# Test invocation:
meltano invoke tap-gorgias --version
# OR run a test `elt` pipeline:
meltano elt tap-gorgias target-jsonl
```

### SDK Dev Guide

See the [dev guide](https://sdk.meltano.com/en/latest/dev_guide.html) for more instructions on how to use the SDK to
develop your own taps and targets.
