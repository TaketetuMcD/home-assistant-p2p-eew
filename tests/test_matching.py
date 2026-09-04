from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "p2p_eew"
    / "matching.py"
)
SPEC = importlib.util.spec_from_file_location("p2p_eew_matching", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
matching = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(matching)


class AreaMatchingTests(unittest.TestCase):
    def test_exact_prefecture_forecast_area(self) -> None:
        area = {"pref": "神奈川", "name": "神奈川県東部"}
        self.assertTrue(matching.area_matches("神奈川", area))

    def test_common_prefecture_suffix_alias(self) -> None:
        area = {"pref": "神奈川", "name": "神奈川県東部"}
        self.assertTrue(matching.area_matches("神奈川県", area))

    def test_tokyo_suffix_alias(self) -> None:
        area = {"pref": "東京", "name": "東京都２３区"}
        self.assertTrue(matching.area_matches("東京都", area))

    def test_hokkaido_alias_matches_all_hokkaido_forecast_areas(self) -> None:
        hokkaido_areas = (
            "北海道道央",
            "北海道道南",
            "北海道道北",
            "北海道道東",
        )
        for pref in hokkaido_areas:
            with self.subTest(pref=pref):
                self.assertTrue(
                    matching.area_matches(
                        "北海道", {"pref": pref, "name": "テスト地域"}
                    )
                )

    def test_okinawa_alias_matches_island_forecast_areas(self) -> None:
        for pref in ("沖縄本島", "大東島", "宮古島", "八重山"):
            with self.subTest(pref=pref):
                self.assertTrue(
                    matching.area_matches(
                        "沖縄県", {"pref": pref, "name": "テスト地域"}
                    )
                )

    def test_fine_area_is_exact(self) -> None:
        east = {"pref": "神奈川", "name": "神奈川県東部"}
        west = {"pref": "神奈川", "name": "神奈川県西部"}
        self.assertTrue(matching.area_matches("神奈川県東部", east))
        self.assertFalse(matching.area_matches("神奈川県東部", west))

    def test_multiple_areas_use_or_semantics(self) -> None:
        areas = [
            {"pref": "千葉", "name": "千葉県北西部"},
            {"pref": "神奈川", "name": "神奈川県東部"},
            {"pref": "静岡", "name": "静岡県伊豆"},
        ]
        self.assertEqual(
            matching.matching_areas(["東京都", "神奈川県"], areas),
            [areas[1]],
        )

    def test_no_selection_returns_all_valid_areas(self) -> None:
        areas = [{"pref": "東京"}, None, "invalid", {"pref": "神奈川"}]
        self.assertEqual(
            matching.matching_areas([], areas),
            [areas[0], areas[3]],
        )

    def test_full_width_parentheses_and_spaces_are_normalized(self) -> None:
        area = {"pref": "奄美(群島)", "name": "奄美大島近海"}
        self.assertTrue(matching.area_matches(" 奄美（群島） ", area))


class ScaleTests(unittest.TestCase):
    def test_parse_scale_handles_invalid_values(self) -> None:
        self.assertEqual(matching.parse_scale("55"), 55)
        self.assertEqual(matching.parse_scale(None), -1)
        self.assertEqual(matching.parse_scale("unknown"), -1)

    def test_max_scale_uses_greatest_prediction(self) -> None:
        areas = [{"scaleTo": 45}, {"scaleTo": "55"}, {}]
        self.assertEqual(matching.max_scale(areas, "scaleTo"), 55)


if __name__ == "__main__":
    unittest.main()
