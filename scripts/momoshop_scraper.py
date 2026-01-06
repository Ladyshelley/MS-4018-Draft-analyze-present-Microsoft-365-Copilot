"""Momoshop 3C AI phone scraper.

This script downloads product titles and prices from the Momoshop 3C -> AI 手機
category page and prints them in a simple table or JSON format.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

DEFAULT_URL = (
    "https://www.momoshop.com.tw/category/LgrpCategory.jsp"
    "?l_code=1912300000&mdiv=1099600000-bt_0_996_10-&ctype=B"
)
DEFAULT_FILTER = "AI手機"


@dataclass
class Product:
    """Represents a single product listing."""

    title: str
    price: Optional[str]
    category: Optional[str]

    def matches_keyword(self, keyword: str) -> bool:
        normalized = keyword.replace(" ", "").lower()
        haystack = " ".join(filter(None, [self.category, self.title]))
        return normalized in haystack.replace(" ", "").lower()


def fetch_html(url: str, *, timeout: int = 15) -> str:
    """Download the HTML for the given URL.

    Parameters
    ----------
    url: str
        Target Momoshop category URL.
    timeout: int
        Request timeout in seconds.
    """

    session = requests.Session()
    session.trust_env = False
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
    }
    response = session.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return response.text


def _text_or_none(element) -> Optional[str]:
    if not element:
        return None
    text = element.get_text(strip=True)
    return text if text else None


def _parse_json_metadata(li) -> Optional[dict]:
    raw = li.get("data-ec") or li.get("ec-data") or li.get("data-gtm")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _extract_from_cards(soup: BeautifulSoup) -> List[Product]:
    candidates: Iterable = soup.select(
        "li[data-index], li.goodsItemLi, li[class*=prd], li[class*=goodsItem]"
    )
    products: List[Product] = []
    for li in candidates:
        title = None
        price = None

        title_node = li.select_one("h3, p.prdName, p[class*=name], div[class*=name]")
        if not title_node:
            title_node = li.find("a", attrs={"title": True})
        title = _text_or_none(title_node)

        price_node = li.select_one(
            "span.price, span[class*=price], em[class*=price], b[class*=price]"
        )
        if not price_node:
            # look for NT$ formatted numbers
            match = re.search(r"NT\$?\s*([0-9,]+)", li.get_text())
            if match:
                price = match.group(1)
        else:
            price = _text_or_none(price_node)

        meta = _parse_json_metadata(li)
        category = None
        if meta:
            category = meta.get("cateLevel2Name") or meta.get("cateLevel1Name")

        if title:
            products.append(Product(title=title, price=price, category=category))
    return products


def _extract_from_scripts(soup: BeautifulSoup) -> List[Product]:
    products: List[Product] = []
    pattern = re.compile(r"\{[^\}]*?goodsName\s*:\s*\"?(.*?)\"?[^\}]*?price\s*:?\s*\"?([0-9,]+)\"?[^\}]*?\}")
    for script in soup.find_all("script"):
        text = script.string or script.text
        if not text:
            continue
        for match in pattern.finditer(text):
            title, price = match.groups()
            products.append(Product(title=title, price=price, category=None))
    return products


def extract_products(html: str) -> List[Product]:
    soup = BeautifulSoup(html, "lxml")
    products = _extract_from_cards(soup)
    if not products:
        products = _extract_from_scripts(soup)
    return products


def filter_products(products: Iterable[Product], keyword: str) -> List[Product]:
    return [product for product in products if product.matches_keyword(keyword)]


def format_products(products: Iterable[Product]) -> str:
    lines = []
    for product in products:
        price_part = product.price or "N/A"
        category_part = f" ({product.category})" if product.category else ""
        lines.append(f"- {product.title}{category_part}: {price_part}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract Momoshop 3C AI 手機 titles and prices.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Momoshop category URL")
    parser.add_argument(
        "--keyword",
        default=DEFAULT_FILTER,
        help="Text that must appear in the category or title (e.g. 'AI手機').",
    )
    parser.add_argument(
        "--json", dest="as_json", action="store_true", help="Output JSON instead of text"
    )
    parser.add_argument(
        "--csv", dest="csv_path", default=None, help="Optional path to write results as CSV"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of items to print after filtering.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    html = fetch_html(args.url)
    products = extract_products(html)
    filtered = filter_products(products, args.keyword)
    if args.limit is not None:
        filtered = filtered[: args.limit]

    if args.csv_path is not None:
        with open(args.csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["title", "price", "category"])
            for product in filtered:
                writer.writerow([product.title, product.price or "", product.category or ""])

    if not filtered:
        print("No matching products found.")
        return

    if args.as_json:
        payload = [product.__dict__ for product in filtered]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_products(filtered))

    if args.csv_path is not None:
        print(f"Saved {len(filtered)} products to {args.csv_path}")


if __name__ == "__main__":
    main()
