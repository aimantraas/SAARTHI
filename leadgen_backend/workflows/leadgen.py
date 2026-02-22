"""
Workflow 1: LeadGen + Enrichment
Equivalent to N8N LeadGen workflow.
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..config import LeadGenConfig
from ..models import LeadRecord, LinkedInProfile, SerpAPIResult, OrganicResult
from ..clients import SerpAPIClient, SerpAPIRequestError, ApifyLinkedInClient
from ..sheets import GoogleSheetsClient
from ..data_cleaning import (
    clean_serp_api_data,
    clean_serp_google_data,
    filter_linkedin_urls
)


class LeadGenWorkflow:
    """
    Main workflow for lead generation and enrichment.
    
    Flow:
    1. Initialize with companies, position, country
    2. SerpAPI Google search for LinkedIn profiles
    3. Filter and dedupe LinkedIn URLs
    4. Apify LinkedIn Profile Scraper
    5. SerpAPI AI Mode for contact details
    6. Data cleaning and merging
    7. Save to Google Sheets
    """
    
    def __init__(
        self,
        config: LeadGenConfig,
        sheets_client: Optional[GoogleSheetsClient] = None
    ):
        self.config = config
        self.serp_client = SerpAPIClient(config)
        self.apify_client = ApifyLinkedInClient(config)
        self.sheets_client = sheets_client
    
    async def run(
        self,
        companies: Optional[List[str]] = None,
        position: Optional[str] = None,
        country: Optional[str] = None,
        country_code: Optional[str] = None,
        sheet_name: str = "Sheet1"
    ) -> List[LeadRecord]:
        """
        Run the complete lead generation workflow.
        """
        # Use config defaults or override with parameters
        companies = companies or self.config.companies
        position = position or self.config.position
        country = country or self.config.country
        country_code = country_code or self.config.country_code
        
        all_records = []
        
        for company in companies:
            print(f"\n{'='*50}")
            print(f"Processing company: {company}")
            print(f"Position: {position}")
            print(f"Country: {country}")
            print(f"{'='*50}\n")
            
            # Step 1: Search LinkedIn profiles via SerpAPI Google
            print("Step 1: Searching LinkedIn profiles...")
            profile_results = await self._search_linkedin_profiles(
                company, position, country, country_code
            )
            
            if not profile_results:
                print(f"No profiles found for {company}")
                continue
            
            print(f"Found {len(profile_results)} organic results")
            
            # Step 2: Extract and filter LinkedIn URLs
            print("\nStep 2: Filtering LinkedIn URLs...")
            linkedin_urls = self._extract_linkedin_urls(profile_results)
            print(f"Filtered to {len(linkedin_urls)} unique profile URLs")
            
            if not linkedin_urls:
                continue
            
            # Step 3: Scrape LinkedIn profiles via Apify
            print("\nStep 3: Scraping LinkedIn profiles via Apify...")
            linkedin_profiles = await self._scrape_linkedin_profiles(linkedin_urls)
            print(f"Scraped {len(linkedin_profiles)} profiles")
            
            # Step 4: Enrich with contact details via SerpAPI AI Mode
            print("\nStep 4: Enriching with contact details...")
            enriched_records = await self._enrich_profiles(
                linkedin_profiles, profile_results
            )
            print(f"Enriched {len(enriched_records)} records")
            
            # Step 5: Save to Google Sheets
            if self.sheets_client:
                print("\nStep 5: Saving to Google Sheets...")
                for record in enriched_records:
                    try:
                        self.sheets_client.save_lead_record(sheet_name, record)
                    except Exception as e:
                        print(f"Error saving record: {e}")
                print(f"Saved {len(enriched_records)} records")
            
            all_records.extend(enriched_records)
        
        return all_records
    
    async def _search_linkedin_profiles(
        self,
        company: str,
        position: str,
        country: str,
        country_code: str
    ) -> List[OrganicResult]:
        """Search for LinkedIn profiles using SerpAPI Google search."""
        all_results = []
        
        for start_index in self.config.start_indexes:
            try:
                raw_data = await self.serp_client.search_linkedin_profiles_with_wait(
                    company=company,
                    position=position,
                    country=country,
                    country_code=country_code,
                    start_index=start_index
                )
                
                results = clean_serp_google_data(raw_data)
                all_results.extend(results)
                
                print(f"  Page start={start_index}: {len(results)} results")
                
            except SerpAPIRequestError as e:
                # Fail fast on authentication/authorization problems.
                print(f"  Error at start={start_index}: {e}")
                if e.status_code in (401, 403):
                    raise
                continue
            except Exception as e:
                print(f"  Error at start={start_index}: {e}")
                continue
        
        # Deduplicate by link
        seen_links = set()
        unique_results = []
        for result in all_results:
            if result.link and result.link not in seen_links:
                seen_links.add(result.link)
                unique_results.append(result)
        
        return unique_results
    
    def _extract_linkedin_urls(self, results: List[OrganicResult]) -> List[str]:
        """Extract and filter LinkedIn profile URLs."""
        urls = [r.link for r in results if r.link]
        return filter_linkedin_urls(urls)
    
    async def _scrape_linkedin_profiles(
        self,
        linkedin_urls: List[str]
    ) -> List[LinkedInProfile]:
        """Scrape LinkedIn profiles using Apify."""
        return await self.apify_client.scrape_with_rate_limit(
            linkedin_urls,
            batch_size=self.config.batch_size
        )
    
    async def _enrich_profiles(
        self,
        profiles: List[LinkedInProfile],
        organic_results: List[OrganicResult]
    ) -> List[LeadRecord]:
        """Enrich profiles with contact details from SerpAPI AI Mode."""
        records = []
        
        # Create lookup from organic results
        organic_by_url = {r.link: r for r in organic_results if r.link}
        
        for profile in profiles:
            # Get organic result data
            organic = organic_by_url.get(profile.linkedin_url)
            
            # Search for contact details
            contact_data = None
            if profile.full_name and profile.company_name:
                try:
                    raw_contact = await self.serp_client.search_contact_details_with_wait(
                        full_name=profile.full_name,
                        company_name=profile.company_name
                    )
                    contact_data = clean_serp_api_data(raw_contact)
                except Exception as e:
                    print(f"  Error getting contact details for {profile.full_name}: {e}")
            
            # Merge all data into LeadRecord
            record = self._merge_to_record(profile, organic, contact_data)
            records.append(record)
        
        return records
    
    def _merge_to_record(
        self,
        profile: LinkedInProfile,
        organic: Optional[OrganicResult],
        contact: Optional[SerpAPIResult]
    ) -> LeadRecord:
        """Merge data from multiple sources into a LeadRecord."""
        emails = []
        phones = []
        
        # Add emails from contact data
        if contact and contact.emails:
            emails.extend(contact.emails)
        
        # Add email from profile
        if profile.email:
            emails.append(profile.email)
        
        # Add phones from contact data
        if contact and contact.phones:
            phones.extend(contact.phones)
        
        # Add mobile from profile
        if profile.mobile_number:
            phones.append(profile.mobile_number)
        
        # Dedupe
        emails = list(dict.fromkeys(emails))
        phones = list(dict.fromkeys(phones))
        
        return LeadRecord(
            linkedin_url=profile.linkedin_url,
            full_name=profile.full_name,
            first_name=profile.first_name,
            last_name=profile.last_name,
            connections=profile.connections,
            follower=organic.displayed_link if organic else None,
            email=emails,
            mobile_number=phones[0] if phones else None,
            headline=profile.headline or (contact.headline if contact else None),
            address_country_only=profile.address_country_only,
            job_title=profile.job_title,
            job_location=profile.job_location,
            company_name=profile.company_name,
            company_industry=profile.company_industry,
            company_website=profile.company_website,
            company_linkedin=profile.company_linkedin,
            company_size=profile.company_size,
            job_started_on=profile.job_started_on,
            current_job_duration=profile.current_job_duration,
            address_without_country=profile.address_without_country,
            followers=profile.followers,
            snippet=organic.snippet if organic else None,
            about=profile.about or (contact.about if contact else None),
            name=contact.name if contact else None,
            displayed_link=organic.displayed_link if organic else None,
            status="PROCESS" if emails else None
        )
    
    async def run_single_page(
        self,
        company: str,
        position: str,
        country: str,
        country_code: str,
        start_index: int = 0,
        sheet_name: str = "Sheet1"
    ) -> List[LeadRecord]:
        """
        Run workflow for a single page of results.
        Useful for incremental processing.
        """
        # Search
        raw_data = await self.serp_client.search_linkedin_profiles_with_wait(
            company, position, country, country_code, start_index
        )
        results = clean_serp_google_data(raw_data)
        
        if not results:
            return []
        
        # Filter URLs
        urls = self._extract_linkedin_urls(results)
        
        if not urls:
            return []
        
        # Scrape
        profiles = await self._scrape_linkedin_profiles(urls)
        
        # Enrich
        records = await self._enrich_profiles(profiles, results)
        
        # Save
        if self.sheets_client:
            for record in records:
                self.sheets_client.save_lead_record(sheet_name, record)
        
        return records


async def run_leadgen_workflow(
    config: LeadGenConfig,
    sheets_client: Optional[GoogleSheetsClient] = None,
    companies: Optional[List[str]] = None,
    position: Optional[str] = None,
    country: Optional[str] = None,
    country_code: Optional[str] = None,
    sheet_name: str = "Sheet1"
) -> List[LeadRecord]:
    """
    Convenience function to run the lead generation workflow.
    """
    workflow = LeadGenWorkflow(config, sheets_client)
    return await workflow.run(
        companies=companies,
        position=position,
        country=country,
        country_code=country_code,
        sheet_name=sheet_name
    )
