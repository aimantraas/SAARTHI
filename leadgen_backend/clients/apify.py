"""
Apify client for LinkedIn profile scraping.
"""
import asyncio
import random
from typing import List, Dict, Any, Optional
import httpx

from ..config import LeadGenConfig
from ..models import LinkedInProfile
from ..data_cleaning import filter_linkedin_urls


class ApifyLinkedInClient:
    """Client for Apify LinkedIn Profile Scraper."""
    
    ACTOR_ID = "dev_fusion~linkedin-profile-scraper"
    BASE_URL = "https://api.apify.com/v2"
    
    def __init__(self, config: LeadGenConfig):
        self.config = config
        self.api_token = config.apify_api_token
    
    def _get_run_url(self) -> str:
        """Get URL for running the actor synchronously."""
        return f"{self.BASE_URL}/acts/{self.ACTOR_ID}/run-sync-get-dataset-items"
    
    def _get_run_async_url(self) -> str:
        """Get URL for running the actor asynchronously."""
        return f"{self.BASE_URL}/acts/{self.ACTOR_ID}/runs"
    
    def _get_dataset_url(self, dataset_id: str) -> str:
        """Get URL for fetching dataset items."""
        return f"{self.BASE_URL}/datasets/{dataset_id}/items"
    
    def _get_run_status_url(self, run_id: str) -> str:
        """Get URL for checking run status."""
        return f"{self.BASE_URL}/actor-runs/{run_id}"
    
    async def scrape_profiles_sync(
        self,
        profile_urls: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Scrape LinkedIn profiles synchronously (waits for completion).
        Equivalent to N8N Agent 2 node.
        """
        url = self._get_run_url()
        params = {"token": self.api_token}
        payload = {"profileUrls": profile_urls}
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, params=params, json=payload)
            response.raise_for_status()
            return response.json()
    
    async def scrape_profiles_async(
        self,
        profile_urls: List[str]
    ) -> str:
        """
        Start asynchronous scraping and return run ID.
        """
        url = self._get_run_async_url()
        params = {"token": self.api_token}
        payload = {"profileUrls": profile_urls}
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, params=params, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["id"]
    
    async def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """Get status of an async run."""
        url = self._get_run_status_url(run_id)
        params = {"token": self.api_token}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    
    async def get_dataset_items(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Get items from a dataset."""
        url = self._get_dataset_url(dataset_id)
        params = {"token": self.api_token}
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    
    async def scrape_profiles_with_poll(
        self,
        profile_urls: List[str],
        poll_interval: float = 5.0,
        max_wait: float = 300.0
    ) -> List[Dict[str, Any]]:
        """
        Scrape profiles with polling until completion.
        Equivalent to N8N ApifyWait pattern.
        """
        # Start async run
        run_id = await self.scrape_profiles_async(profile_urls)
        
        # Poll until done
        elapsed = 0.0
        while elapsed < max_wait:
            status = await self.get_run_status(run_id)
            state = status.get("status")
            
            if state == "SUCCEEDED":
                dataset_id = status.get("defaultDatasetId")
                if dataset_id:
                    return await self.get_dataset_items(dataset_id)
                return []
            elif state in ["FAILED", "ABORTED", "TIMED-OUT"]:
                raise Exception(f"Apify run {run_id} failed with status: {state}")
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        raise TimeoutError(f"Apify run {run_id} did not complete within {max_wait} seconds")
    
    def parse_profile_data(self, data: Dict[str, Any]) -> LinkedInProfile:
        """Parse raw Apify response into LinkedInProfile model."""
        return LinkedInProfile(
            linkedin_url=data.get("linkedinUrl"),
            full_name=data.get("fullName"),
            first_name=data.get("firstName"),
            last_name=data.get("lastName"),
            headline=data.get("headline"),
            connections=data.get("connections"),
            followers=data.get("followers"),
            email=data.get("email"),
            mobile_number=data.get("mobileNumber"),
            job_title=data.get("jobTitle"),
            job_location=data.get("jobLocation"),
            company_name=data.get("companyName"),
            company_industry=data.get("companyIndustry"),
            company_website=data.get("companyWebsite"),
            company_linkedin=data.get("companyLinkedin"),
            company_size=data.get("companySize"),
            job_started_on=data.get("jobStartedOn"),
            current_job_duration=data.get("currentJobDuration"),
            address_country_only=data.get("addressCountryOnly"),
            address_without_country=data.get("addressWithoutCountry"),
            about=data.get("about")
        )
    
    def parse_profiles(self, data_list: List[Dict[str, Any]]) -> List[LinkedInProfile]:
        """Parse multiple profile responses."""
        return [self.parse_profile_data(data) for data in data_list]
    
    async def scrape_and_parse_profiles(
        self,
        profile_urls: List[str]
    ) -> List[LinkedInProfile]:
        """Scrape and parse LinkedIn profiles."""
        # Filter URLs to only include profile URLs
        filtered_urls = filter_linkedin_urls(profile_urls)
        
        if not filtered_urls:
            return []
        
        raw_data = await self.scrape_profiles_sync(filtered_urls)
        return self.parse_profiles(raw_data if isinstance(raw_data, list) else [raw_data])
    
    async def scrape_with_rate_limit(
        self,
        profile_urls: List[str],
        batch_size: int = 10
    ) -> List[LinkedInProfile]:
        """
        Scrape profiles in batches with rate limiting.
        """
        all_profiles = []
        
        for i in range(0, len(profile_urls), batch_size):
            batch = profile_urls[i:i + batch_size]
            profiles = await self.scrape_and_parse_profiles(batch)
            all_profiles.extend(profiles)
            
            # Wait between batches
            if i + batch_size < len(profile_urls):
                await asyncio.sleep(random.uniform(2, 5))
        
        return all_profiles
