"""
Test configuration parameters for newsletter generation.
This module allows for storing and reusing input parameters for testing.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional


class TestConfig:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.params = {
            "keywords": [],
            "domain": "",
            "newsletter_count": 1,
            "language": "ko",
            "topic": "",
            "date_range": 7,  # Default to 7 days
            "additional_params": {},
        }
        self.intermediate_data_file = None

    def set_keywords(self, keywords: List[str]) -> None:
        """Set search keywords for news scraping."""
        self.params["keywords"] = keywords

    def set_domain(self, domain: str) -> None:
        """Set domain/topic area for the newsletter."""
        self.params["domain"] = domain

    def set_newsletter_count(self, count: int) -> None:
        """Set number of newsletters to generate."""
        self.params["newsletter_count"] = count

    def set_language(self, language: str) -> None:
        """Set language for generation."""
        self.params["language"] = language

    def set_topic(self, topic: str) -> None:
        """Set specific topic for the newsletter."""
        self.params["topic"] = topic

    def set_date_range(self, days: int) -> None:
        """Set date range for news scraping in days."""
        self.params["date_range"] = days

    def add_param(self, key: str, value) -> None:
        """Add additional custom parameter."""
        self.params["additional_params"][key] = value

    def set_intermediate_data(self, file_path: str) -> None:
        """Set path to existing intermediate data for testing."""
        if os.path.exists(file_path):
            self.intermediate_data_file = file_path
        else:
            raise FileNotFoundError(f"Intermediate data file not found: {file_path}")

    def save_config(self, file_path: Optional[str] = None) -> str:
        """Save current configuration to a file."""
        import json

        if file_path is None:
            file_path = f"config/test_config_{self.timestamp}.json"

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        config_data = {
            "timestamp": self.timestamp,
            "params": self.params,
            "intermediate_data_file": self.intermediate_data_file,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        return file_path

    @classmethod
    def load_config(cls, file_path: str) -> "TestConfig":
        """Load configuration from a file."""
        import json

        with open(file_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        config = cls()
        config.timestamp = config_data.get("timestamp", config.timestamp)
        config.params = config_data.get("params", config.params)
        config.intermediate_data_file = config_data.get("intermediate_data_file")

        return config
