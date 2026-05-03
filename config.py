"""
config.py — ClubWPT Gold Poker Advisor
All region coordinates are PROPORTIONAL (0.0–1.0) relative to the detected
poker table bounding box. This makes them resolution-independent.

Run calibrate.py first if regions are off on your screen.
"""

# ── SCAN SETTINGS ─────────────────────────────────────────────────────────────
SCAN_INTERVAL = 0.5  # seconds between screen reads

# ── TABLE DETECTION ───────────────────────────────────────────────────────────
# HSV color range for the green felt table
TABLE_HSV_LOWER = (40, 40, 40)
TABLE_HSV_UPPER = (90, 255, 190)
TABLE_MIN_AREA   = 80_000  # pixels — ignore small green blobs

# ── ACTION BUTTON DETECTION ───────────────────────────────────────────────────
# BGR color of the blue Fold/Call/Raise buttons
BUTTON_BGR       = [42, 110, 205]
BUTTON_TOLERANCE = 55
# Region (proportional) to search for action buttons within table bounds
BUTTON_SEARCH_REGION = (0.55, 0.75, 1.0, 1.0)  # (x1, y1, x2, y2)

# ── CARD REGIONS (proportional to table bounds) ───────────────────────────────
# Your two hole cards — bottom-center of the table
HOLE_CARD_1 = (0.37, 0.56, 0.46, 0.80)
HOLE_CARD_2 = (0.44, 0.56, 0.53, 0.80)

# Community cards (flop/turn/river) — center of table
COMMUNITY_CARDS = [
    (0.28, 0.38, 0.38, 0.60),  # flop card 1
    (0.38, 0.38, 0.48, 0.60),  # flop card 2
    (0.48, 0.38, 0.58, 0.60),  # flop card 3
    (0.58, 0.38, 0.68, 0.60),  # turn
    (0.68, 0.38, 0.78, 0.60),  # river
]

# ── TEXT REGIONS (proportional to table bounds) ───────────────────────────────
POT_REGION       = (0.33, 0.28, 0.58, 0.38)  # "POT: 0.85"
HAND_TYPE_REGION = (0.36, 0.52, 0.56, 0.60)  # "High Card" / "Pair" etc.
MY_STACK_REGION  = (0.38, 0.72, 0.56, 0.80)  # "4.90 sc"
BLINDS_REGION    = (0.83, 0.00, 1.00, 0.08)  # "0.05/0.10" top-right

# Action button text regions (relative to BUTTON_SEARCH_REGION)
FOLD_BTN_REGION  = (0.55, 0.78, 0.72, 0.95)
CALL_BTN_REGION  = (0.72, 0.78, 0.87, 0.95)
RAISE_BTN_REGION = (0.87, 0.78, 1.00, 0.95)

# ── POSITION DETECTION ────────────────────────────────────────────────────────
# Where to look for SB/BB/D badges near each seat
# Player (you) is always at bottom-center
MY_POSITION_BADGE = (0.36, 0.70, 0.48, 0.76)  # look for "SB"/"BB" near you
DEALER_BTN_REGION = (0.10, 0.40, 0.35, 0.60)  # "D" marker area

# ── OCR SETTINGS ──────────────────────────────────────────────────────────────
# Tesseract config — digits + card ranks only for card OCR
CARD_OCR_CONFIG  = "--psm 8 -c tessedit_char_whitelist=23456789TJQKA"
TEXT_OCR_CONFIG  = "--psm 7"

# Tesseract binary path — change this on Windows:
# TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_PATH = None  # None = auto-detect (works on Mac/Linux)
