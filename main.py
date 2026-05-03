"""
main.py — ClubWPT Gold Poker Advisor
Entry point. Run this while the poker site is open in your browser.

Usage:
    python main.py
"""

import time
import threading
import sys

import capture
import game_state
import engine
import overlay as ov
import config


def scan_loop(advisor: ov.AdvisorOverlay):
    """
    Main scan loop — runs in a background thread.
    Captures screen → detects table → parses state → decides → updates overlay.
    """
    print("[Advisor] Starting scan loop...")
    consecutive_failures = 0

    while True:
        try:
            screen = capture.capture_screen()
            table  = capture.find_table_bounds(screen)

            if table is None:
                consecutive_failures += 1
                if consecutive_failures >= 5:
                    advisor.set_status("⚠ Table not found", "#e74c3c")
                    print("[Advisor] Table not detected — is ClubWPT Gold open?")
                time.sleep(config.SCAN_INTERVAL)
                continue

            consecutive_failures = 0
            advisor.set_status("● scanning", "#27ae60")

            if not capture.is_player_turn(screen, table):
                advisor.set_waiting()
                time.sleep(config.SCAN_INTERVAL)
                continue

            # It's your turn — parse and decide
            gs = game_state.parse_game_state(screen, table)

            if len(gs.hole_cards) < 2:
                advisor.set_status("⚠ Can't read cards", "#e67e22")
                print(f"[Advisor] Could not read hole cards. State: {gs}")
                time.sleep(config.SCAN_INTERVAL)
                continue

            print(f"[Advisor] {gs}")
            decision = engine.decide(gs)
            print(f"[Advisor] Decision: {decision.display()} — {decision.reason}")

            advisor.update_decision(decision)

        except Exception as e:
            print(f"[Advisor] Error in scan loop: {e}")
            advisor.set_status("⚠ Error", "#e74c3c")

        time.sleep(config.SCAN_INTERVAL)


def main():
    print("=" * 50)
    print("  ClubWPT Gold Poker Advisor")
    print("=" * 50)
    print("  Open ClubWPT Gold in your browser and sit")
    print("  at a cash game table. The overlay will show")
    print("  your recommended action when it's your turn.")
    print()
    print("  Press Ctrl+C to quit.")
    print("=" * 50)

    advisor = ov.AdvisorOverlay()

    # Run scan loop in a background thread
    scan_thread = threading.Thread(
        target=scan_loop, args=(advisor,), daemon=True
    )
    scan_thread.start()

    # Run the overlay UI on the main thread (required by tkinter)
    try:
        advisor.run()
    except KeyboardInterrupt:
        print("\n[Advisor] Shutting down.")
        sys.exit(0)


if __name__ == "__main__":
    main()
