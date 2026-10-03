import csv
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from backend.app.config.settings import settings

logger = logging.getLogger(__name__)

class KaggleIngestor:
    """Ingests structured & unstructured financial news from Kaggle dataset."""

    def __init__(self):
        self.kaggle_dir = settings.KAGGLE_DIR
        self.sample_csv_path = self.kaggle_dir / "financial_news_sample.csv"
        self._ensure_sample_file()

    def _ensure_sample_file(self):
        """Creates sample institutional Kaggle dataset if not already present."""
        if not self.sample_csv_path.exists():
            rows = [
                ["headline", "ticker", "date", "publisher"],
                ["Regional bank credit default swaps widen sharply as deposit outflows accelerate", "KRE", "2024-03-10 14:00:00", "Benzinga"],
                ["Tesla faces National Highway Traffic Safety Administration probe over autonomous steering systems", "TSLA", "2024-03-11 09:15:00", "CNBC"],
                ["Pfizer cuts full-year revenue outlook after severe decline in seasonal vaccine sales", "PFE", "2024-03-12 11:30:00", "MarketWatch"],
                ["Microsoft secures long-term nuclear power agreement to supply AI data center clusters", "MSFT", "2024-03-13 16:45:00", "Wall Street Journal"],
                ["Chevron acquires deepwater Gulf of Mexico exploration assets for $6.2 billion", "CVX", "2024-03-14 08:20:00", "Reuters"],
                ["Boeing faces FAA production cap extension following door plug blowout inquiry", "BA", "2024-03-14 13:00:00", "Bloomberg"]
            ]
            try:
                with open(self.sample_csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerows(rows)
            except Exception as e:
                logger.error(f"Error creating Kaggle sample CSV: {e}")

    def load_from_csv(self, file_path: Path = None, limit: int = 50) -> List[Dict[str, Any]]:
        target_path = file_path or self.sample_csv_path
        if not target_path.exists():
            self._ensure_sample_file()

        records = []
        try:
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    # Dynamically identify columns
                    headline = (
                        row.get("headline") or row.get("title") or row.get("news") or ""
                    ).strip()
                    if not headline:
                        continue

                    ticker = (row.get("ticker") or row.get("stock") or row.get("symbol") or "").strip().upper()
                    date_str = row.get("date") or row.get("timestamp") or ""
                    
                    try:
                        published_at = datetime.fromisoformat(date_str) if date_str else datetime.utcnow()
                    except Exception:
                        published_at = datetime.utcnow()

                    art_hash = hashlib.sha256(f"Kaggle_{headline}_{date_str}".encode("utf-8")).hexdigest()

                    records.append({
                        "id": art_hash,
                        "source": "Kaggle",
                        "title": headline,
                        "ticker_hint": ticker,
                        "url": None,
                        "domain": row.get("publisher", "Kaggle Dataset"),
                        "published_at": published_at,
                        "content": headline
                    })
                    count += 1
                    if count >= limit:
                        break
        except Exception as e:
            logger.error(f"Failed to read Kaggle CSV ({target_path}): {e}")

        return records
