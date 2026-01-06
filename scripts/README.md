# Momoshop scraper

This folder contains a small Python utility for pulling product titles and prices from the Momoshop 3C > AI 手機 category page.

## Setup

```bash
python -m pip install requests beautifulsoup4 lxml
```

## Usage

Fetch and print AI 手機 products as plain text:

```bash
python scripts/momoshop_scraper.py
```

Limit the output and emit JSON:

```bash
python scripts/momoshop_scraper.py --limit 5 --json
```

Write results to a CSV file while still printing them:

```bash
python scripts/momoshop_scraper.py --limit 10 --csv ai_phones.csv
```

If you need to target another AI 手機 page, override the URL:

```bash
python scripts/momoshop_scraper.py --url "https://www.momoshop.com.tw/category/LgrpCategory.jsp?l_code=1912300000"
```
