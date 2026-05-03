"""
game_state.py — Parses the full game state from a screenshot.
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np

import config
import capture
import ocr


@dataclass
class GameState:
    # Cards
    hole_cards:      list[str] = field(default_factory=list)  # e.g. ['5d', '3d']
    community_cards: list[str] = field(default_factory=list)  # 0–5 cards

    # Amounts
    pot:          float = 0.0
    call_amount:  float = 0.0
    raise_amount: float = 0.0
    my_stack:     float = 0.0
    small_blind:  float = 0.05
    big_blind:    float = 0.10

    # Situation
    hand_type:    str   = ""      # Site-provided label: "High Card", "Pair", etc.
    street:       str   = "preflop"  # preflop / flop / turn / river

    # Meta
    is_my_turn:   bool  = False
    table_found:  bool  = False

    def __str__(self):
        hole = " ".join(self.hole_cards) if self.hole_cards else "??"
        comm = " ".join(self.community_cards) if self.community_cards else "—"
        return (
            f"Cards: [{hole}]  Community: [{comm}]  "
            f"Pot: {self.pot:.2f}  Call: {self.call_amount:.2f}  "
            f"Stack: {self.my_stack:.2f}  Street: {self.street}"
        )


def parse_game_state(screen: np.ndarray, table: tuple) -> GameState:
    """
    Given a screenshot and detected table bounds, extract the full game state.
    """
    gs = GameState(table_found=True)

    def crop(prop):
        return capture.crop_region(screen, table, prop)

    # ── Blinds ────────────────────────────────────────────────────────────────
    gs.small_blind, gs.big_blind = ocr.read_blinds(crop(config.BLINDS_REGION))

    # ── Hole cards ────────────────────────────────────────────────────────────
    card1 = ocr.read_card(crop(config.HOLE_CARD_1))
    card2 = ocr.read_card(crop(config.HOLE_CARD_2))
    gs.hole_cards = [c for c in [card1, card2] if c is not None]

    # ── Community cards ───────────────────────────────────────────────────────
    for prop in config.COMMUNITY_CARDS:
        c_crop = crop(prop)
        if ocr.has_card(c_crop):
            card = ocr.read_card(c_crop)
            if card:
                gs.community_cards.append(card)

    # ── Street detection ──────────────────────────────────────────────────────
    n = len(gs.community_cards)
    gs.street = {0: "preflop", 3: "flop", 4: "turn", 5: "river"}.get(n, "preflop")

    # ── Pot and action amounts ────────────────────────────────────────────────
    gs.pot          = ocr.read_pot(crop(config.POT_REGION))
    gs.call_amount  = ocr.read_button_amount(crop(config.CALL_BTN_REGION))
    gs.raise_amount = ocr.read_button_amount(crop(config.RAISE_BTN_REGION))
    gs.my_stack     = ocr.read_stack(crop(config.MY_STACK_REGION))

    # ── Hand type label (from the site itself) ────────────────────────────────
    gs.hand_type = ocr.read_hand_type(crop(config.HAND_TYPE_REGION))

    return gs
