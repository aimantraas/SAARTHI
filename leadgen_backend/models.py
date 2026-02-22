"""
Data models for the LeadGen system.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class SearchParameters:
    """Search parameters for SerpAPI queries."""
    q: Optional[str] = None
    engine: Optional[str] = None


@dataclass
class SearchMetadata:
    """Search metadata from SerpAPI response."""
    id: Optional[str] = None
    engine: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class ContactInfo:
    """Contact information extracted from various sources."""
    name: Optional[str] = None
    headline: Optional[str] = None
    emails: List[str] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    about: Optional[str] = None
    address: Optional[str] = None
    sources: List[str] = field(default_factory=list)


@dataclass
class MetaInfo:
    """Metadata for a contact record."""
    query: Optional[str] = None
    engine: Optional[str] = None
    id: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class SerpAPIResult:
    """Result from SerpAPI google_ai_mode search."""
    name: Optional[str] = None
    headline: Optional[str] = None
    emails: List[str] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    about: Optional[str] = None
    address: Optional[str] = None
    sources: List[str] = field(default_factory=list)
    meta: MetaInfo = field(default_factory=MetaInfo)


@dataclass
class LinkedInProfile:
    """LinkedIn profile data from Apify scraper."""
    linkedin_url: Optional[str] = None
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    headline: Optional[str] = None
    connections: Optional[int] = None
    followers: Optional[int] = None
    email: Optional[str] = None
    mobile_number: Optional[str] = None
    job_title: Optional[str] = None
    job_location: Optional[str] = None
    company_name: Optional[str] = None
    company_industry: Optional[str] = None
    company_website: Optional[str] = None
    company_linkedin: Optional[str] = None
    company_size: Optional[str] = None
    job_started_on: Optional[str] = None
    current_job_duration: Optional[str] = None
    address_country_only: Optional[str] = None
    address_without_country: Optional[str] = None
    about: Optional[str] = None


@dataclass
class OrganicResult:
    """Organic search result from SerpAPI Google search."""
    search_id: Optional[str] = None
    query: Optional[str] = None
    position: Optional[int] = None
    page_next: Optional[str] = None
    name: Optional[str] = None
    headline: Optional[str] = None
    role_guess: Optional[str] = None
    link: Optional[str] = None
    linkedin_host: Optional[str] = None
    tld_country: Optional[str] = None
    is_india: bool = False
    followers_est: Optional[int] = None
    snippet: Optional[str] = None
    location_hint: Optional[str] = None
    org_hint: Optional[str] = None
    source: Optional[str] = None
    displayed_link: Optional[str] = None
    favicon: Optional[str] = None


@dataclass
class LeadRecord:
    """Complete lead record for Google Sheets storage."""
    linkedin_url: Optional[str] = None
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    connections: Optional[int] = None
    follower: Optional[str] = None
    email: List[str] = field(default_factory=list)
    email_verification: Optional[str] = None
    mobile_number: Optional[str] = None
    headline: Optional[str] = None
    address_country_only: Optional[str] = None
    job_title: Optional[str] = None
    job_location: Optional[str] = None
    company_name: Optional[str] = None
    company_industry: Optional[str] = None
    company_website: Optional[str] = None
    company_linkedin: Optional[str] = None
    company_size: Optional[str] = None
    job_started_on: Optional[str] = None
    current_job_duration: Optional[str] = None
    address_without_country: Optional[str] = None
    followers: Optional[int] = None
    snippet: Optional[str] = None
    email_type: Optional[str] = None
    status: Optional[str] = None
    about: Optional[str] = None
    name: Optional[str] = None
    displayed_link: Optional[str] = None
    verified_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Google Sheets."""
        return {
            "LinkedinUrl": self.linkedin_url,
            "FullName": self.full_name,
            "FirstName": self.first_name,
            "LastName": self.last_name,
            "Connections": self.connections,
            "Follower": self.follower,
            "Email": self.email,
            " email verification": self.email_verification,
            "mobileNumber": self.mobile_number,
            "headline": self.headline,
            "address Country Only": self.address_country_only,
            "jobTitle": self.job_title,
            "jobLocation": self.job_location,
            "companyName": self.company_name,
            "companyIndustry": self.company_industry,
            "companyWebsite": self.company_website,
            "companyLinkedin": self.company_linkedin,
            "companySize": self.company_size,
            "jobStartedOn": self.job_started_on,
            "currentJobDuration": self.current_job_duration,
            "addressWithoutCountry": self.address_without_country,
            "followers": self.followers,
            "snippet": self.snippet,
            "emailType": self.email_type,
            "status": self.status,
            "about": self.about,
            "name": self.name,
            "displayed_link": self.displayed_link,
        }


@dataclass
class EmailVerificationResult:
    """Result from email verification API."""
    email: str
    status: str  # valid, invalid, catch_all, role_based, unknown
    verified_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    linkedin_url: Optional[str] = None
