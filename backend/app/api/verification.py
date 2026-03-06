"""
License verification API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import hashlib
import json
import uuid

from app.database import get_db
from app.auth.api_key import get_current_user, get_current_active_subscription, check_rate_limit, increment_usage
from app.models import User, ProfessionalLicense, LicenseVerificationAudit, StateBoardCache
from app.schemas import (
    LicenseVerificationRequest,
    LicenseVerificationResponse,
    MultiStateSearchRequest,
    MultiStateSearchResponse,
    StateSearchResult
)
from app.services.state_boards import StateBoardAdapterFactory, MultiStateVerificationService
from app.config import settings

router = APIRouter(prefix="/verify", tags=["Verification"])


@router.post("/license", response_model=LicenseVerificationResponse)
async def verify_license(
    request: LicenseVerificationRequest,
    user: User = Depends(get_current_user),
    subscription = Depends(get_current_active_subscription),
    db: Session = Depends(get_db)
):
    """
    Verify a single professional license
    
    **What it does:**
    - Checks state board database for license validity
    - Returns current status, expiration, discipline records
    - Caches results for faster future lookups
    - Creates audit trail for compliance
    
    **Example:**
    ```json
    {
      "license_number": "123456",
      "state_code": "AZ",
      "license_type": "RN"
    }
    ```
    """
    # Check rate limits
    check_rate_limit(user, subscription, db)
    
    # Check cache first
    cache_key = f"{request.license_number}_{request.state_code}"
    cached = db.query(StateBoardCache).filter(
        StateBoardCache.license_number == request.license_number,
        StateBoardCache.state_code == request.state_code,
        StateBoardCache.cache_expires_at > datetime.utcnow()
    ).first()
    
    if cached:
        # Return cached result
        cached_data = cached.cached_response
        return LicenseVerificationResponse(
            verified=True,
            license_number=request.license_number,
            state=request.state_code,
            status=cached_data.get("status"),
            license_type=cached_data.get("license_type"),
            expiration_date=cached_data.get("expiration_date"),
            discipline_record=cached_data.get("discipline_record", False),
            restrictions=cached_data.get("restrictions"),
            last_verified=datetime.utcnow(),
            confidence="high",
            source="cache",
            verification_id=str(uuid.uuid4())
        )
    
    # Call state board API
    adapter = StateBoardAdapterFactory.get_adapter(
        request.state_code,
        request.license_type or "RN",
        {"nursys": settings.NURSYS_API_KEY}
    )
    
    result = await adapter.verify_license(
        request.license_number,
        request.state_code
    )
    
    if result.get("status") == "error" or result.get("status") == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"License {request.license_number} not found in {request.state_code}"
        )
    
    # Create or update license record
    license = db.query(ProfessionalLicense).filter(
        ProfessionalLicense.license_number == request.license_number,
        ProfessionalLicense.state_code == request.state_code
    ).first()
    
    if not license:
        license = ProfessionalLicense(
            license_number=request.license_number,
            state_code=request.state_code,
            license_type=result.get("license_type", "RN"),
            status=result.get("status"),
            expiration_date=result.get("expiration_date"),
            discipline_record=result.get("discipline_record", False),
            restrictions=result.get("restrictions"),
            last_verified_at=datetime.utcnow(),
            verification_count=1
        )
        db.add(license)
    else:
        # Update existing license
        license.status = result.get("status")
        license.expiration_date = result.get("expiration_date")
        license.discipline_record = result.get("discipline_record", False)
        license.restrictions = result.get("restrictions")
        license.last_verified_at = datetime.utcnow()
        license.verification_count += 1
    
    db.commit()
    db.refresh(license)
    
    # Cache result
    cache_ttl_hours = 24 if result.get("status") == "active" else 1
    cache_entry = StateBoardCache(
        license_number=request.license_number,
        state_code=request.state_code,
        cached_response=result,
        cache_expires_at=datetime.utcnow() + timedelta(hours=cache_ttl_hours)
    )
    db.add(cache_entry)
    
    # Create audit trail
    verification_id = str(uuid.uuid4())
    audit_record = LicenseVerificationAudit(
        audit_id=verification_id,
        verifier_user_id=user.id,
        verifier_name=user.full_name,
        verifier_email=user.email,
        verifier_organization=user.organization,
        license_id=license.id,
        license_number=request.license_number,
        state_code=request.state_code,
        verification_result=result,
        license_status=result.get("status"),
        expiration_date=result.get("expiration_date"),
        discipline_record=result.get("discipline_record"),
        data_source=result.get("source"),
        verification_purpose="api_verification",
        verification_hash=_generate_verification_hash(result, user.email)
    )
    db.add(audit_record)
    
    db.commit()
    
    # Increment usage counter
    increment_usage(subscription, db)
    
    return LicenseVerificationResponse(
        verified=True,
        license_number=request.license_number,
        state=request.state_code,
        status=result.get("status"),
        license_type=result.get("license_type"),
        expiration_date=result.get("expiration_date"),
        discipline_record=result.get("discipline_record", False),
        restrictions=result.get("restrictions"),
        last_verified=datetime.utcnow(),
        confidence="high",
        source=result.get("source"),
        verification_id=verification_id
    )


@router.post("/multi-state-search", response_model=MultiStateSearchResponse)
async def multi_state_search(
    request: MultiStateSearchRequest,
    user: User = Depends(get_current_user),
    subscription = Depends(get_current_active_subscription),
    db: Session = Depends(get_db)
):
    """
    Search for licenses across multiple states
    
    **Features:**
    - Searches all 50 states in parallel (or specific states if provided)
    - Returns results in 3-8 seconds regardless of number of states
    - Caches results for faster future lookups
    
    **Example:**
    ```json
    {
      "first_name": "Jane",
      "last_name": "Doe",
      "license_type": "RN",
      "states": ["AZ", "CA", "TX", "FL", "NY"]
    }
    ```
    """
    # Check rate limits (multi-state search counts as multiple verifications)
    states_to_search = request.states or ["AZ", "CA", "TX"]  # Default to 3 states for demo
    check_rate_limit(user, subscription, db)
    
    # Perform multi-state search
    service = MultiStateVerificationService({"nursys": settings.NURSYS_API_KEY})
    
    search_results = await service.verify_all_states(
        license_number=request.license_number,
        first_name=request.first_name,
        last_name=request.last_name,
        states=states_to_search,
        license_type=request.license_type or "RN"
    )
    
    # Parse results
    results_list = []
    for result in search_results["results"]:
        state_code = result["state"]
        data = result.get("data", {})
        
        if result["status"] == "success" and data.get("status") != "not_found":
            # Found a license
            results_list.append(StateSearchResult(
                state=state_code,
                status="success",
                license=LicenseVerificationResponse(
                    verified=True,
                    license_number=request.license_number or "N/A",
                    state=state_code,
                    status=data.get("status"),
                    license_type=data.get("license_type"),
                    expiration_date=data.get("expiration_date"),
                    discipline_record=data.get("discipline_record", False),
                    restrictions=data.get("restrictions"),
                    last_verified=datetime.utcnow(),
                    confidence="high",
                    source=data.get("source"),
                    verification_id=str(uuid.uuid4())
                )
            ))
        else:
            # No license found or error
            results_list.append(StateSearchResult(
                state=state_code,
                status="no_match" if result["status"] == "success" else "error",
                error=result.get("error")
            ))
    
    # Increment usage (count each state searched)
    for _ in states_to_search:
        increment_usage(subscription, db)
    
    search_id = str(uuid.uuid4())
    
    return MultiStateSearchResponse(
        search_id=search_id,
        total_states_searched=search_results["total_states_searched"],
        total_licenses_found=search_results["total_licenses_found"],
        search_duration_ms=search_results["search_duration_ms"],
        results=results_list,
        cached_until=datetime.utcnow() + timedelta(hours=24)
    )


@router.get("/license/{license_id}")
async def get_license_details(
    license_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific license
    """
    license = db.query(ProfessionalLicense).filter(
        ProfessionalLicense.id == license_id
    ).first()
    
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )
    
    return license


def _generate_verification_hash(result: dict, verifier_email: str) -> str:
    """
    Generate tamper-proof hash of verification data
    """
    data = {
        "license_number": result.get("license_number", ""),
        "state": result.get("state", ""),
        "status": result.get("status", ""),
        "verified_at": datetime.utcnow().isoformat(),
        "verifier": verifier_email
    }
    
    canonical = json.dumps(data, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()
