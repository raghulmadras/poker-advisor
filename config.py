"""
config.py — ClubWPT Gold Poker Advisor
Recalibrated for the DARK TABLE theme (0.01/0.02 micro stakes layout).

All regions are proportional to the FULL SCREEN dimensions.
This avoids relying on table color detection (which broke on the dark theme).

Calibrated from Mac/Vivaldi screenshot at standard 100% zoom.
If boxes are slightly off, adjust the values here and re-run calibrate.py.
"""

# ── SCAN SETTINGS ─────────────────────────────────────────────────────────────
SCAN_INTERVAL = 0.5

# ── TABLE / TURN DETECTION ────────────────────────────────────────────────────
# Gold oval border (replaces green felt detection)
TABLE_HSV_LOWER = (15, 80, 100)   # warm gold/amber
TABLE_HSV_UPPER = (45, 255, 255)
TABLE_MIN_AREA  = 5000            # gold border is thin — lower threshold

# Blue action buttons (Fold / Check or Call / Bet or Raise)
BUTTON_BGR       = [210, 100, 50]  # BGR for the blue buttons
BUTTON_TOLERANCE = 60
# Search for buttons in bottom-right quadrant of screen
BUTTON_SEARCH_REGION = (0.60, 0.88, 1.00, 1.00)

# ── HOLE CARDS (your two cards — bottom center) ───────────────────────────────
HOLE_CARD_1 = (0.466, 0.748, 0.527, 0.878)
HOLE_CARD_2 = (0.527, 0.748, 0.588, 0.878)

# ── COMMUNITY CARDS (center of table) ────────────────────────────────────────
COMMUNITY_CARDS = [
    (0.370, 0.505, 0.425, 0.643),  # flop card 1
    (0.425, 0.505, 0.480, 0.643),  # flop card 2
    (0.480, 0.505, 0.535, 0.643),  # flop card 3
    (0.535, 0.505, 0.590, 0.643),  # turn
    (0.590, 0.505, 0.645, 0.643),  # river
]

# ── TEXT REGIONS ──────────────────────────────────────────────────────────────
POT_REGION       = (0.455, 0.463, 0.588, 0.501)  # "POT: 0.63"
HAND_TYPE_REGION = (0.475, 0.715, 0.573, 0.745)  # "HIGH CARD" / "PAIR" etc.
MY_STACK_REGION  = (0.500, 0.895, 0.595, 0.930)  # "0.18 CHIPS"
BLINDS_REGION    = (0.872, 0.162, 0.995, 0.210)  # "0.01/0.02"

# ── ACTION BUTTONS ────────────────────────────────────────────────────────────
# Handles both variants:
#   Fold / Check / Bet X        (no one has bet yet)
#   Fold / Call X / Raise to X  (facing a bet)
FOLD_BTN_REGION  = (0.608, 0.940, 0.718, 0.990)
CALL_BTN_REGION  = (0.728, 0.940, 0.843, 0.990)  # also "Check" when no bet
RAISE_BTN_REGION = (0.853, 0.940, 0.968, 0.990)  # also "Bet X"
BET_SIZE_REGION  = (0.920, 0.930, 0.998, 0.960)  # the amount in the input box

# ── POSITION DETECTION ────────────────────────────────────────────────────────
MY_POSITION_BADGE = (0.450, 0.870, 0.560, 0.900)
DEALER_BTN_REGION = (0.170, 0.610, 0.310, 0.710)  # "D" marker area

# ── OCR SETTINGS ──────────────────────────────────────────────────────────────
CARD_OCR_CONFIG = "--psm 8 -c tessedit_char_whitelist=23456789TJQKA"
TEXT_OCR_CONFIG = "--psm 7"
TESSERACT_PATH  = None  # None = auto-detect on Mac/Linux
