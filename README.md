# ClubWPT Gold Poker Advisor — Setup Guide

## What this does
Watches your screen while you play on ClubWPT Gold.  
When it's your turn, a small overlay window tells you exactly what to do:  
**FOLD**, **CALL**, or **RAISE to X.XX**

---

## Step 1 — Install Python
You need Python 3.11 or newer.  
Download from: https://www.python.org/downloads/

---

## Step 2 — Install Tesseract OCR
Tesseract reads text from the screen (card ranks, pot size, etc.).

**Mac:**
```bash
brew install tesseract
```

**Windows:**
1. Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to: `C:\Program Files\Tesseract-OCR\`
3. Open `config.py` and uncomment + set:
   ```python
   TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
   ```

**Linux:**
```bash
sudo apt install tesseract-ocr
```

---

## Step 3 — Install Python packages
Open a terminal in the `poker_advisor` folder and run:
```bash
pip install -r requirements.txt
```

---

## Step 4 — Calibrate regions
1. Open ClubWPT Gold in your browser and **sit at a cash game table**
2. Make sure a hand is in progress (cards are dealt, action buttons visible)
3. Run:
   ```bash
   python calibrate.py
   ```
4. Open the saved `calibration_check.png` file
5. Check that the colored boxes align with the correct parts of the UI
6. If they're off, adjust the proportional values in `config.py`

---

## Step 5 — Run the advisor
```bash
python main.py
```

A small overlay window appears in the top-right corner of your screen.  
It will say **Waiting...** until it's your turn, then show your recommended action.

You can **drag the overlay window** anywhere on your screen.

---

## Troubleshooting

**"Table not found"**  
→ The green table color isn't matching. Try adjusting `TABLE_HSV_LOWER/UPPER` in `config.py`.

**Cards reading wrong**  
→ Run `calibrate.py` and check if CYAN boxes cover your hole cards.  
→ Adjust `HOLE_CARD_1` and `HOLE_CARD_2` proportions in `config.py`.

**Overlay shows wrong action when checking manually**  
→ The decision engine uses real poker math. It won't always match your gut — trust the math, especially in this soft player pool.

---

## Notes
- Works on **cash game tables** (ring games). Tournament support can be added later.
- The advisor is calibrated for ClubWPT Gold's unique **8-max straddle + ante** format.
- Runs on **Windows, Mac, and Linux**.
