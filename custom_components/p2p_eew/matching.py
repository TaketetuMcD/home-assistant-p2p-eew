from __future__ import annotations

from typing import Any

# Japan Meteorological Agency "Earthquake Early Warning / Prefecture forecast
# areas" (AreaForecastLocalEEW). P2PQuake exposes these names in areas[].pref.
PREFECTURE_FORECAST_AREAS = (
    "北海道道央",
    "北海道道南",
    "北海道道北",
    "北海道道東",
    "青森",
    "岩手",
    "宮城",
    "秋田",
    "山形",
    "福島",
    "茨城",
    "栃木",
    "群馬",
    "埼玉",
    "千葉",
    "東京",
    "伊豆諸島",
    "小笠原",
    "神奈川",
    "新潟",
    "富山",
    "石川",
    "福井",
    "山梨",
    "長野",
    "岐阜",
    "静岡",
    "愛知",
    "三重",
    "滋賀",
    "京都",
    "大阪",
    "兵庫",
    "奈良",
    "和歌山",
    "鳥取",
    "島根",
    "岡山",
    "広島",
    "徳島",
    "香川",
    "愛媛",
    "高知",
    "山口",
    "福岡",
    "佐賀",
    "長崎",
    "熊本",
    "大分",
    "宮崎",
    "鹿児島",
    "奄美(群島)",
    "沖縄本島",
    "大東島",
    "宮古島",
    "八重山",
)

OKINAWA_FORECAST_AREAS = {"沖縄本島", "大東島", "宮古島", "八重山"}


def normalize_area_name(value: Any) -> str:
    """Normalize harmless spacing and parenthesis differences in area names."""
    return (
        str(value or "")
        .replace(" ", "")
        .replace("　", "")
        .replace("（", "(")
        .replace("）", ")")
        .strip()
    )


def _without_prefecture_suffix(value: str) -> str:
    if value == "北海道":
        return value
    if value.endswith(("都", "府", "県")):
        return value[:-1]
    return value


def area_matches(selected_area: str, area: dict[str, Any]) -> bool:
    """Return whether a configured broad or fine area matches a P2P area."""
    target = normalize_area_name(selected_area)
    pref = normalize_area_name(area.get("pref"))
    name = normalize_area_name(area.get("name"))

    if not target:
        return True
    if target == pref or target == name:
        return True

    # Friendly aliases used by people more often than the P2P/JMA labels.
    if target == "北海道" and pref.startswith("北海道"):
        return True
    if target in {"沖縄", "沖縄県"} and pref in OKINAWA_FORECAST_AREAS:
        return True

    # P2P uses e.g. "神奈川" for areas[].pref, while users commonly type
    # "神奈川県". Compare only broad labels here; fine names stay exact.
    return bool(pref) and _without_prefecture_suffix(
        target
    ) == _without_prefecture_suffix(pref)


def matching_areas(
    selected_areas: list[str] | tuple[str, ...], areas: list[Any]
) -> list[dict[str, Any]]:
    """Return P2P areas matching any selected area (OR semantics)."""
    valid_areas = [area for area in areas if isinstance(area, dict)]
    selected = [area for area in selected_areas if normalize_area_name(area)]
    if not selected:
        return valid_areas
    return [
        area
        for area in valid_areas
        if any(area_matches(target, area) for target in selected)
    ]


def parse_scale(value: Any) -> int:
    """Parse a JMA intensity code, returning -1 for missing/invalid values."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def max_scale(areas: list[dict[str, Any]], key: str) -> int:
    """Return the greatest intensity code for a list of P2P areas."""
    return max((parse_scale(area.get(key)) for area in areas), default=-1)
