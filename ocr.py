"""
ocr.py — Card recognition and game state text extraction

Card reading strategy:
  - Rank: pytesseract OCR on the card crop (whitelist: 23456789TJQKA)
  - Suit: color analysis (red = hearts/diamonds, black = spades/clubs)
          then shape detection to distinguish H vs D, S vs C
"""

import re
import numpy as np
import cv2
import pytesseract
from PIL import Image
import config

if config.TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_PATH

# ── CARD READING ──────────────────────────────────────────────────────────────

RANK_MAP = {
    '1': 'A', 'a': 'A', 'A': 'A',
    '2': '2', '3': '3', '4': '4', '5': '5',
    '6': '6', '7': '7', '8': '8', '9': '9',
    '0': 'T', 'T': 'T', 't': 'T',
    'J': 'J', 'j': 'J',
    'Q': 'Q', 'q': 'Q',
    'K': 'K', 'k': 'K',
}

def _preprocess_card(crop: np.ndarray) -> np.ndarray:
    """Prepare a card crop for OCR: isolate the rank text area."""
    # The rank digit is in the top-left corner of the card
    h, w = crop.shape[:2]
    rank_area = crop[0:int(h * 0.45), 0:int(w * 0.55)]

    # Convert to grayscale
    gray = cv2.cvtColor(rank_area, cv2.COLOR_BGR2GRAY)

    # Upscale for better OCR accuracy
    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    # Threshold: card background is white, text is colored
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    return thresh


def _read_rank(crop: np.ndarray) -> str | None:
    """OCR the rank from a card image crop."""
    processed = _preprocess_card(crop)
    pil_img = Image.fromarray(processed)
    raw = pytesseract.image_to_string(pil_img, config=config.CARD_OCR_CONFIG).strip()

    # Clean up OCR noise
    raw = re.sub(r'[^23456789TJQKAa10]', '', raw)
    if not raw:
        return None

    # Handle "10" → "T"
    if raw.startswith('10') or raw == '10':
        return 'T'

    char = raw[0].upper()
    return RANK_MAP.get(char)


def _detect_suit(crop: np.ndarray) -> str | None:
    """
    Detect suit by:
    1. Color: red pixels → hearts or diamonds; dark pixels → spades or clubs
    2. Shape: diamond (rotated square) vs heart; spade vs club
    """
    h, w = crop.shape[:2]
    # Look at center area where the large suit symbol is
    suit_area = crop[int(h * 0.3):int(h * 0.85), int(w * 0.1):int(w * 0.9)]

    hsv = cv2.cvtColor(suit_area, cv2.COLOR_BGR2HSV)

    # Red mask (hue wraps around — check both ends)
    red_lo1 = cv2.inRange(hsv, np.array([0, 100, 80]),   np.array([10, 255, 255]))
    red_lo2 = cv2.inRange(hsv, np.array([160, 100, 80]), np.array([180, 255, 255]))
    red_mask = cv2.bitwise_or(red_lo1, red_lo2)

    # Black/dark mask
    dark_mask = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 60, 80]))

    red_count  = cv2.countNonZero(red_mask)
    dark_count = cv2.countNonZero(dark_mask)

    if red_count < 20 and dark_count < 20:
        return None  # Can't determine

    if red_count > dark_count:
        # Red suit — distinguish diamond vs heart by shape
        return _distinguish_red_suit(suit_area, red_mask)
    else:
        # Dark suit — distinguish spade vs club by shape
        return _distinguish_dark_suit(suit_area, dark_mask)


def _distinguish_red_suit(area: np.ndarray, mask: np.ndarray) -> str:
    """
    Diamond = roughly 4 corners pointing up/down/left/right (rotated square).
    Heart   = two bumps on top, pointed bottom.
    Use the contour's aspect ratio and solidity to tell them apart.
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 'd'  # Default to diamond (most common in this screenshot)

    c = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(c)

    if w == 0 or h == 0:
        return 'd'

    aspect = w / h
    hull_area = cv2.contourArea(cv2.convexHull(c))
    contour_area = cv2.contourArea(c)
    solidity = contour_area / hull_area if hull_area > 0 else 1

    # Diamond: aspect ≈ 1.0, high solidity (≈ 0.95+)
    # Heart:   aspect ≈ 1.1, lower solidity (≈ 0.75–0.85) due to the notch
    if solidity > 0.90 and 0.7 < aspect < 1.3:
        return 'd'
    else:
        return 'h'


def _distinguish_dark_suit(area: np.ndarray, mask: np.ndarray) -> str:
    """
    Spade = inverted heart shape with a stem.
    Club  = three circles + stem.
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 's'

    c = max(contours, key=cv2.contourArea)
    hull_area = cv2.contourArea(cv2.convexHull(c))
    contour_area = cv2.contourArea(c)
    solidity = contour_area / hull_area if hull_area > 0 else 1

    # Club has more circular bumps → lower solidity
    # Spade is more solid overall
    if solidity < 0.80:
        return 'c'
    else:
        return 's'


def read_card(crop: np.ndarray) -> str | None:
    """
    Full card read from a cropped card image.
    Returns card string like 'As', 'Kh', 'Td', '5d', or None if unreadable.
    """
    if crop is None or crop.size == 0:
        return None

    rank = _read_rank(crop)
    suit = _detect_suit(crop)

    if rank and suit:
        return f"{rank}{suit}"
    return None


# ── TEXT EXTRACTION ───────────────────────────────────────────────────────────

def _ocr_text(crop: np.ndarray, config_str: str = config.TEXT_OCR_CONFIG) -> str:
    """Run OCR on a cropped region and return cleaned text."""
    if crop is None or crop.size == 0:
        return ""
    # Upscale for accuracy
    crop = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    pil = Image.fromarray(thresh)
    return pytesseract.image_to_string(pil, config=config_str).strip()


def read_pot(crop: np.ndarray) -> float:
    """Extract pot size from 'POT: 0.85' text region."""
    text = _ocr_text(crop)
    match = re.search(r'[\d]+\.[\d]+', text)
    return float(match.group()) if match else 0.0


def read_button_amount(crop: np.ndarray) -> float:
    """
    Extract numeric amount from action buttons.
    Handles: 'Call 0.60', 'Raise to 1.10', 'Bet 0.02', 'Check' (returns 0.0)
    """
    text = _ocr_text(crop)
    match = re.search(r'[\d]+\.[\d]+', text)
    return float(match.group()) if match else 0.0


def is_check_available(crop: np.ndarray) -> bool:
    """Returns True if the middle button says 'Check' (no bet to call)."""
    text = _ocr_text(crop).lower()
    return 'check' in text


def read_stack(crop: np.ndarray) -> float:
    """Extract stack size from '4.90 sc' region."""
    text = _ocr_text(crop)
    match = re.search(r'[\d]+\.[\d]+', text)
    return float(match.group()) if match else 0.0


def read_hand_type(crop: np.ndarray) -> str:
    """Read the hand type label the site shows ('High Card', 'Pair', etc.)."""
    return _ocr_text(crop).strip()


def read_blinds(crop: np.ndarray) -> tuple[float, float]:
    """Extract small blind and big blind from '0.01/0.02'."""
    text = _ocr_text(crop)
    matches = re.findall(r'[\d]+\.[\d]+', text)
    if len(matches) >= 2:
        return float(matches[0]), float(matches[1])
    return 0.01, 0.02  # Fallback default for micro stakes (0.01/0.02)


def has_card(crop: np.ndarray) -> bool:
    """Check if a community card slot actually has a card (white area = card present)."""
    if crop is None or crop.size == 0:
        return False
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    white_pixels = cv2.countNonZero(cv2.inRange(gray,
                                                np.array([200]),
                                                np.array([255])))
    return white_pixels > (gray.size * 0.15)
