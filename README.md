# Budget Receipt Reader

Snap a photo of a receipt (or upload one) and it gets read by Claude, categorized, and written straight into your Google Sheets budget tracker. Also handles opening a new budget cycle — duplicating your template tab, writing start/end dates, income, and savings entries automatically.

Built as a personal tool for a pay-cycle budget that doesn't follow calendar months (e.g. 25th–25th).

## How it works

1. You take a photo of a receipt (camera or gallery) from the web page.
2. The image is sent to Claude, which extracts the store name, purchase date, and a breakdown of items grouped by spending category, returned as structured JSON.
3. That data is written as one or more rows into the current cycle's "Expense Tracker" section of your Google Sheet — one row per category.
4. A local SQLite database keeps track of which tab is the "current" one and how long it's valid for, so the app doesn't have to re-scan every tab in the spreadsheet on every request.
5. When your current cycle is ending, a form on the page lets you open the next one: it duplicates a template tab, names it based on the new cycle's end month, and fills in the dates, income sources, and savings entries you provide.

## Project structure

```
.
├── app.py              # Flask routes — thin, just wiring between the pieces below
├── config.py           # Loads credentials/env vars, builds the Anthropic and Sheets clients
├── sheets.py           # All Google Sheets logic — reading/writing cells, duplicating tabs, tab lookups
├── claude_client.py    # Builds the extraction prompt and calls the Claude API
├── db.py               # SQLite caching for "what's the current tab, and until when"
├── public/
│   └── index.html      # The frontend — camera/gallery upload, new-cycle form
├── requirements.txt
├── .env                # Not committed — see setup below
└── .gitignore
```

## Setup

### 1. Google Cloud

- Create a Google Cloud project and enable the **Google Sheets API**.
- Create a **service account**. If your organization blocks downloadable service account keys, either use a personal Google account for this project, or run the app on a Compute Engine VM with the service account attached directly (no key file needed).
- If you do use a key file, download it and keep it **out of version control** (see `.gitignore`).
- Share your budget Google Sheet with the service account's email address, with **Editor** access.

### 2. Anthropic API key

Get one from [console.anthropic.com](https://console.anthropic.com) → Settings → API Keys.

### 3. Environment variables

Create a `.env` file (or set these as real environment variables / Codespaces secrets):

```
ANTHROPIC_API_KEY=your_key_here
SHEET_ID=your_google_sheet_id
```

The Sheet ID is the long string in your sheet's URL, between `/d/` and `/edit`.

### 4. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Sheet template requirements

The app expects your spreadsheet to have a tab named exactly `Budget I` as the template, containing:

- `G9` — cycle start date
- `G10` — cycle end date
- An income section starting around row 27 (name in column D, amount in columns G and J)
- A savings section starting around row 42 (same layout)
- An "Expense Tracker" section starting at row 62, with Date in column D, Amount in column G, Category in column I, Notes in column K

New monthly tabs are created by duplicating `Budget I`.

### 6. Seed the database (first run only)

If you already have a tab for your current cycle created manually, tell the app about it once:

```bash
python3 -c "
from db import set_current_tab
set_current_tab('me', 'YOUR_SHEET_ID', 'YourCurrentTabName', '2026-08-25')
"
```

### 7. Run it

```bash
python3 app.py
```

Open the printed URL in a browser — on your phone, this lets you take a photo directly and send it to the app.

## Notes on categories

Spending categories are hardcoded in `claude_client.py` (`categories` list) and should match whatever dropdown list your sheet's Expense Tracker validates against, so Claude's output lines up cleanly with your sheet.

## Known limitations

- Single-user only — the app assumes one person, one sheet, one set of credentials.
- No confirm/edit step before writing — whatever Claude extracts is written directly to the sheet.
- No duplicate-receipt detection.
