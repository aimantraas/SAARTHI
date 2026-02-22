"""
SerpAPI client for Google search and AI mode queries.
"""
import asyncio
import random
from typing import List, Dict, Any, Optional
import httpx

from ..config import LeadGenConfig
from ..models import OrganicResult
from ..data_cleaning import clean_serp_api_data, clean_serp_google_data


class SerpAPIRequestError(RuntimeError):
    def __init__(self, status_code: int, message: str):
        super().__init__(f"SerpAPI request failed ({status_code}): {message}")
        self.status_code = status_code
        self.message = message


class SerpAPIClient:
    """Client for SerpAPI interactions."""
    
    BASE_URL = "https://serpapi.com/search.json"
    
    def __init__(self, config: LeadGenConfig):
        self.config = config
        self.api_key = config.serp_api_key

    def _ensure_api_key(self) -> None:
        if not self.api_key:
            raise RuntimeError(
                "SERP_API_KEY is missing. Set it in `.env` or as an environment variable."
            )

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        try:
            data = response.json()
        except Exception:
            return response.text.strip()[:300] or "Unknown error"

        if isinstance(data, dict):
            for key in ("error", "message"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            return str(data)[:300]

        return str(data)[:300]

    async def _get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_api_key()

        request_params = dict(params)
        request_params["api_key"] = self.api_key

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(self.BASE_URL, params=request_params)

        if response.status_code >= 400:
            message = self._extract_error_message(response)
            raise SerpAPIRequestError(response.status_code, message)

        data = response.json()
        if isinstance(data, dict) and isinstance(data.get("error"), str) and data["error"].strip():
            raise RuntimeError(f"SerpAPI error: {data['error'].strip()}")

        return data
    
    async def _wait_random(self, min_sec: float, max_sec: float) -> None:
        """Wait for a random duration between min and max seconds."""
        duration = random.uniform(min_sec, max_sec)
        await asyncio.sleep(duration)
    
    async def search_linkedin_profiles(
        self,
        company: str,
        position: str,
        country: str,
        country_code: str,
        start_index: int = 0,
        num_results: int = 10
    ) -> Dict[str, Any]:
        """
        Search for LinkedIn profiles using Google search engine.
        Equivalent to N8N Agent1 node.
        """
        query = f"site:linkedin.com/in {company} {position}"
        
        params = {
            "engine": "google",
            "q": query,
            "location": country,
            "gl": country_code,
            "hl": "en",
            "num": num_results,
            "start": start_index,
            "safe": "active",
        }

        return await self._get(params)
    
    async def search_contact_details(
        self,
        full_name: str,
        company_name: str
    ) -> Dict[str, Any]:
        """
        Search for contact details using Google AI mode.
        Equivalent to N8N Agent3 node.
        """
        query = f"Contact Details {full_name}, {company_name}"
        
        params = {
            "engine": "google_ai_mode",
            "q": query,
        }

        return await self._get(params)
    
    async def search_linkedin_profiles_with_wait(
        self,
        company: str,
        position: str,
        country: str,
        country_code: str,
        start_index: int = 0,
        num_results: int = 10
    ) -> Dict[str, Any]:
        """Search with rate limiting wait."""
        result = await self.search_linkedin_profiles(
            company, position, country, country_code, start_index, num_results
        )
        await self._wait_random(self.config.serp_api_wait_min, self.config.serp_api_wait_max)
        return result
    
    async def search_contact_details_with_wait(
        self,
        full_name: str,
        company_name: str
    ) -> Dict[str, Any]:
        """Search contact details with rate limiting wait."""
        result = await self.search_contact_details(full_name, company_name)
        await self._wait_random(self.config.serp_api_wait_min, self.config.serp_api_wait_max)
        return result
    
    def parse_google_results(self, data: Dict[str, Any]) -> List[OrganicResult]:
        """Parse Google search results into structured data."""
        return clean_serp_google_data(data)
    
    def parse_ai_mode_results(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AI mode results into structured contact data."""
        return clean_serp_api_data(data)
    
    async def batch_search_profiles(
        self,
        company: str,
        position: str,
        country: str,
        country_code: str,
        start_indexes: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Batch search for LinkedIn profiles across multiple pages.
        Equivalent to N8N Loop Over Items with startIndexes.
        """
        results = []
        
        for start_index in start_indexes:
            try:
                result = await self.search_linkedin_profiles_with_wait(
                    company, position, country, country_code, start_index
                )
                results.append(result)
            except Exception as e:
                print(f"Error searching with start_index {start_index}: {e}")
                continue
        
        return results
