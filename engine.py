"""
engine.py — Exploitative decision engine v2

Decision hierarchy (in order of priority):
  1. Opponent type  → shapes the entire strategy (exploit weak players)
  2. Position       → when to open, how wide, when to fold
  3. Equity         → Monte Carlo vs opponent's actual range (not random)
  4. SPR            → stack-to-pot ratio changes commitment strategy
  5. Street         → preflop vs postflop logic differs significantly
"""

from dataclasses import dataclass
import equity as eq
import position as pos
from opponent_db import OpponentStats

# ── PREFLOP RANGE TIERS ───────────────────────────────────────────────────────
# How far into HAND_RANKINGS each position opens from (0.0 = top %, 1.0 = all hands)
# Adjusted wider than standard due to ClubWPT Gold straddle+ante dead money

OPEN_RANGE_BY_POSITION = {
    "BTN":     0.52,
    "CO":      0.38,
    "HJ":      0.28,
    "MP":      0.22,
    "UTG+1":   0.16,
    "UTG":     0.13,
    "SB":      0.42,
    "BB":      0.55,
    "unknown": 0.22,
}

THREBET_RANGE_BY_POSITION = {
    "BTN":     0.10,
    "CO":      0.08,
    "HJ":      0.06,
    "MP":      0.05,
    "UTG+1":   0.04,
    "UTG":     0.04,
    "SB":      0.09,
    "BB":      0.10,
    "unknown": 0.06,
}

RANGE_ADJUST_VS_OPPONENT = {
    "fish":          +0.08,
    "tight_passive": +0.10,
    "lag":           -0.08,
    "tag":            0.00,
    "unknown":        0.00,
}


@dataclass
class Decision:
    action:     str
    amount:     float
    reason:     str
    confidence: str
    equity:     float
    exploit:    str

    def display(self) -> str:
        if self.action == "FOLD":
            return "FOLD"
        if self.action == "CALL":
            return "CALL" if self.amount == 0 else f"CALL {self.amount:.2f}"
        return f"RAISE to {self.amount:.2f}"


def decide(gs, opponent: OpponentStats | None = None, position: str = "unknown") -> Decision:
    opp = opponent or OpponentStats(name="unknown")
    opp_type = opp.player_type
    exploit_tip = opp.exploit_notes

    if len(gs.hole_cards) < 2:
        return Decision("FOLD", 0, "Can't read cards", "LOW", 0.0, exploit_tip)

    spr = gs.my_stack / gs.pot if gs.pot > 0 else 99.0

    if gs.street == "preflop":
        return _decide_preflop(gs, opp_type, position, spr, exploit_tip)
    return _decide_postflop(gs, opp_type, position, spr, exploit_tip)


def _hand_rank_index(hole_cards: list) -> int:
    if len(hole_cards) < 2:
        return len(eq.HAND_RANKINGS)
    r1 = hole_cards[0][0].upper()
    s1 = hole_cards[0][1].lower()
    r2 = hole_cards[1][0].upper()
    s2 = hole_cards[1][1].lower()
    suited = (s1 == s2)
    ranks = "23456789TJQKA"
    ri1, ri2 = ranks.index(r1), ranks.index(r2)
    if ri2 > ri1:
        r1, r2 = r2, r1
    try:
        return eq.HAND_RANKINGS.index((r1, r2, suited))
    except ValueError:
        try:
            return eq.HAND_RANKINGS.index((r1, r2, not suited)) + 5
        except ValueError:
            return len(eq.HAND_RANKINGS) - 1


def _decide_preflop(gs, opp_type, position, spr, exploit_tip) -> Decision:
    hand_idx = _hand_rank_index(gs.hole_cards)
    total_hands = len(eq.HAND_RANKINGS)
    hand_percentile = hand_idx / total_hands

    base_range = OPEN_RANGE_BY_POSITION.get(position, 0.22)
    adj = RANGE_ADJUST_VS_OPPONENT.get(opp_type, 0.0)
    open_range = min(0.75, max(0.10, base_range + adj))
    threbet_range = THREBET_RANGE_BY_POSITION.get(position, 0.06)
    call_range = open_range * 0.65

    hand_label = " ".join(gs.hole_cards)
    bb = gs.big_blind

    if gs.call_amount <= bb * 1.2:
        if hand_percentile <= open_range:
            raise_size = round(max(gs.raise_amount, bb * 3.0), 2)
            if opp_type == "fish":
                raise_size = round(raise_size * 1.35, 2)
            return Decision(
                "RAISE", raise_size,
                f"{hand_label} | {position} | Open raise ({open_range:.0%} range)",
                "HIGH" if hand_percentile < 0.12 else "MEDIUM",
                0.0, exploit_tip
            )
        return Decision("FOLD", 0,
                        f"{hand_label} | {position} | Outside open range ({open_range:.0%})",
                        "MEDIUM", 0.0, exploit_tip)

    pot_odds = gs.call_amount / (gs.pot + gs.call_amount) if (gs.pot + gs.call_amount) > 0 else 0.5
    effective_call_range = call_range
    if opp_type == "tight_passive":
        effective_call_range *= 0.60
    elif opp_type == "fish":
        effective_call_range *= 1.20

    if hand_percentile <= threbet_range:
        reraise = round(gs.call_amount * 3.0, 2)
        return Decision(
            "RAISE", reraise,
            f"{hand_label} | {position} | 3-bet (top {threbet_range:.0%})",
            "HIGH", 0.0, exploit_tip
        )

    if hand_percentile <= effective_call_range:
        hand_equity = eq.monte_carlo_equity(gs.hole_cards, [], opp_type, num_simulations=300)
        if hand_equity > pot_odds + 0.04:
            return Decision(
                "CALL", 0,
                f"{hand_label} | equity {hand_equity:.0%} > pot odds {pot_odds:.0%}",
                "MEDIUM", hand_equity, exploit_tip
            )

    return Decision("FOLD", 0,
                    f"{hand_label} | {position} | Outside call range vs raise",
                    "HIGH", 0.0, exploit_tip)


def _decide_postflop(gs, opp_type, position, spr, exploit_tip) -> Decision:
    hand_equity = eq.monte_carlo_equity(
        gs.hole_cards, gs.community_cards, opp_type, num_simulations=600
    )
    pot_odds = gs.call_amount / (gs.pot + gs.call_amount) if gs.call_amount > 0 else 0.0
    is_late = pos.position_is_late(position)
    site_label = gs.hand_type or "?"
    commit_threshold = 0.65 if spr > 4 else (0.55 if spr > 2 else 0.45)

    if gs.call_amount == 0:
        if hand_equity >= commit_threshold:
            bet_pct = 0.75 if opp_type == "fish" else 0.60
            bet = round(gs.pot * bet_pct, 2)
            return Decision(
                "RAISE", bet,
                f"{site_label} | {hand_equity:.0%} equity | value bet ({bet_pct:.0%} pot)",
                "HIGH", hand_equity, exploit_tip
            )
        if is_late and gs.street in ("flop", "turn") and opp_type == "tight_passive":
            bluff = round(gs.pot * 0.55, 2)
            return Decision(
                "RAISE", bluff,
                f"{site_label} | bluff in position vs tight-passive",
                "LOW", hand_equity, exploit_tip
            )
        return Decision("CALL", 0,
                        f"{site_label} | {hand_equity:.0%} equity | check",
                        "MEDIUM", hand_equity, exploit_tip)

    if opp_type == "fish" and hand_equity < 0.45:
        return Decision("FOLD", 0,
                        f"{site_label} | {hand_equity:.0%} equity (vs fish — no bluff-catching)",
                        "HIGH", hand_equity, exploit_tip)

    if hand_equity >= commit_threshold and spr < 3:
        return Decision(
            "RAISE", gs.my_stack,
            f"{site_label} | {hand_equity:.0%} equity + low SPR ({spr:.1f}) — commit",
            "HIGH", hand_equity, exploit_tip
        )

    if hand_equity > pot_odds + 0.08:
        if hand_equity >= commit_threshold:
            raise_to = round(gs.call_amount * 2.5, 2)
            return Decision("RAISE", raise_to,
                            f"{site_label} | {hand_equity:.0%} — raise for value",
                            "HIGH", hand_equity, exploit_tip)
        return Decision("CALL", 0,
                        f"{site_label} | {hand_equity:.0%} > pot odds {pot_odds:.0%}",
                        "MEDIUM", hand_equity, exploit_tip)

    if gs.street in ("flop", "turn") and hand_equity > pot_odds - 0.05:
        return Decision("CALL", 0,
                        f"{site_label} | drawing — {hand_equity:.0%} equity, marginal call",
                        "LOW", hand_equity, exploit_tip)

    return Decision("FOLD", 0,
                    f"{site_label} | {hand_equity:.0%} equity < pot odds {pot_odds:.0%}",
                    "HIGH", hand_equity, exploit_tip)
