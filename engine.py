"""
engine.py — Poker decision engine for ClubWPT Gold
Optimized for: 8-max NLHE, mandatory straddle + ante structure.

Decision philosophy:
  - Preflop: range-based, wider than standard due to straddle+ante dead money
  - Postflop: hand strength vs pot odds + position
  - Output: one clear action string ("FOLD" / "CALL" / "RAISE to X.XX")
"""

from dataclasses import dataclass
from treys import Card, Evaluator

evaluator = Evaluator()


# ── PREFLOP HAND CLASSIFICATION ───────────────────────────────────────────────
# Hands grouped by strength tier (ClubWPT Gold adjusted — slightly wider than
# standard 8-max due to straddle+ante dead money).

TIER_1_PREMIUM = {
    # Always raise/reraise from any position
    ('A', 'A'), ('K', 'K'), ('Q', 'Q'), ('J', 'J'),
    ('A', 'K'),  # suited or offsuit both premium
}

TIER_2_STRONG = {
    # Raise from all positions, call 3-bets
    ('T', 'T'), ('9', '9'),
    ('A', 'Q'), ('A', 'J'), ('K', 'Q'),
}

TIER_3_MEDIUM = {
    # Raise from middle/late position; call from early
    ('8', '8'), ('7', '7'),
    ('A', 'T'), ('K', 'J'), ('Q', 'J'), ('J', 'T'),
    ('A', '9'), ('K', 'T'),
}

TIER_4_SPECULATIVE = {
    # Raise from late position (BTN/CO), otherwise fold to raises
    ('6', '6'), ('5', '5'), ('4', '4'),
    ('A', '8'), ('A', '7'), ('A', '6'), ('A', '5'), ('A', '4'), ('A', '3'), ('A', '2'),
    ('T', '9'), ('9', '8'), ('8', '7'), ('7', '6'), ('6', '5'), ('5', '4'),
}

# Everything else = Tier 5 (fold preflop)


@dataclass
class Decision:
    action:      str    # "FOLD" | "CALL" | "RAISE"
    amount:      float  # raise amount (0 if fold/call)
    reason:      str    # one-line explanation
    confidence:  str    # "HIGH" | "MEDIUM" | "LOW"

    def display(self) -> str:
        if self.action == "FOLD":
            return "FOLD"
        if self.action == "CALL":
            return f"CALL"
        return f"RAISE to {self.amount:.2f}"


# ── CARD PARSING ──────────────────────────────────────────────────────────────

def _parse_card(card_str: str):
    """Convert '5d' → treys Card int. Returns None on failure."""
    try:
        return Card.new(card_str)
    except Exception:
        return None


def _hand_key(rank1: str, rank2: str, suited: bool) -> tuple:
    """Normalize a hand into a canonical (high, low) rank pair."""
    rank_order = '23456789TJQKA'
    r1 = rank_order.index(rank1)
    r2 = rank_order.index(rank2)
    if r1 >= r2:
        return (rank1, rank2)
    return (rank2, rank1)


def _classify_preflop(hole_cards: list[str]) -> int:
    """
    Returns hand tier 1–5.
    1 = Premium, 5 = Trash.
    """
    if len(hole_cards) < 2:
        return 5

    r1 = hole_cards[0][0].upper()
    s1 = hole_cards[0][1].lower()
    r2 = hole_cards[1][0].upper()
    s2 = hole_cards[1][1].lower()

    suited = (s1 == s2)
    key = _hand_key(r1, r2, suited)

    if key in TIER_1_PREMIUM:
        return 1
    if key in TIER_2_STRONG:
        # Suited connectors get a small bonus
        if suited:
            return 2
        return 2
    if key in TIER_3_MEDIUM:
        if suited:
            return 3
        return 3
    if key in TIER_4_SPECULATIVE:
        if suited:
            return 4
        # Offsuit speculative hands are only playable late position
        return 5 if not suited else 4

    # Pairs not listed above
    if r1 == r2:
        rank_order = '23456789TJQKA'
        rank_val = rank_order.index(r1)
        if rank_val >= 8:   # 99+
            return 2
        if rank_val >= 5:   # 66-88
            return 3
        return 4             # 22-55

    return 5


def _pot_odds(call_amount: float, pot: float) -> float:
    """Required equity to break even on a call."""
    total = pot + call_amount
    if total == 0:
        return 0.0
    return call_amount / total


# Rough preflop equity vs a calling range, indexed by tier
TIER_EQUITY = {1: 0.72, 2: 0.60, 3: 0.52, 4: 0.44, 5: 0.35}


# ── POSTFLOP EVALUATION ───────────────────────────────────────────────────────

def _hand_strength_postflop(hole_cards: list[str], community: list[str]) -> float:
    """
    Returns approximate hand equity (0.0–1.0) using treys hand rank.
    treys rank: 1 (royal flush) → 7462 (worst high card).
    We invert and normalize to 0.0–1.0.
    """
    h = [_parse_card(c) for c in hole_cards]
    b = [_parse_card(c) for c in community]

    if None in h or None in b or len(h) < 2 or len(b) < 3:
        return 0.40  # Unknown — be conservative

    try:
        rank = evaluator.evaluate(b, h)
        # rank 1 = best, 7462 = worst → normalize to 0–1
        strength = 1.0 - (rank - 1) / 7461.0
        return strength
    except Exception:
        return 0.40


# ── MAIN DECISION FUNCTION ────────────────────────────────────────────────────

def decide(gs) -> Decision:
    """
    Takes a GameState, returns a Decision.
    This is the function everything flows through.
    """
    # Safety: if we can't read cards, fold
    if len(gs.hole_cards) < 2:
        return Decision("FOLD", 0, "Can't read cards — folding safely", "LOW")

    # ── PREFLOP ───────────────────────────────────────────────────────────────
    if gs.street == "preflop":
        return _decide_preflop(gs)

    # ── POSTFLOP (flop / turn / river) ────────────────────────────────────────
    return _decide_postflop(gs)


def _decide_preflop(gs) -> Decision:
    tier = _classify_preflop(gs.hole_cards)
    equity = TIER_EQUITY[tier]
    odds = _pot_odds(gs.call_amount, gs.pot)

    hand_label = " ".join(gs.hole_cards)

    # No bet to call — we can check or open-raise
    if gs.call_amount <= gs.big_blind * 1.1:
        if tier <= 2:
            raise_to = max(gs.raise_amount, gs.big_blind * 3)
            return Decision("RAISE", raise_to,
                            f"Strong hand ({hand_label}) — open raise", "HIGH")
        if tier == 3:
            raise_to = gs.raise_amount if gs.raise_amount > 0 else gs.big_blind * 2.5
            return Decision("RAISE", raise_to,
                            f"Medium hand ({hand_label}) — open raise", "MEDIUM")
        if tier == 4:
            return Decision("CALL", 0,
                            f"Speculative hand ({hand_label}) — limp in", "LOW")
        return Decision("FOLD", 0,
                        f"Weak hand ({hand_label}) — fold", "MEDIUM")

    # There is a bet to call
    if equity > odds + 0.05:  # Need a 5% buffer to make calling worth it
        if tier <= 2:
            # Reraise with strong hands
            raise_to = gs.raise_amount * 3 if gs.raise_amount > 0 else gs.call_amount * 3
            return Decision("RAISE", raise_to,
                            f"Premium hand ({hand_label}) — 3-bet", "HIGH")
        if tier == 3:
            return Decision("CALL", 0,
                            f"Medium hand ({hand_label}) — call has equity", "MEDIUM")
        if tier == 4:
            return Decision("CALL", 0,
                            f"Speculative ({hand_label}) — pot odds are ok", "LOW")

    # Pot odds don't support calling
    if tier <= 1:
        # Never fold premiums preflop
        raise_to = gs.raise_amount * 3 if gs.raise_amount > 0 else gs.call_amount * 2.5
        return Decision("RAISE", raise_to,
                        f"Premium hand ({hand_label}) — 3-bet regardless", "HIGH")

    return Decision("FOLD", 0,
                    f"Weak hand ({hand_label}) or bad pot odds — fold", "HIGH")


def _decide_postflop(gs) -> Decision:
    strength = _hand_strength_postflop(gs.hole_cards, gs.community_cards)
    odds = _pot_odds(gs.call_amount, gs.pot)

    site_label = gs.hand_type  # e.g. "Two Pair", "Flush", etc.

    # No bet to face — check or bet
    if gs.call_amount == 0:
        if strength > 0.75:
            bet = round(gs.pot * 0.65, 2)  # 2/3 pot bet
            return Decision("RAISE", bet,
                            f"Strong hand ({site_label}) — bet for value", "HIGH")
        if strength > 0.50:
            return Decision("CALL", 0,  # CALL with amount=0 = check
                            f"Medium hand ({site_label}) — check", "MEDIUM")
        return Decision("CALL", 0,
                        f"Weak hand ({site_label}) — check", "LOW")

    # Facing a bet
    if strength > 0.80:
        raise_to = gs.raise_amount if gs.raise_amount > 0 else gs.call_amount * 2.5
        return Decision("RAISE", raise_to,
                        f"Very strong hand ({site_label}) — raise for value", "HIGH")

    if strength > odds + 0.08:
        return Decision("CALL", 0,
                        f"Hand strength {strength:.0%} beats pot odds {odds:.0%}", "MEDIUM")

    if strength > 0.45 and gs.street in ("flop", "turn"):
        return Decision("CALL", 0,
                        f"Drawing hand — calling for equity on {gs.street}", "LOW")

    return Decision("FOLD", 0,
                    f"Hand strength {strength:.0%} doesn't beat pot odds {odds:.0%}", "HIGH")
