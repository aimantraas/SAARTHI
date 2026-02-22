#!/usr/bin/env python3
"""
Main entry point for the LeadGen Backend system.
Provides CLI commands for running workflows.
"""
import asyncio
import argparse
import json
import sys
from typing import List, Optional
from pathlib import Path

from leadgen_backend import (
    LeadGenConfig,
    GoogleSheetsClient,
    MockGoogleSheetsClient,
    run_leadgen_workflow,
    run_email_verification
)


def load_config_from_file(config_path: str) -> dict:
    """Load configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)


def create_config(args: argparse.Namespace) -> LeadGenConfig:
    """Create configuration from CLI arguments."""
    config = LeadGenConfig()
    
    # Override with CLI arguments
    if getattr(args, "serp_api_key", None):
        config.serp_api_key = args.serp_api_key
    if getattr(args, "apify_token", None):
        config.apify_api_token = args.apify_token
    if getattr(args, "email_verify_key", None):
        config.email_verify_api_key = args.email_verify_key
    if getattr(args, "sheet_id", None):
        config.google_sheet_id = args.sheet_id
    if getattr(args, "credentials_path", None):
        config.google_credentials_path = args.credentials_path
    
    # Search parameters
    if getattr(args, "companies", None):
        config.companies = args.companies
    if getattr(args, "position", None):
        config.position = args.position
    if getattr(args, "country", None):
        config.country = args.country
    if getattr(args, "country_code", None):
        config.country_code = args.country_code
    
    # Batch settings
    if getattr(args, "batch_size", None):
        config.batch_size = args.batch_size
    if getattr(args, "email_batch_limit", None):
        config.email_batch_limit = args.email_batch_limit
    
    return config


def create_sheets_client(
    config: LeadGenConfig,
    mock: bool = False
):
    """Create Google Sheets client."""
    if mock:
        return MockGoogleSheetsClient(config)
    return GoogleSheetsClient(config)


async def cmd_leadgen(args: argparse.Namespace) -> int:
    """Run the lead generation workflow."""
    config = create_config(args)
    sheets_client = create_sheets_client(config, args.mock_sheets)
    
    print("="*60)
    print("LeadGen + Enrichment Workflow")
    print("="*60)
    print(f"Companies: {config.companies}")
    print(f"Position: {config.position}")
    print(f"Country: {config.country} ({config.country_code})")
    print(f"Start indexes: {config.start_indexes}")
    print("="*60)
    
    try:
        records = await run_leadgen_workflow(
            config=config,
            sheets_client=sheets_client,
            sheet_name=args.sheet_name
        )
        
        print(f"\nCompleted! Generated {len(records)} lead records")
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


async def cmd_email_verify(args: argparse.Namespace) -> int:
    """Run the email verification workflow."""
    config = create_config(args)
    sheets_client = create_sheets_client(config, args.mock_sheets)
    
    print("="*60)
    print("Email Verification Workflow")
    print("="*60)
    print(f"Sheet: {args.sheet_name}")
    print(f"Batch limit: {config.email_batch_limit}")
    print("="*60)
    
    try:
        results = await run_email_verification(
            config=config,
            sheets_client=sheets_client,
            sheet_name=args.sheet_name,
            batch_limit=args.limit
        )
        
        print(f"\nCompleted! Verified {len(results)} emails")
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


async def cmd_full_pipeline(args: argparse.Namespace) -> int:
    """Run the complete pipeline: leadgen + email verification."""
    config = create_config(args)
    sheets_client = create_sheets_client(config, args.mock_sheets)
    
    print("="*60)
    print("Full Pipeline: LeadGen + Email Verification")
    print("="*60)
    
    # Step 1: Lead Generation
    print("\n[Step 1/2] Running Lead Generation...")
    try:
        records = await run_leadgen_workflow(
            config=config,
            sheets_client=sheets_client,
            sheet_name=args.sheet_name
        )
        print(f"Generated {len(records)} lead records")
    except Exception as e:
        print(f"Error in lead generation: {e}")
        return 1
    
    # Step 2: Email Verification
    print("\n[Step 2/2] Running Email Verification...")
    try:
        results = await run_email_verification(
            config=config,
            sheets_client=sheets_client,
            sheet_name=args.sheet_name,
            batch_limit=args.limit
        )
        print(f"Verified {len(results)} emails")
    except Exception as e:
        print(f"Error in email verification: {e}")
        return 1
    
    print("\n" + "="*60)
    print("Pipeline completed successfully!")
    print("="*60)
    return 0


async def cmd_schedule_email_verify(args: argparse.Namespace) -> int:
    """Run email verification on a schedule."""
    from leadgen_backend import EmailVerificationWorkflow
    
    config = create_config(args)
    sheets_client = create_sheets_client(config, args.mock_sheets)
    
    workflow = EmailVerificationWorkflow(config, sheets_client)
    
    print("="*60)
    print("Scheduled Email Verification")
    print(f"Interval: {args.interval} seconds")
    print("="*60)
    
    try:
        await workflow.run_scheduled(
            sheet_name=args.sheet_name,
            batch_limit=args.limit,
            interval_seconds=args.interval
        )
    except KeyboardInterrupt:
        print("\nStopped by user")
        return 0
    except Exception as e:
        print(f"\nError: {e}")
        return 1


def cmd_test_config(args: argparse.Namespace) -> int:
    """Test configuration and API connections."""
    config = create_config(args)
    
    print("="*60)
    print("Configuration Test")
    print("="*60)
    
    print("\nConfiguration values:")
    print(f"  SerpAPI Key: {'*' * 8 if config.serp_api_key else 'NOT SET'}")
    print(f"  Apify Token: {'*' * 8 if config.apify_api_token else 'NOT SET'}")
    print(f"  Email Verify Key: {'*' * 8 if config.email_verify_api_key else 'NOT SET'}")
    print(f"  Google Sheet ID: {config.google_sheet_id or 'NOT SET'}")
    print(f"  Credentials Path: {config.google_credentials_path}")
    
    print("\nSearch parameters:")
    print(f"  Companies: {config.companies}")
    print(f"  Position: {config.position}")
    print(f"  Country: {config.country} ({config.country_code})")
    
    print("\nBatch settings:")
    print(f"  Start indexes: {config.start_indexes}")
    print(f"  Batch size: {config.batch_size}")
    print(f"  Email batch limit: {config.email_batch_limit}")
    
    # Test API connections
    async def test_connections():
        print("\n" + "-"*60)
        print("Testing API Connections...")
        print("-"*60)
        
        # Test SerpAPI
        if config.serp_api_key:
            try:
                from leadgen_backend.clients import SerpAPIClient
                client = SerpAPIClient(config)
                # Simple test query
                print("  SerpAPI: Configured (key present)")
            except Exception as e:
                print(f"  SerpAPI: Error - {e}")
        else:
            print("  SerpAPI: NOT CONFIGURED")
        
        # Test Apify
        if config.apify_api_token:
            try:
                from leadgen_backend.clients import ApifyLinkedInClient
                client = ApifyLinkedInClient(config)
                print("  Apify: Configured (token present)")
            except Exception as e:
                print(f"  Apify: Error - {e}")
        else:
            print("  Apify: NOT CONFIGURED")
        
        # Test Email Verify
        if config.email_verify_api_key:
            try:
                from leadgen_backend.clients import EmailVerifyClient
                client = EmailVerifyClient(config)
                print("  Email Verify: Configured (key present)")
            except Exception as e:
                print(f"  Email Verify: Error - {e}")
        else:
            print("  Email Verify: NOT CONFIGURED")
        
        # Test Google Sheets
        if config.google_sheet_id and Path(config.google_credentials_path).exists():
            try:
                sheets = GoogleSheetsClient(config)
                _ = sheets.service  # Trigger auth
                print("  Google Sheets: Connected")
            except Exception as e:
                print(f"  Google Sheets: Error - {e}")
        else:
            print("  Google Sheets: NOT CONFIGURED (missing sheet ID or credentials)")
    
    asyncio.run(test_connections())
    
    print("\n" + "="*60)
    print("Configuration test complete")
    print("="*60)
    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="LeadGen Backend - LinkedIn Lead Generation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run lead generation
  python main.py leadgen --companies "Retail" "Tech" --position "CEO"
  
  # Run email verification
  python main.py email-verify --limit 50
  
  # Run full pipeline
  python main.py pipeline
  
  # Test configuration
  python main.py test-config
"""
    )
    
    # Global options
    parser.add_argument(
        "--config", "-c",
        help="Path to configuration JSON file"
    )
    parser.add_argument(
        "--serp-api-key",
        help="SerpAPI key (or set SERP_API_KEY env var)"
    )
    parser.add_argument(
        "--apify-token",
        help="Apify API token (or set APIFY_API_TOKEN env var)"
    )
    parser.add_argument(
        "--email-verify-key",
        help="Email verification API key (or set EMAIL_VERIFY_API_KEY env var)"
    )
    parser.add_argument(
        "--sheet-id",
        help="Google Sheet ID (or set GOOGLE_SHEET_ID env var)"
    )
    parser.add_argument(
        "--credentials-path",
        help="Path to Google credentials JSON file"
    )
    parser.add_argument(
        "--mock-sheets",
        action="store_true",
        help="Use mock sheets client (for testing)"
    )
    parser.add_argument(
        "--sheet-name",
        default="Sheet1",
        help="Google Sheet name/tab (default: Sheet1)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # LeadGen command
    leadgen_parser = subparsers.add_parser(
        "leadgen",
        help="Run lead generation workflow"
    )
    leadgen_parser.add_argument(
        "--companies",
        nargs="+",
        help="List of companies to search"
    )
    leadgen_parser.add_argument(
        "--position",
        help="Position/title to search for"
    )
    leadgen_parser.add_argument(
        "--country",
        help="Country for search"
    )
    leadgen_parser.add_argument(
        "--country-code",
        help="Country code (e.g., IN, US)"
    )
    leadgen_parser.add_argument(
        "--batch-size",
        type=int,
        help="Batch size for Apify scraping"
    )
    
    # Email verify command
    email_parser = subparsers.add_parser(
        "email-verify",
        help="Run email verification workflow"
    )
    email_parser.add_argument(
        "--limit",
        type=int,
        help="Maximum emails to verify in this run"
    )
    
    # Full pipeline command
    pipeline_parser = subparsers.add_parser(
        "pipeline",
        help="Run full pipeline (leadgen + email verification)"
    )
    pipeline_parser.add_argument(
        "--companies",
        nargs="+",
        help="List of companies to search"
    )
    pipeline_parser.add_argument(
        "--position",
        help="Position/title to search for"
    )
    pipeline_parser.add_argument(
        "--limit",
        type=int,
        help="Maximum emails to verify"
    )
    
    # Schedule command
    schedule_parser = subparsers.add_parser(
        "schedule",
        help="Run email verification on schedule"
    )
    schedule_parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Interval in seconds between runs (default: 3600)"
    )
    schedule_parser.add_argument(
        "--limit",
        type=int,
        help="Maximum emails to verify per run"
    )
    
    # Test config command
    test_parser = subparsers.add_parser(
        "test-config",
        help="Test configuration and API connections"
    )
    
    args = parser.parse_args()
    
    # Load config file if specified
    if hasattr(args, 'config') and args.config:
        file_config = load_config_from_file(args.config)
        # Override config values from file
        for key, value in file_config.items():
            if not getattr(args, key, None):
                setattr(args, key, value)
    
    # Run command
    if args.command == "leadgen":
        return asyncio.run(cmd_leadgen(args))
    elif args.command == "email-verify":
        return asyncio.run(cmd_email_verify(args))
    elif args.command == "pipeline":
        return asyncio.run(cmd_full_pipeline(args))
    elif args.command == "schedule":
        return asyncio.run(cmd_schedule_email_verify(args))
    elif args.command == "test-config":
        return cmd_test_config(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
