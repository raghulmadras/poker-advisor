"""
overlay.py — Always-on-top recommendation window

Shows the current decision in large, clear text so you can act
without looking away from the poker table.
"""

import tkinter as tk
import threading
from engine import Decision


ACTION_COLORS = {
    "FOLD":  {"bg": "#c0392b", "fg": "white"},
    "CALL":  {"bg": "#27ae60", "fg": "white"},
    "RAISE": {"bg": "#e67e22", "fg": "white"},
}

CONFIDENCE_SYMBOL = {"HIGH": "●●●", "MEDIUM": "●●○", "LOW": "●○○"}


class AdvisorOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Poker Advisor")
        self.root.attributes("-topmost", True)       # Always on top
        self.root.attributes("-alpha", 0.92)         # Slight transparency
        self.root.overrideredirect(False)
        self.root.resizable(False, False)

        # Position top-right corner of screen
        screen_w = self.root.winfo_screenwidth()
        self.root.geometry(f"300x140+{screen_w - 320}+20")

        # ── Layout ────────────────────────────────────────────────────────────
        self.frame = tk.Frame(self.root, bg="#1a1a2e", padx=10, pady=8)
        self.frame.pack(fill="both", expand=True)

        # Header
        tk.Label(
            self.frame, text="♠ POKER ADVISOR",
            bg="#1a1a2e", fg="#7f8c8d",
            font=("Helvetica", 9, "bold")
        ).pack(anchor="w")

        # Main action label
        self.action_label = tk.Label(
            self.frame, text="Waiting...",
            bg="#1a1a2e", fg="white",
            font=("Helvetica", 32, "bold"),
            width=12, anchor="center"
        )
        self.action_label.pack(pady=(4, 0))

        # Reason label
        self.reason_label = tk.Label(
            self.frame, text="",
            bg="#1a1a2e", fg="#bdc3c7",
            font=("Helvetica", 9),
            wraplength=280, justify="left"
        )
        self.reason_label.pack(anchor="w", pady=(2, 0))

        # Confidence + status row
        bottom = tk.Frame(self.frame, bg="#1a1a2e")
        bottom.pack(fill="x", pady=(4, 0))

        self.confidence_label = tk.Label(
            bottom, text="",
            bg="#1a1a2e", fg="#f39c12",
            font=("Helvetica", 9)
        )
        self.confidence_label.pack(side="left")

        self.status_label = tk.Label(
            bottom, text="● scanning",
            bg="#1a1a2e", fg="#27ae60",
            font=("Helvetica", 8)
        )
        self.status_label.pack(side="right")

        # Allow dragging the window
        self.frame.bind("<ButtonPress-1>", self._start_drag)
        self.frame.bind("<B1-Motion>", self._on_drag)

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        x = self.root.winfo_x() + event.x - self._drag_x
        y = self.root.winfo_y() + event.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def update_decision(self, decision: Decision):
        """Update the overlay with a new decision. Thread-safe."""
        self.root.after(0, self._do_update, decision)

    def _do_update(self, decision: Decision):
        colors = ACTION_COLORS.get(decision.action, ACTION_COLORS["FOLD"])
        self.frame.config(bg=colors["bg"])
        self.action_label.config(
            text=decision.display(),
            bg=colors["bg"],
            fg=colors["fg"]
        )
        self.reason_label.config(
            text=decision.reason,
            bg=colors["bg"],
            fg="white"
        )
        self.confidence_label.config(
            text=CONFIDENCE_SYMBOL.get(decision.confidence, ""),
            bg=colors["bg"],
            fg="white"
        )

    def set_status(self, msg: str, color: str = "#27ae60"):
        self.root.after(0, lambda: self.status_label.config(text=msg, fg=color))

    def set_waiting(self):
        """Show neutral 'waiting for turn' state."""
        self.root.after(0, self._do_waiting)

    def _do_waiting(self):
        self.frame.config(bg="#1a1a2e")
        self.action_label.config(text="Waiting...", bg="#1a1a2e", fg="#7f8c8d")
        self.reason_label.config(text="Not your turn", bg="#1a1a2e")
        self.confidence_label.config(text="", bg="#1a1a2e")

    def run(self):
        self.root.mainloop()
