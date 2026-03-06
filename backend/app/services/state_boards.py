"""
State Board API adapters for license verification
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx
from datetime import datetime, date, timedelta
import asyncio
from loguru import logger


class StateBoardAdapter(ABC):
    """
    Base class for all state board integrations
    Each state gets its own adapter implementation
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.rate_limit_per_minute = 60
        self.cost_per_lookup = 0.0
    
    @abstractmethod
    async def verify_license(
        self,
        license_number: str,
        state_code: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Verify a license and return standardized response
        
        Returns:
            {
                "status": "active" | "expired" | "suspended" | "revoked",
                "license_type": "RN" | "LPN" | "CDL",
                "expiration_date": "2028-03-15",
                "discipline_record": true | false,
                "restrictions": "None" | "Supervised practice only",
                "last_verified": "2026-03-05T12:00:00Z",
                "source": "adapter_name"
            }
        """
        pass
    
    @abstractmethod
    async def search_by_name(
        self,
        first_name: str,
        last_name: str,
        state_code: str
    ) -> list:
        """
        Search for licenses by professional name
        Returns list of matching licenses
        """
        pass


class NursysAdapter(StateBoardAdapter):
    """
    Nursys - Multi-state nursing license compact (44 states)
    API: REST with OAuth 2.0
    """
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://www.nursys.com/api/v1"
        self.rate_limit_per_minute = 100
        self.cost_per_lookup = 0.10
    
    async def verify_license(
        self,
        license_number: str,
        state_code: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Verify nursing license via Nursys
        """
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                response = await client.get(
                    f"{self.base_url}/licenses/verify",
                    params={
                        "license_number": license_number,
                        "state": state_code
                    },
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 404:
                    return {
                        "status": "not_found",
                        "error": "License not found in Nursys database",
                        "source": "nursys"
                    }
                
                response.raise_for_status()
                data = response.json()
                
                # Parse Nursys response to standardized format
                return self._parse_nursys_response(data)
                
        except httpx.TimeoutException:
            logger.error(f"Nursys API timeout for {license_number}")
            return {
                "status": "error",
                "error": "API timeout",
                "source": "nursys"
            }
        except Exception as e:
            logger.error(f"Nursys API error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "source": "nursys"
            }
    
    def _parse_nursys_response(self, data: dict) -> Dict[str, Any]:
        """Parse Nursys API response to standardized format"""
        return {
            "status": data.get("status", "unknown").lower(),
            "license_type": data.get("licenseType", "RN"),
            "expiration_date": data.get("expirationDate"),
            "discipline_record": data.get("disciplinaryAction", False),
            "restrictions": data.get("restrictions"),
            "last_verified": datetime.utcnow().isoformat(),
            "source": "nursys",
            "raw_data": data
        }
    
    async def search_by_name(
        self,
        first_name: str,
        last_name: str,
        state_code: str
    ) -> list:
        """Search for nursing licenses by name"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/licenses/search",
                    params={
                        "first_name": first_name,
                        "last_name": last_name,
                        "state": state_code
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0
                )
                
                response.raise_for_status()
                return response.json().get("results", [])
                
        except Exception as e:
            logger.error(f"Nursys search error: {str(e)}")
            return []


class MockStateBoardAdapter(StateBoardAdapter):
    """
    Mock adapter for testing and development
    Returns realistic fake data
    """
    
    async def verify_license(
        self,
        license_number: str,
        state_code: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Return mock verification data
        """
        # Simulate API delay
        await asyncio.sleep(0.5)
        
        # Mock data based on license number pattern
        is_valid = len(license_number) >= 5
        
        if not is_valid:
            return {
                "status": "not_found",
                "error": "License not found",
                "source": "mock"
            }
        
        # Generate mock expiration date (2 years from now)
        expiration = date.today() + timedelta(days=730)
        
        return {
            "status": "active",
            "license_type": "RN",
            "expiration_date": expiration.isoformat(),
            "discipline_record": False,
            "restrictions": None,
            "issue_date": "2020-03-15",
            "last_verified": datetime.utcnow().isoformat(),
            "source": "mock",
            "mock_data": True
        }
    
    async def search_by_name(
        self,
        first_name: str,
        last_name: str,
        state_code: str
    ) -> list:
        """Return mock search results"""
        await asyncio.sleep(0.3)
        
        return [
            {
                "license_number": "123456",
                "first_name": first_name,
                "last_name": last_name,
                "state": state_code,
                "license_type": "RN",
                "status": "active"
            }
        ]


class StateBoardAdapterFactory:
    """
    Factory for getting the appropriate state board adapter
    """
    
    # States covered by Nursys compact
    NURSYS_STATES = [
        "AZ", "AR", "CO", "DE", "FL", "GA", "ID", "IN", "IA", "KS",
        "KY", "LA", "ME", "MD", "MS", "MO", "MT", "NE", "NV", "NH",
        "NJ", "NM", "NC", "ND", "OK", "PA", "RI", "SC", "SD", "TN",
        "TX", "UT", "VT", "VA", "WV", "WI", "WY"
    ]
    
    @classmethod
    def get_adapter(
        cls,
        state_code: str,
        license_type: str = "RN",
        api_keys: Optional[Dict[str, str]] = None
    ) -> StateBoardAdapter:
        """
        Get appropriate adapter for state and license type
        
        Args:
            state_code: Two-letter state code
            license_type: Type of license (RN, LPN, CDL, etc.)
            api_keys: Dictionary of API keys for various services
        
        Returns:
            StateBoardAdapter instance
        """
        api_keys = api_keys or {}
        
        # For nursing licenses in Nursys compact states
        if license_type in ["RN", "LPN"] and state_code in cls.NURSYS_STATES:
            nursys_key = api_keys.get("nursys")
            if nursys_key:
                return NursysAdapter(nursys_key)
        
        # TODO: Add more state-specific adapters
        # elif state_code == "CA":
        #     return CaliforniaDCAAdapter()
        # elif state_code == "TX":
        #     return TexasBONAdapter()
        
        # Default to mock adapter for development
        logger.warning(f"Using mock adapter for {state_code} - {license_type}")
        return MockStateBoardAdapter()


class MultiStateVerificationService:
    """
    Service for verifying licenses across multiple states in parallel
    """
    
    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        self.api_keys = api_keys or {}
    
    async def verify_all_states(
        self,
        license_number: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        states: Optional[list] = None,
        license_type: str = "RN"
    ) -> Dict[str, Any]:
        """
        Search for license across multiple states in parallel
        
        Args:
            license_number: License number to search for
            first_name: Professional's first name
            last_name: Professional's last name
            states: List of state codes (if None, searches all 50)
            license_type: Type of license
        
        Returns:
            Dictionary with search results
        """
        if not states:
            states = self._get_all_states()
        
        start_time = datetime.utcnow()
        
        # Create tasks for parallel execution
        tasks = []
        for state in states:
            adapter = StateBoardAdapterFactory.get_adapter(
                state,
                license_type,
                self.api_keys
            )
            
            if license_number:
                task = adapter.verify_license(license_number, state)
            elif first_name and last_name:
                task = adapter.search_by_name(first_name, last_name, state)
            else:
                continue
            
            tasks.append((state, task))
        
        # Execute all verifications in parallel
        results = []
        for state, task in tasks:
            try:
                result = await task
                results.append({
                    "state": state,
                    "status": "success" if result.get("status") != "error" else "error",
                    "data": result
                })
            except Exception as e:
                logger.error(f"Error verifying {state}: {str(e)}")
                results.append({
                    "state": state,
                    "status": "error",
                    "error": str(e)
                })
        
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Count successful finds
        found_count = sum(
            1 for r in results 
            if r.get("status") == "success" and r.get("data", {}).get("status") != "not_found"
        )
        
        return {
            "total_states_searched": len(states),
            "total_licenses_found": found_count,
            "search_duration_ms": duration_ms,
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _get_all_states(self) -> list:
        """Return all 50 US state codes"""
        return [
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
        ]
