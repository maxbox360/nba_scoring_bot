import logging
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

import pandas as pd
import requests

from nba import nba_main, nba_utils
from utils import calculate_ranking, posts, settings


class RankingTests(unittest.TestCase):
    def test_ordinal_suffix_handles_teens_and_regular_ordinals(self):
        for number, suffix in {1: "st", 2: "nd", 3: "rd", 4: "th", 11: "th", 21: "st"}.items():
            with self.subTest(number=number):
                self.assertEqual(calculate_ranking.get_ordinal_suffix(number), suffix)

    def test_passed_players_and_next_tied_rank(self):
        table = pd.DataFrame([
            {"PLAYER_NAME": "Alpha", "PTS_RANK": 1, "PTS": 1000},
            {"PLAYER_NAME": "Bravo", "PTS_RANK": 2, "PTS": 900},
            {"PLAYER_NAME": "Charlie", "PTS_RANK": 2, "PTS": 900},
        ])

        self.assertEqual(
            calculate_ranking.get_passed_player(["Bravo"], 950, table),
            [("Bravo", 2, 50)],
        )
        self.assertEqual(
            calculate_ranking.get_next_player(3, 950, table),
            ("Bravo, Charlie", 2, "-49"),
        )


class PostTests(unittest.TestCase):
    def setUp(self):
        self.post_data = {
            "player_name": "New Player",
            "current_rank": 10,
            "ordinal_suffix": "th",
            "points": 12345,
            "difference_to_next": "100",
            "next_name": "Next Player",
            "next_player_rank": 9,
            "next_ordinal_suffix": "th",
        }

    def compose(self, names):
        return posts.compose_post({
            **self.post_data,
            "players_passed_info": [(name, rank, 1) for rank, name in enumerate(names)],
        })

    def test_formats_one_two_and_multiple_passed_players(self):
        expected = {
            ("A",): "passing: A.",
            ("A", "B"): "passing: A and B.",
            ("A", "B", "C"): "passing: A, B, and C.",
        }
        for names, text in expected.items():
            with self.subTest(names=names):
                self.assertIn(text, self.compose(names))

    def test_long_multi_player_post_uses_short_fallback(self):
        post = self.compose([f"Player Name {index} " * 3 for index in range(10)])
        self.assertIn("and others.", post)
        self.assertLessEqual(len(post), 280)

    def test_formats_tied_next_players(self):
        self.assertEqual(posts.get_next_players("A, B, C"), "A, B, and C")
        self.assertEqual(posts.get_next_players("A, B"), "A and B")


class NBAUtilsTests(unittest.TestCase):
    def test_fetch_builds_dataframe_and_retries_request_errors(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "resultSet": {"headers": ["PLAYER_ID"], "rowSet": [[1], [2]]}
        }
        with patch.object(nba_utils.requests, "get", side_effect=[requests.ConnectionError, response]) as get:
            with patch.object(nba_utils, "sleep") as sleep:
                table = nba_utils.fetch_nba_data("https://example.test")

        self.assertEqual(table["PLAYER_ID"].tolist(), [1, 2])
        self.assertEqual(get.call_count, 2)
        sleep.assert_called_once_with(2)

    def test_fetch_fails_after_invalid_responses(self):
        response = Mock(status_code=200)
        response.json.return_value = {}
        with patch.object(nba_utils.requests, "get", return_value=response) as get:
            with patch.object(nba_utils, "sleep"):
                with self.assertRaises(RuntimeError):
                    nba_utils.fetch_nba_data("https://example.test")
        self.assertEqual(get.call_count, 5)

    def test_fetch_reports_non_json_response_details(self):
        response = Mock(
            status_code=200,
            text="<html>Access denied</html>",
            headers={"Content-Type": "text/html"},
        )
        response.json.side_effect = ValueError("Expecting value")
        with patch.object(nba_utils.requests, "get", return_value=response) as get:
            with patch.object(nba_utils, "sleep"):
                with self.assertRaises(RuntimeError) as error:
                    nba_utils.fetch_nba_data("https://example.test")
        get.assert_called_once()
        self.assertIn("content-type text/html", str(error.exception))
        self.assertIn("Access denied", str(error.exception))

    def test_update_and_load_table_round_trip_and_missing_file(self):
        table = pd.DataFrame([{"PLAYER_ID": 1}])
        with tempfile.TemporaryDirectory() as directory:
            filename = os.path.join(directory, "table.csv")
            nba_utils.update_table(table, filename)
            pd.testing.assert_frame_equal(nba_utils.load_table(filename), table)
            self.assertIsNone(nba_utils.load_table(os.path.join(directory, "missing.csv")))


class BotTests(unittest.TestCase):
    def setUp(self):
        self.bot = nba_main.NBA("user", "password", debug=True)

    def test_detects_players_passed_and_composes_post(self):
        previous = pd.DataFrame([
            {"PLAYER_ID": 1, "PLAYER_NAME": "Alpha", "PTS_RANK": 1, "PTS": 1000},
            {"PLAYER_ID": 2, "PLAYER_NAME": "Bravo", "PTS_RANK": 2, "PTS": 900},
            {"PLAYER_ID": 3, "PLAYER_NAME": "Charlie", "PTS_RANK": 3, "PTS": 800},
        ])
        current = pd.DataFrame([
            {"PLAYER_ID": 1, "PLAYER_NAME": "Alpha", "PTS_RANK": 1, "PTS": 1000},
            {"PLAYER_ID": 3, "PLAYER_NAME": "Charlie", "PTS_RANK": 2, "PTS": 950},
            {"PLAYER_ID": 2, "PLAYER_NAME": "Bravo", "PTS_RANK": 3, "PTS": 900},
        ])

        self.bot.collect_posts(current, previous)

        self.assertEqual(len(self.bot.posts), 1)
        self.assertIn("Charlie", self.bot.posts[0])
        self.assertIn("passing: Bravo.", self.bot.posts[0])
        self.assertIsNone(self.bot.check_rank_changes(99, 1, previous))

    def test_debug_send_does_not_create_client(self):
        self.bot.posts = ["preview"]
        with patch.object(nba_main, "Client") as client:
            self.bot.send_bluesky_post()
        client.assert_not_called()

    def test_live_send_reverses_posts_and_waits_between_them(self):
        self.bot.debug = False
        self.bot.posts = ["first", "second"]
        with patch.object(nba_main, "Client") as client_type:
            with patch.object(nba_main.time, "sleep") as sleep:
                self.bot.send_bluesky_post()

        client_type.return_value.login.assert_called_once_with("user", "password")
        self.assertEqual(
            [call.args[0] for call in client_type.return_value.send_post.call_args_list],
            ["second", "first"],
        )
        sleep.assert_called_once_with(180)

    def test_compose_skips_without_previous_table_or_rank_changes(self):
        with patch.object(self.bot, "send_bluesky_post") as send:
            self.bot.compose_post(pd.DataFrame(), None)
            self.bot.compose_post(pd.DataFrame(), pd.DataFrame())
        send.assert_not_called()

    def test_debug_main_uses_sample_tables(self):
        with patch.object(self.bot, "compose_post") as compose:
            self.bot.main()

        new_table, old_table = compose.call_args.args
        self.assertEqual(len(new_table), 5)
        self.assertEqual(len(old_table), 5)

    def test_live_main_fetches_and_saves_tables(self):
        self.bot.debug = False
        current = pd.DataFrame([{"PLAYER_ID": 1}])
        previous = pd.DataFrame([{"PLAYER_ID": 1}])
        with patch.object(nba_main, "fetch_nba_data", return_value=current) as fetch:
            with patch.object(nba_main, "load_table", return_value=previous):
                with patch.object(nba_main, "update_table") as update:
                    with patch.object(self.bot, "compose_post") as compose:
                        self.bot.main()

        self.assertIn("stats.nba.com", fetch.call_args.args[0])
        self.assertEqual(update.call_count, 2)
        compose.assert_called_once_with(current, previous)

    def test_live_main_skips_and_preserves_csvs_when_fetch_fails(self):
        self.bot.debug = False
        with patch.object(nba_main, "fetch_nba_data", side_effect=RuntimeError("HTML block")):
            with patch.object(nba_main, "load_table") as load:
                with patch.object(nba_main, "update_table") as update:
                    with patch.object(self.bot, "compose_post") as compose:
                        self.bot.main()

        load.assert_not_called()
        update.assert_not_called()
        compose.assert_not_called()


class SettingsTests(unittest.TestCase):
    def test_configures_environment_log_level_and_reads_environment(self):
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG", "BOT_TEST_VALUE": "value"}):
            with patch.object(settings.logging, "basicConfig") as basic_config:
                settings.configure_logging()
            self.assertEqual(basic_config.call_args.kwargs["level"], logging.DEBUG)
            self.assertEqual(settings.get_env("BOT_TEST_VALUE"), "value")

    def test_invalid_log_level_falls_back_to_info(self):
        with patch.dict(os.environ, {"LOG_LEVEL": "not-a-level"}):
            with patch.object(settings.logging, "basicConfig") as basic_config:
                settings.configure_logging()
        self.assertEqual(basic_config.call_args.kwargs["level"], logging.INFO)


if __name__ == "__main__":
    unittest.main()
