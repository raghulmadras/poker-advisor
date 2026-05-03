"""
calibrate.py — Visual calibration tool

Run this to verify that all detected regions are correct for YOUR screen.
It captures a screenshot, draws all the detection boxes, and saves the result.

Usage:
    python calibrate.py

Then open 'calibration_check.png' to see if regions align with the UI.
Adjust values in config.py if they're off.
"""

import cv2
import numpy as np
import capture
import config

COLORS = {
    "hole":      (0, 255, 255),   # cyan
    "community": (255, 165, 0),   # orange
    "pot":       (0, 255, 0),     # green
    "buttons":   (255, 0, 0),     # red
    "stack":     (255, 0, 255),   # magenta
    "blinds":    (255, 255, 0),   # yellow
    "search":    (128, 128, 255), # light blue
}


def draw_region(img, table, prop, color, label=""):
    tx, ty, tw, th = table
    x1 = int(tx + prop[0] * tw)
    y1 = int(ty + prop[1] * th)
    x2 = int(tx + prop[2] * tw)
    y2 = int(ty + prop[3] * th)

    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    if label:
        cv2.putText(img, label, (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)


def main():
    print("[Calibrate] Capturing screen...")
    screen = capture.capture_screen()

    table = capture.find_table_bounds(screen)
    if table is None:
        print("[Calibrate] ERROR: Poker table not detected.")
        print("  Make sure ClubWPT Gold is open and a table is visible.")
        print("  If the table IS visible, the green HSV color range in config.py")
        print("  may need adjusting.")
        return

    print(f"[Calibrate] Table found at: x={table[0]}, y={table[1]}, "
          f"w={table[2]}, h={table[3]}")

    vis = screen.copy()
    tx, ty, tw, th = table
    cv2.rectangle(vis, (tx, ty), (tx + tw, ty + th), (255, 255, 255), 3)

    # Hole cards
    draw_region(vis, table, config.HOLE_CARD_1, COLORS["hole"], "Hole 1")
    draw_region(vis, table, config.HOLE_CARD_2, COLORS["hole"], "Hole 2")

    # Community cards
    for i, prop in enumerate(config.COMMUNITY_CARDS):
        draw_region(vis, table, prop, COLORS["community"], f"Comm{i+1}")

    # Pot
    draw_region(vis, table, config.POT_REGION, COLORS["pot"], "Pot")

    # Buttons
    draw_region(vis, table, config.FOLD_BTN_REGION,  COLORS["buttons"], "Fold")
    draw_region(vis, table, config.CALL_BTN_REGION,  COLORS["buttons"], "Call")
    draw_region(vis, table, config.RAISE_BTN_REGION, COLORS["buttons"], "Raise")
    draw_region(vis, table, config.BUTTON_SEARCH_REGION, COLORS["search"], "Btn Search")

    # Stack / blinds
    draw_region(vis, table, config.MY_STACK_REGION,  COLORS["stack"],  "My Stack")
    draw_region(vis, table, config.BLINDS_REGION,    COLORS["blinds"], "Blinds")
    draw_region(vis, table, config.HAND_TYPE_REGION, COLORS["pot"],    "Hand Type")

    # Is player turn?
    is_turn = capture.is_player_turn(screen, table)
    status = "YOUR TURN" if is_turn else "Waiting"
    cv2.putText(vis, f"Status: {status}", (tx + 10, ty + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                (0, 255, 0) if is_turn else (100, 100, 100), 2)

    # Save output
    out_path = "calibration_check.png"
    cv2.imwrite(out_path, vis)
    print(f"[Calibrate] Saved to: {out_path}")
    print()
    print("Open 'calibration_check.png' and verify:")
    print("  CYAN boxes     = your hole cards")
    print("  ORANGE boxes   = community card slots")
    print("  GREEN boxes    = pot / hand type label")
    print("  RED boxes      = action buttons (Fold/Call/Raise)")
    print("  MAGENTA box    = your stack")
    print("  YELLOW box     = blinds display")
    print()
    print("If any box is off, adjust the proportional values in config.py.")


if __name__ == "__main__":
    main()
