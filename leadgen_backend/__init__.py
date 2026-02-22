"""
LeadGen Backend - Python implementation of N8N LinkedIn LeadGen workflows.

This package provides a Python backend for:
- Workflow 1: LeadGen + Enrichment (SerpAPI, LinkedIn scraping, data cleaning)
- Workflow 2: Email Verification

Usage:
    from leadgen_backend import LeadGenConfig, run_leadgen_workflow, run_email_verification
    from leadgen_backend import GoogleSheetsClient
    
    config = LeadGenConfig()
    sheets = GoogleSheetsClient(config)
    
    # Run lead generation
    records = await run_leadgen_workflow(config, sheets)
    
    # Run email verification
    results = await run_email_verification(config, sheets)
"""

from .config import LeadGenConfig, SheetColumns, config, sheet_columns
from .models import (
    LeadRecord,
    LinkedInProfile,
    SerpAPIResult,
    OrganicResult,
    EmailVerificationResult,
    ContactInfo,
    MetaInfo,
    SearchParameters,
    SearchMetadata
)
from .clients import SerpAPIClient, ApifyLinkedInClient, EmailVerifyClient
from .sheets import GoogleSheetsClient
from .workflows import (
    LeadGenWorkflow,
    run_leadgen_workflow,
    EmailVerificationWorkflow,
    run_email_verification
)
from .data_cleaning import (
    clean_serp_api_data,
    clean_serp_google_data,
    extract_emails,
    extract_phones,
    filter_linkedin_urls,
    parse_email_field
)

__version__ = "1.0.0"
__author__ = "LeadGen Team"

__all__ = [
    # Config
    "LeadGenConfig",
    "SheetColumns",
    "config",
    "sheet_columns",
    
    # Models
    "LeadRecord",
    "LinkedInProfile",
    "SerpAPIResult",
    "OrganicResult",
    "EmailVerificationResult",
    "ContactInfo",
    "MetaInfo",
    "SearchParameters",
    "SearchMetadata",
    
    # Clients
    "SerpAPIClient",
    "ApifyLinkedInClient",
    "EmailVerifyClient",
    
    # Sheets
    "GoogleSheetsClient",
    
    # Workflows
    "LeadGenWorkflow",
    "run_leadgen_workflow",
    "EmailVerificationWorkflow",
    "run_email_verification",
    
    # Data Cleaning
    "clean_serp_api_data",
    "clean_serp_google_data",
    "extract_emails",
    "extract_phones",
    "filter_linkedin_urls",
    "parse_email_field",
]
