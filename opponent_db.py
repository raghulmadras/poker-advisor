"""
opponent_db.py — Persistent opponent stat tracking

Tracks every opponent's behavior across sessions in a local SQLite database.
After enough hands, classifies them so the decision engine can exploit them.

Stats tracked:
  vpip         : Voluntarily Put money In Pot (preflop, excluding BB)
  pfr          : Pre-Flop Raise frequency
  aggression   : Bet/raise actions vs call/check (postflop)
  fold_to_cbet : How often they fold to a continuation bet

Player types (assigned after MIN_HANDS_TO_CLASSIFY hands):
  fish          : High VPIP (>40%), low PFR (<15%)  — call with anything
  tight_passive : Low VPIP (<18%), low PFR (<8%)    — only strong hands, passive
  lag           : High VPIP (>35%), high PFR (>25%) — wide and aggressive
  tag           : Moderate VPIP (18-30%), PFR>15%   — solid and aggressive
  unknown       : < MIN_HANDS_TO_CLASSIFY hands seen
"""

import sqlite3
import os
from dataclasses import dataclass

DB_PATH = os.path.join(os.path.dirname(__file__), "opponents.db")
MIN_HANDS_TO_CLASSIFY = 15  # Need this many VPIP opportunities before classifying


@dataclass
class OpponentStats:
    name:             str
    hands_seen:       int   = 0
    vpip_opps:        int   = 0   # Hands where they could voluntarily put money in
    vpip_count:       int   = 0   # Times they actually did
    pfr_opps:         int   = 0   # Preflop raise opportunities
    pfr_count:        int   = 0   # Times they raised preflop
    agg_actions:      int   = 0   # Bet + raise actions (postflop)
    passive_actions:  int   = 0   # Call + check actions (postflop)
    fold_to_cbet:     int   = 0   # Times they folded to a cbet
    cbet_faced:       int   = 0   # Times they faced a cbet

    @property
    def vpip(self) -> float:
        return self.vpip_count / self.vpip_opps if self.vpip_opps > 0 else 0.0

    @property
    def pfr(self) -> float:
        return self.pfr_count / self.pfr_opps if self.pfr_opps > 0 else 0.0

    @property
    def aggression_factor(self) -> float:
        return self.agg_actions / self.passive_actions if self.passive_actions > 0 else 2.0

    @property
    def fold_to_cbet_pct(self) -> float:
        return self.fold_to_cbet / self.cbet_faced if self.cbet_faced > 0 else 0.5

    @property
    def player_type(self) -> str:
        if self.vpip_opps < MIN_HANDS_TO_CLASSIFY:
            return "unknown"
        v = self.vpip
        p = self.pfr
        if v > 0.40 and p < 0.15:
            return "fish"
        if v < 0.18 and p < 0.08:
            return "tight_passive"
        if v > 0.35 and p > 0.25:
            return "lag"
        if 0.18 <= v <= 0.32 and p > 0.14:
            return "tag"
        if v > 0.30:
            return "fish"  # Wide but not agressive = call-happy
        return "unknown"

    @property
    def exploit_notes(self) -> str:
        """One-line human-readable exploit tip."""
        pt = self.player_type
        tips = {
            "fish":          "NEVER bluff. Bet big for value. They call with anything.",
            "tight_passive": "Bluff freely. Fold to their bets — they have it.",
            "lag":           "Tighten up. 3-bet/4-bet light. Trap with strong hands.",
            "tag":           "Play solid. Don't bluff too much. Respect their raises.",
            "unknown":       f"Only {self.vpip_opps} hands — using default strategy.",
        }
        return tips.get(pt, "")


class OpponentDB:
    def __init__(self, db_path: str = DB_PATH):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS opponents (
                name            TEXT PRIMARY KEY,
                hands_seen      INTEGER DEFAULT 0,
                vpip_opps       INTEGER DEFAULT 0,
                vpip_count      INTEGER DEFAULT 0,
                pfr_opps        INTEGER DEFAULT 0,
                pfr_count       INTEGER DEFAULT 0,
                agg_actions     INTEGER DEFAULT 0,
                passive_actions INTEGER DEFAULT 0,
                fold_to_cbet    INTEGER DEFAULT 0,
                cbet_faced      INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    def get(self, name: str) -> OpponentStats:
        """Retrieve stats for a player. Creates entry if new."""
        cur = self.conn.execute(
            "SELECT * FROM opponents WHERE name = ?", (name,)
        )
        row = cur.fetchone()
        if row is None:
            self.conn.execute(
                "INSERT OR IGNORE INTO opponents (name) VALUES (?)", (name,)
            )
            self.conn.commit()
            return OpponentStats(name=name)

        cols = [d[0] for d in cur.description]
        data = dict(zip(cols, row))
        return OpponentStats(**data)

    def update(self, name: str, **kwargs):
        """Increment specific stat counters for a player."""
        if not kwargs:
            return
        # Ensure player row exists before updating
        self.conn.execute(
            "INSERT OR IGNORE INTO opponents (name) VALUES (?)", (name,)
        )
        sets = ", ".join(f"{k} = {k} + ?" for k in kwargs)
        vals = list(kwargs.values()) + [name]
        self.conn.execute(
            f"UPDATE opponents SET {sets} WHERE name = ?", vals
        )
        self.conn.commit()

    def record_preflop_action(self, name: str, voluntarily_in: bool, raised: bool):
        """Record one preflop decision for VPIP/PFR tracking."""
        updates = {"vpip_opps": 1, "pfr_opps": 1, "hands_seen": 1}
        if voluntarily_in:
            updates["vpip_count"] = 1
        if raised:
            updates["pfr_count"] = 1
        self.update(name, **updates)

    def record_postflop_action(self, name: str, aggressive: bool):
        """Record a postflop bet/raise (aggressive=True) or call/check (False)."""
        if aggressive:
            self.update(name, agg_actions=1)
        else:
            self.update(name, passive_actions=1)

    def record_fold_to_cbet(self, name: str, folded: bool):
        """Record whether a player folded to a continuation bet."""
        self.update(name, cbet_faced=1)
        if folded:
            self.update(name, fold_to_cbet=1)

    def get_all(self) -> list[OpponentStats]:
        """Return stats for all tracked players."""
        cur = self.conn.execute("SELECT * FROM opponents ORDER BY hands_seen DESC")
        cols = [d[0] for d in cur.description]
        return [OpponentStats(**dict(zip(cols, row))) for row in cur.fetchall()]

    def summary(self) -> str:
        """Print a table of all tracked opponents."""
        players = self.get_all()
        if not players:
            return "No opponents tracked yet."
        lines = [f"{'Name':<20} {'Type':<15} {'VPIP':>6} {'PFR':>6} {'Hands':>6}"]
        lines.append("-" * 58)
        for p in players:
            lines.append(
                f"{p.name:<20} {p.player_type:<15} "
                f"{p.vpip:>5.0%} {p.pfr:>5.0%} {p.vpip_opps:>6}"
            )
        return "\n".join(lines)


# Singleton instance used throughout the app
db = OpponentDB()
