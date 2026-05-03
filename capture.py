"""
capture.py — Screen capture + table region detection

Redesigned for ClubWPT Gold's dark table theme.
Uses SCREEN-RELATIVE coordinates instead of green-table detection.
Table detection now uses the gold oval border color.
"""

import mss
import numpy as np
import cv2
import config

_sct = mss.mss()


def capture_screen() -> np.ndarray:
    """Grab primary monitor, return as BGR numpy array."""
    monitor = _sct.monitors[1]
    shot = _sct.grab(monitor)
    img = np.array(shot)
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def find_table_bounds(screen: np.ndarray) -> tuple:
    """
    Returns (x, y, w, h) using the FULL SCREEN as the coordinate space.
    We no longer rely on green felt detection — instead we confirm the
    game is visible by checking for the gold oval border.
    Falls back to full screen bounds if gold border not found.
    """
    h, w = screen.shape[:2]

    # Try to confirm game is visible via gold border
    hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)
    lower = np.array(config.TABLE_HSV_LOWER)
    upper = np.array(config.TABLE_HSV_UPPER)
    mask = cv2.inRange(hsv, lower, upper)

    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) >= config.TABLE_MIN_AREA:
            # Gold border found — use full screen as reference
            return (0, 0, w, h)

    # Fallback: check for blue buttons (player turn = game definitely visible)
    if is_player_turn(screen, (0, 0, w, h)):
        return (0, 0, w, h)

    return None  # Game not detected


def crop_region(screen: np.ndarray, table: tuple, prop: tuple) -> np.ndarray:
    """
    Crop a proportional region from the screen.
    table = (x, y, w, h)  — now always (0, 0, screen_w, screen_h)
    prop  = (x1, y1, x2, y2) as fractions of screen width/height
    """
    tx, ty, tw, th = table
    x1 = int(tx + prop[0] * tw)
    y1 = int(ty + prop[1] * th)
    x2 = int(tx + prop[2] * tw)
    y2 = int(ty + prop[3] * th)
    sh, sw = screen.shape[:2]
    x1, x2 = max(0, x1), min(sw, x2)
    y1, y2 = max(0, y1), min(sh, y2)
    return screen[y1:y2, x1:x2]


def is_player_turn(screen: np.ndarray, table: tuple) -> bool:
    """
    Detect if action buttons are visible (it's your turn).
    Looks for the blue Fold/Check/Call buttons in the bottom-right area.
    """
    btn_crop = crop_region(screen, table, config.BUTTON_SEARCH_REGION)
    lower = np.array([max(0, c - config.BUTTON_TOLERANCE) for c in config.BUTTON_BGR])
    upper = np.array([min(255, c + config.BUTTON_TOLERANCE) for c in config.BUTTON_BGR])
    mask = cv2.inRange(btn_crop, lower, upper)
    return cv2.countNonZero(mask) > 200
