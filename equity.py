"""
equity.py — Monte Carlo equity calculator

Instead of computing equity vs a random hand (naive), we estimate equity
vs the opponent's likely range based on their player type profile.

Player types and their estimated preflop ranges:
  fish/calling_station : top 60% of hands (plays almost anything)
  tight_passive        : top 15% of hands (only strong hands)
  lag                  : top 40%, aggressive (wide and raises a lot)
  tag                  : top 22% (solid, aggressive)
  unknown              : top 35% (conservative estimate)
"""

import random
from treys import Card, Deck, Evaluator

evaluator = Evaluator()

# ── OPPONENT RANGE DEFINITIONS ────────────────────────────────────────────────
# Preflop hand ranges as percentage of all hands.
# We represent each range as a list of hand combos to sample from.
# These are calibrated for ClubWPT Gold's straddle+ante dead money structure
# (ranges slightly wider than standard due to better pot odds preflop).

PLAYER_TYPE_RANGE_PCT = {
    "fish":          0.65,   # Calling station — plays almost anything
    "tight_passive": 0.15,   # Rock — only premiums
    "lag":           0.42,   # Loose aggressive — wide and attacks
    "tag":           0.22,   # Solid aggressive — standard strong range
    "unknown":       0.35,   # Default when not enough data
}

# All 169 unique preflop hands ranked by strength (Chen formula approximation)
# Format: (rank1, rank2, suited) — True = suited, False = offsuit
# Ordered best → worst
HAND_RANKINGS = [
    ("A","A",False),("K","K",False),("Q","Q",False),("J","J",False),
    ("A","K",True), ("T","T",False),("A","Q",True), ("A","K",False),
    ("A","J",True), ("K","Q",True), ("9","9",False),("A","T",True),
    ("A","Q",False),("8","8",False),("K","J",True), ("Q","J",True),
    ("K","T",True), ("A","J",False),("Q","T",True), ("J","T",True),
    ("A","9",True), ("K","Q",False),("7","7",False),("A","8",True),
    ("T","9",True), ("9","8",True), ("K","9",True), ("J","9",True),
    ("A","7",True), ("K","J",False),("Q","9",True), ("T","8",True),
    ("A","5",True), ("A","4",True), ("A","3",True), ("A","2",True),
    ("A","6",True), ("8","7",True), ("Q","J",False),("6","6",False),
    ("K","8",True), ("J","8",True), ("7","6",True), ("Q","T",False),
    ("A","T",False),("5","5",False),("9","7",True), ("J","T",False),
    ("K","7",True), ("8","6",True), ("T","7",True), ("K","T",False),
    ("A","9",False),("4","4",False),("6","5",True), ("Q","9",False),
    ("K","6",True), ("3","3",False),("5","4",True), ("Q","8",True),
    ("9","6",True), ("T","9",False),("7","5",True), ("K","5",True),
    ("2","2",False),("J","9",False),("8","5",True), ("K","9",False),
    ("A","8",False),("J","7",True), ("6","4",True), ("T","8",False),
    ("9","8",False),("K","4",True), ("5","3",True), ("Q","7",True),
    ("K","3",True), ("7","4",True), ("K","8",False),("A","7",False),
    ("8","7",False),("4","3",True), ("9","5",True), ("K","2",True),
    ("Q","6",True), ("J","8",False),("A","6",False),("A","5",False),
    ("7","6",False),("8","4",True), ("Q","5",True), ("9","7",False),
    ("6","3",True), ("A","4",False),("Q","4",True), ("T","7",False),
    ("J","6",True), ("5","4",False),("8","6",False),("Q","3",True),
    ("A","3",False),("5","2",True), ("J","5",True), ("6","5",False),
    ("Q","2",True), ("A","2",False),("J","4",True), ("4","2",True),
    ("T","6",True), ("8","5",False),("9","4",True), ("7","5",False),
    ("3","2",True), ("J","3",True), ("J","6",False),("Q","8",False),
    ("9","3",True), ("J","2",True), ("6","4",False),("T","5",True),
    ("J","7",False),("9","6",False),("T","4",True), ("8","3",True),
    ("Q","7",False),("4","3",False),("7","4",False),("T","3",True),
    ("9","2",True), ("8","2",True), ("T","2",True), ("J","5",False),
    ("5","3",False),("6","3",False),("Q","6",False),("7","2",True),
    ("T","6",False),("5","2",False),("8","4",False),("9","5",False),
    ("4","2",False),("J","4",False),("Q","5",False),("3","2",False),
    ("9","4",False),("T","5",False),("8","3",False),("J","3",False),
    ("6","2",True), ("7","3",True), ("Q","4",False),("J","2",False),
    ("9","3",False),("T","4",False),("6","2",False),("7","2",False),
    ("8","2",False),("Q","3",False),("T","3",False),("7","3",False),
    ("Q","2",False),("9","2",False),("T","2",False),("6","1",False),  # padding
]

RANKS = "23456789TJQKA"
SUITS = "shdc"

def _hand_to_cards(rank1: str, rank2: str, suited: bool, blocked: list) -> list[str] | None:
    """Try to build a valid 2-card hand not conflicting with already-dealt cards."""
    blocked_set = set(blocked)
    suit_pairs = [(s1, s2) for s1 in SUITS for s2 in SUITS
                  if (s1 == s2) == suited or not suited]

    random.shuffle(suit_pairs)
    for s1, s2 in suit_pairs:
        if rank1 == rank2 and s1 == s2:
            continue
        c1 = f"{rank1}{s1}"
        c2 = f"{rank2}{s2}"
        if c1 not in blocked_set and c2 not in blocked_set and c1 != c2:
            return [c1, c2]
    return None


def get_range(player_type: str) -> list[tuple]:
    """Return the hand range (list of hand combos) for a given player type."""
    pct = PLAYER_TYPE_RANGE_PCT.get(player_type, 0.35)
    cutoff = int(len(HAND_RANKINGS) * pct)
    return HAND_RANKINGS[:cutoff]


def monte_carlo_equity(
    hole_cards: list[str],
    community_cards: list[str],
    player_type: str = "unknown",
    num_simulations: int = 800,
) -> float:
    """
    Estimate our equity via Monte Carlo simulation against the opponent's
    estimated range.

    Returns win probability (0.0–1.0).
    """
    if len(hole_cards) < 2:
        return 0.40

    known_cards = hole_cards + community_cards
    opponent_range = get_range(player_type)

    wins = 0
    ties = 0
    valid_sims = 0

    for _ in range(num_simulations):
        # Sample opponent hand from their range
        hand_combo = random.choice(opponent_range)
        r1, r2, suited = hand_combo
        opp_hand = _hand_to_cards(r1, r2, suited, known_cards)
        if opp_hand is None:
            continue

        # Build remaining deck
        all_blocked = known_cards + opp_hand
        remaining_deck = [
            f"{r}{s}" for r in RANKS for s in SUITS
            if f"{r}{s}" not in all_blocked
        ]
        random.shuffle(remaining_deck)

        # Deal out remaining community cards
        board = list(community_cards)
        needed = 5 - len(board)
        if needed > len(remaining_deck):
            continue
        board += remaining_deck[:needed]

        # Evaluate hands
        try:
            my_cards  = [Card.new(c) for c in hole_cards]
            opp_cards = [Card.new(c) for c in opp_hand]
            board_cards = [Card.new(c) for c in board]

            my_rank  = evaluator.evaluate(board_cards, my_cards)
            opp_rank = evaluator.evaluate(board_cards, opp_cards)

            # Lower rank = stronger hand in treys
            if my_rank < opp_rank:
                wins += 1
            elif my_rank == opp_rank:
                ties += 1

            valid_sims += 1
        except Exception:
            continue

    if valid_sims == 0:
        return 0.40

    return (wins + ties * 0.5) / valid_sims
