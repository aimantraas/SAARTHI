"""
Workflow 2: Email Verification
Equivalent to N8N ScheduleEmailOutR workflow.
"""
import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..config import LeadGenConfig
from ..models import EmailVerificationResult
from ..clients import EmailVerifyClient
from ..sheets import GoogleSheetsClient
from ..data_cleaning import parse_email_field


class EmailVerificationWorkflow:
    """
    Workflow for verifying emails from Google Sheets.
    
    Flow:
    1. Load rows with email verification = "PROCESS"
    2. Split out email arrays into individual items
    3. Parse primary and secondary emails
    4. Skip already verified emails
    5. Verify via EmailVerify.io API
    6. Route based on status (valid, invalid, catch_all, role_based, unknown)
    7. Update Google Sheets with verification result
    """
    
    def __init__(
        self,
        config: LeadGenConfig,
        sheets_client: GoogleSheetsClient
    ):
        self.config = config
        self.email_client = EmailVerifyClient(config)
        self.sheets_client = sheets_client
    
    async def run(
        self,
        sheet_name: str = "Sheet1",
        batch_limit: Optional[int] = None
    ) -> List[EmailVerificationResult]:
        """
        Run the email verification workflow.
        """
        batch_limit = batch_limit or self.config.email_batch_limit
        
        print(f"\n{'='*50}")
        print("Starting Email Verification Workflow")
        print(f"{'='*50}\n")
        
        # Step 1: Load rows needing verification
        print("Step 1: Loading rows with status 'PROCESS'...")
        rows = self.sheets_client.get_unverified_emails(
            sheet_name,
            status_filter=self.config.email_status_process
        )
        
        if not rows:
            print("No rows found needing email verification")
            return []
        
        print(f"Found {len(rows)} rows to process")
        
        # Step 2: Get already verified emails to skip
        print("\nStep 2: Getting already verified emails...")
        verified_emails = self._get_verified_emails(sheet_name)
        print(f"Found {len(verified_emails)} already verified emails")
        
        # Step 3: Parse and flatten emails
        print("\nStep 3: Parsing and flattening email arrays...")
        email_items = self._parse_email_rows(rows)
        print(f"Parsed {len(email_items)} email items")
        
        # Step 4: Filter out already verified
        print("\nStep 4: Filtering out already verified emails...")
        to_verify = [
            item for item in email_items
            if item['email'] and item['email'].lower() not in verified_emails
        ]
        print(f"{len(to_verify)} emails need verification")
        
        # Apply batch limit
        if batch_limit and len(to_verify) > batch_limit:
            to_verify = to_verify[:batch_limit]
            print(f"Limited to {batch_limit} emails for this run")
        
        if not to_verify:
            print("No emails to verify")
            return []
        
        # Step 5: Verify emails
        print("\nStep 5: Verifying emails...")
        results = await self._verify_emails(to_verify)
        
        # Step 6: Update sheets with results
        print("\nStep 6: Updating Google Sheets...")
        for result in results:
            try:
                self._update_sheet_with_result(sheet_name, result)
            except Exception as e:
                print(f"Error updating sheet for {result.email}: {e}")
        
        # Summary
        self._print_summary(results)
        
        return results
    
    def _get_verified_emails(self, sheet_name: str) -> set:
        """Get set of already verified emails."""
        all_data = self.sheets_client.get_sheet_data(sheet_name)
        
        verified = set()
        for row in all_data:
            status = row.get(" email verification", "")
            if status and status != self.config.email_status_process:
                email = row.get("Email", "")
                if email:
                    # Handle array format
                    primary, _ = parse_email_field(email)
                    if primary:
                        verified.add(primary.lower())
        
        return verified
    
    def _parse_email_rows(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse email rows and flatten arrays.
        Equivalent to N8N SplitOut + Code node.
        """
        items = []
        
        for row in rows:
            linkedin_url = row.get("LinkedinUrl")
            email_field = row.get("Email")
            
            primary, secondary = parse_email_field(email_field)
            
            # Add primary email
            if primary:
                items.append({
                    "email": primary,
                    "email2": secondary,
                    "linkedinUrl": linkedin_url,
                    "is_primary": True
                })
            
            # Add secondary email if exists
            if secondary:
                items.append({
                    "email": secondary,
                    "email2": None,
                    "linkedinUrl": linkedin_url,
                    "is_primary": False
                })
        
        return items
    
    async def _verify_emails(
        self,
        email_items: List[Dict[str, Any]]
    ) -> List[EmailVerificationResult]:
        """Verify emails with rate limiting."""
        results = []
        
        for i, item in enumerate(email_items):
            email = item['email']
            linkedin_url = item['linkedinUrl']
            
            print(f"  [{i+1}/{len(email_items)}] Verifying: {email}")
            
            try:
                result = await self.email_client.verify_and_parse(
                    email,
                    linkedin_url
                )
                results.append(result)
                print(f"    Status: {result.status}")
                
            except Exception as e:
                print(f"    Error: {e}")
                # Mark as unknown on error
                results.append(EmailVerificationResult(
                    email=email,
                    status=self.config.email_status_unknown,
                    linkedin_url=linkedin_url
                ))
        
        return results
    
    def _update_sheet_with_result(
        self,
        sheet_name: str,
        result: EmailVerificationResult
    ) -> None:
        """Update Google Sheets with verification result."""
        # Determine the update based on status
        update_data = {
            "LinkedinUrl": result.linkedin_url,
            "Email": result.email,
            " email verification": result.status,
            "status": result.status,
            "verified_at": result.verified_at
        }
        
        # Handle requeue for unknown status
        if result.status == self.config.email_status_unknown:
            # Keep as PROCESS for requeue
            update_data[" email verification"] = self.config.email_status_process
            update_data["status"] = self.config.email_status_unknown
        
        self.sheets_client.append_or_update_row(
            sheet_name,
            update_data,
            matching_column="LinkedinUrl"
        )
    
    def _print_summary(self, results: List[EmailVerificationResult]) -> None:
        """Print summary of verification results."""
        print(f"\n{'='*50}")
        print("Email Verification Summary")
        print(f"{'='*50}")
        
        status_counts = {}
        for result in results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1
        
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
        
        print(f"  Total: {len(results)}")
        print(f"{'='*50}\n")
    
    async def run_scheduled(
        self,
        sheet_name: str = "Sheet1",
        batch_limit: Optional[int] = None,
        interval_seconds: int = 3600
    ) -> None:
        """
        Run verification on a schedule.
        Equivalent to N8N ScheduleTrigger.
        """
        while True:
            try:
                await self.run(sheet_name, batch_limit)
            except Exception as e:
                print(f"Error in scheduled run: {e}")
            
            print(f"\nNext run in {interval_seconds} seconds...")
            await asyncio.sleep(interval_seconds)


async def run_email_verification(
    config: LeadGenConfig,
    sheets_client: GoogleSheetsClient,
    sheet_name: str = "Sheet1",
    batch_limit: Optional[int] = None
) -> List[EmailVerificationResult]:
    """
    Convenience function to run email verification workflow.
    """
    workflow = EmailVerificationWorkflow(config, sheets_client)
    return await workflow.run(sheet_name, batch_limit)