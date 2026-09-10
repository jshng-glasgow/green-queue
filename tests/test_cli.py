from unittest.mock import Mock, patch

import requests

from green_queue.cli import main


@patch("green_queue.cli.DataVisualizer")
@patch("green_queue.cli.DataFetcher")
def test_status_command_passes_options_to_fetcher(fetcher, visualizer) -> None:
    result = main(["status", "--region", "North Scotland", "--timeout", "4"])

    assert result == 0
    fetcher.assert_called_once_with(region="North Scotland", timeout=4.0)
    visualizer.assert_called_once_with(fetcher.return_value)
    visualizer.return_value.display.assert_called_once_with()


@patch("green_queue.cli.DataVisualizer")
def test_status_command_returns_failure_for_network_errors(visualizer, capsys) -> None:
    instance = Mock()
    instance.display.side_effect = requests.Timeout("too slow")
    visualizer.return_value = instance

    result = main(["status"])

    assert result == 1
    assert "unable to retrieve grid status: too slow" in capsys.readouterr().err
