"""
Email verification client using EmailVerify.io API.
"""
import asyncio
import random
from datetime import datetime
from typing import Dict, Any, Optional
import httpx

from ..config import LeadGenConfig
from ..models import EmailVerificationResult


class EmailVerifyClient:
    """Client for email verification API."""
    
    BASE_URL = "https://emailverify.io/api/v1"
    
    # Status mappings from API to internal
    STATUS_VALID = "valid"
    STATUS_INVALID = "invalid"
    STATUS_CATCH_ALL = "catch_all"
    STATUS_ROLE_BASED = "role_based"
    STATUS_UNKNOWN = "unknown"
    
    def __init__(self, config: LeadGenConfig):
        self.config = config
        self.api_key = config.email_verify_api_key
    
    async def _wait_random(self, min_sec: float, max_sec: float) -> None:
        """Wait for a random duration between min and max seconds."""
        duration = random.uniform(min_sec, max_sec)
        await asyncio.sleep(duration)
    
    async def verify_email(self, email: str) -> Dict[str, Any]:
        """
        Verify a single email address.
        Equivalent to N8N EmailVerify.io HTTP GET node.
        """
        url = f"{self.BASE_URL}/verify"
        params = {
            "key": self.api_key,
            "email": email
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    
    async def verify_email_with_wait(self, email: str) -> Dict[str, Any]:
        """Verify email with rate limiting wait."""
        result = await self.verify_email(email)
        await self._wait_random(
            self.config.email_verify_wait_min,
            self.config.email_verify_wait_max
        )
        return result
    
    def parse_verification_result(
        self,
        email: str,
        api_response: Dict[str, Any],
        linkedin_url: Optional[str] = None
    ) -> EmailVerificationResult:
        """Parse API response into EmailVerificationResult."""
        # Map API status to internal status
        api_status = api_response.get("status", "").lower()
        
        # Handle various status formats from different email verification APIs
        status_mapping = {
            "valid": self.STATUS_VALID,
            "deliverable": self.STATUS_VALID,
            "ok": self.STATUS_VALID,
            "invalid": self.STATUS_INVALID,
            "undeliverable": self.STATUS_INVALID,
            "bounce": self.STATUS_INVALID,
            "catch_all": self.STATUS_CATCH_ALL,
            "catchall": self.STATUS_CATCH_ALL,
            "accept_all": self.STATUS_CATCH_ALL,
            "role_based": self.STATUS_ROLE_BASED,
            "role": self.STATUS_ROLE_BASED,
            "role-based": self.STATUS_ROLE_BASED,
            "unknown": self.STATUS_UNKNOWN,
            "risky": self.STATUS_UNKNOWN,
            "maybe": self.STATUS_UNKNOWN,
        }
        
        status = status_mapping.get(api_status, self.STATUS_UNKNOWN)
        
        return EmailVerificationResult(
            email=email,
            status=status,
            verified_at=datetime.utcnow().isoformat(),
            linkedin_url=linkedin_url
        )
    
    async def verify_and_parse(
        self,
        email: str,
        linkedin_url: Optional[str] = None
    ) -> EmailVerificationResult:
        """Verify email and return parsed result."""
        api_response = await self.verify_email_with_wait(email)
        return self.parse_verification_result(email, api_response, linkedin_url)
    
    async def batch_verify(
        self,
        emails: list,
        linkedin_urls: Optional[list] = None
    ) -> list:
        """
        Verify multiple emails with rate limiting.
        """
        results = []
        linkedin_urls = linkedin_urls or [None] * len(emails)
        
        for email, linkedin_url in zip(emails, linkedin_urls):
            if not email:
                continue
            
            try:
                result = await self.verify_and_parse(email, linkedin_url)
                results.append(result)
            except Exception as e:
                # On error, mark as unknown
                results.append(EmailVerificationResult(
                    email=email,
                    status=self.STATUS_UNKNOWN,
                    linkedin_url=linkedin_url
                ))
                print(f"Error verifying {email}: {e}")
        
        return results
    
    def should_requeue(self, status: str) -> bool:
        """Check if email should be requeued for later verification."""
        return status == self.STATUS_UNKNOWN
    
    def is_valid_for_outreach(self, status: str) -> bool:
        """Check if email is valid for outreach."""
        return status in [self.STATUS_VALID, self.STATUS_CATCH_ALL]
