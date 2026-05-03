"""
position.py — Detect the player's position at the table

ClubWPT Gold is 8-max. The player (you) is always at the bottom-center seat.
We detect where the Dealer button is, then count seats clockwise to assign position.

8-max positions (clockwise from BTN):
  BTN → SB → BB → UTG → UTG+1 → MP → HJ → CO → (back to BTN)

Seat layout (fixed, proportional to table bounds):
  We map 8 fixed seat positions clockwise, starting from top-center.
  The bottom-center seat (index 4) is always the player (you).
"""

import numpy as np
import cv2
import config

# Fixed seat positions as (x, y) proportions of table bounds (clockwise from top)
# Index 0 = top-center, going clockwise
SEAT_POSITIONS = [
    (0.47, 0.10),   # 0: top-center
    (0.72, 0.15),   # 1: top-right
    (0.85, 0.42),   # 2: right
    (0.72, 0.70),   # 3: bottom-right
    (0.47, 0.78),   # 4: bottom-center ← YOU (always)
    (0.22, 0.70),   # 5: bottom-left
    (0.15, 0.42),   # 6: left
    (0.22, 0.15),   # 7: top-left
]

MY_SEAT_INDEX = 4  # Bottom-center is always the player

# Position names for 8-max (from BTN, going clockwise)
# Key = seats_from_btn, Value = position name
POSITION_NAMES = {
    0: "BTN",
    1: "SB",
    2: "BB",
    3: "UTG",
    4: "UTG+1",
    5: "MP",
    6: "HJ",
    7: "CO",
}

# Position value: higher = better (more info, act later)
POSITION_VALUE = {
    "BTN":   8,
    "CO":    7,
    "HJ":    6,
    "MP":    5,
    "UTG+1": 4,
    "UTG":   3,
    "BB":    2,
    "SB":    1,
}

# Dealer button: small circular badge with "D"
# We detect it by looking for a white/gray circle in the table region
DEALER_SEARCH_REGION = (0.05, 0.20, 0.55, 0.75)  # left/center of table


def _find_dealer_position(screen: np.ndarray, table: tuple) -> tuple[float, float] | None:
    """
    Find the (x, y) proportional position of the Dealer 'D' button.
    Returns proportions relative to table bounds, or None.
    """
    tx, ty, tw, th = table
    x1 = int(tx + DEALER_SEARCH_REGION[0] * tw)
    y1 = int(ty + DEALER_SEARCH_REGION[1] * th)
    x2 = int(tx + DEALER_SEARCH_REGION[2] * tw)
    y2 = int(ty + DEALER_SEARCH_REGION[3] * th)
    region = screen[y1:y2, x1:x2]

    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)

    # The D button is a small white/light circle
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp=1, minDist=30,
        param1=50, param2=20, minRadius=8, maxRadius=22
    )

    if circles is None:
        return None

    # Take the most confident circle
    circle = circles[0][0]
    cx, cy, _ = circle

    # Convert back to proportional table coords
    abs_x = x1 + cx
    abs_y = y1 + cy
    prop_x = (abs_x - tx) / tw
    prop_y = (abs_y - ty) / th

    return prop_x, prop_y


def _closest_seat(prop_x: float, prop_y: float) -> int:
    """Find which seat index is closest to a given proportional position."""
    min_dist = float("inf")
    closest = 0
    for i, (sx, sy) in enumerate(SEAT_POSITIONS):
        dist = ((prop_x - sx) ** 2 + (prop_y - sy) ** 2) ** 0.5
        if dist < min_dist:
            min_dist = dist
            closest = i
    return closest


def detect_position(screen: np.ndarray, table: tuple) -> str:
    """
    Detect the player's current position.
    Returns position name: 'BTN', 'CO', 'HJ', 'MP', 'UTG+1', 'UTG', 'BB', 'SB'
    Falls back to 'unknown' if detection fails.
    """
    dealer_pos = _find_dealer_position(screen, table)
    if dealer_pos is None:
        return "unknown"

    btn_seat = _closest_seat(*dealer_pos)

    # Count clockwise seats from BTN to MY_SEAT
    seats_from_btn = (MY_SEAT_INDEX - btn_seat) % 8

    return POSITION_NAMES.get(seats_from_btn, "unknown")


def position_is_late(position: str) -> bool:
    return POSITION_VALUE.get(position, 4) >= 7  # CO or BTN

def position_is_early(position: str) -> bool:
    return POSITION_VALUE.get(position, 4) <= 3  # UTG or UTG+1

def position_value(position: str) -> int:
    return POSITION_VALUE.get(position, 4)
