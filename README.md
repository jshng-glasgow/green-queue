# Green Queue

Green Queue displays the current carbon intensity and generation mix for a
UK electricity region, together with statistics for the previous
and next 24 hours. It is intended to help you choose a lower-carbon time to
submit flexible HPC workloads.

Data comes from the [National Energy System Operator Carbon Intensity API](https://api.carbonintensity.org.uk/).

## Requirements

- Python 3.11 or later
- Network access to `api.carbonintensity.org.uk`

## Installation

Create a virtual environment and install the project:

```console
$ python3 -m venv ~/.local/green-queue
$ ~/.local/green-queue/bin/pip install /path/to/green-compute
```

The command is then available at:

```console
$ ~/.local/green-queue/bin/green-queue status
```

To make `green-queue` available without its full path on future logins, add
this line to `~/.bashrc`:

```bash
export PATH="$HOME/.local/green-queue/bin:$PATH"
```

Reload the shell and run the command normally:

```console
$ source ~/.bashrc
$ green-queue status
```

For development, install the checkout in editable mode with its test tools:

```console
$ python3 -m venv .venv
$ source .venv/bin/activate
$ python -m pip install -e '.[test]'
```

## Usage

Show the status for South Scotland:

```console
$ green-queue status
```

Select another API region or change the per-request timeout:

```console
$ green-queue status --region "North Scotland" --timeout 5
```

Run `green-queue status --help` to see all status options. If the API cannot be
reached, the command prints a concise error and returns a non-zero exit code.

Times are returned by the API in UTC and displayed in the machine's local
timezone.

## License

Green Queue is licensed under the [Creative Commons Attribution 4.0
International License](LICENSE).
