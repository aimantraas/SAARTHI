"""
Configuration and constants for the LeadGen system.
"""
import os
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

def _load_dotenv(path: Path) -> dict:
    """
    Minimal .env loader.

    - Does not override already-set environment variables.
    - Supports basic KEY=VALUE lines and ignores comments/blank lines.
    """
    data: dict = {}
    if not path.exists():
        return data

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :].lstrip()
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue

            # Strip trailing comments for unquoted values (best-effort).
            if value and value[0] not in {"'", '"'} and "#" in value:
                value = value.split("#", 1)[0].rstrip()

            # Strip wrapping quotes.
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]

            data[key] = value
            os.environ.setdefault(key, value)

    return data


# Load .env file from project root manually
env_path = Path(__file__).parent.parent / ".env"
env_data = _load_dotenv(env_path)


@dataclass
class LeadGenConfig:
    """Configuration for LeadGen workflow."""
    
    # API Keys
    serp_api_key: str = field(default_factory=lambda: os.environ.get("SERP_API_KEY", ""))
    apify_api_token: str = field(default_factory=lambda: os.environ.get("APIFY_API_TOKEN", ""))
    email_verify_api_key: str = field(default_factory=lambda: os.environ.get("EMAIL_VERIFY_API_KEY", ""))
    
    # Google Sheets
    google_sheet_id: str = field(default_factory=lambda: os.environ.get("GOOGLE_SHEET_ID", ""))
    google_credentials_path: str = field(default_factory=lambda: os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json"))
    
    # Search Parameters
    companies: List[str] = field(default_factory=lambda: ["Retail"])
    position: str = "Head operation"
    country: str = "India"
    country_code: str = "IN"
    
    # Rate Limiting (seconds)
    serp_api_wait_min: float = 2.0
    serp_api_wait_max: float = 5.0
    apify_poll_interval: float = 5.0
    email_verify_wait_min: float = 1.0
    email_verify_wait_max: float = 2.0
    
    # Batch Processing
    batch_size: int = 10
    start_index_begin: int = 10
    start_index_end: int = 200
    start_index_step: int = 10
    email_batch_limit: int = 50
    
    # Email Verification Statuses
    email_status_valid: str = "valid"
    email_status_invalid: str = "invalid"
    email_status_catch_all: str = "catch_all"
    email_status_role_based: str = "role_based"
    email_status_unknown: str = "unknown"
    email_status_process: str = "PROCESS"
    
    @property
    def start_indexes(self) -> List[int]:
        """Generate start indexes for pagination."""
        return list(range(self.start_index_begin, self.start_index_end + 1, self.start_index_step))


@dataclass
class SheetColumns:
    """Google Sheets column mappings."""
    
    linkedin_url: str = "LinkedinUrl"
    full_name: str = "FullName"
    first_name: str = "FirstName"
    last_name: str = "LastName"
    connections: str = "Connections"
    follower: str = "Follower"
    email: str = "Email"
    email_verification: str = " email verification"
    mobile_number: str = "mobileNumber"
    headline: str = "headline"
    address_country_only: str = "address Country Only"
    job_title: str = "jobTitle"
    job_location: str = "jobLocation"
    company_name: str = "companyName"
    company_industry: str = "companyIndustry"
    company_website: str = "companyWebsite"
    company_linkedin: str = "companyLinkedin"
    company_size: str = "companySize"
    job_started_on: str = "jobStartedOn"
    current_job_duration: str = "currentJobDuration"
    address_without_country: str = "addressWithoutCountry"
    followers: str = "followers"
    snippet: str = "snippet"
    email_type: str = "emailType"
    status: str = "status"
    about: str = "about"
    name: str = "name"
    displayed_link: str = "displayed_link"


# Global configuration instance
config = LeadGenConfig()
sheet_columns = SheetColumns()
