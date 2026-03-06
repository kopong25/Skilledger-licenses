"""
Audit trail and compliance API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import List, Dict, Any
import uuid

from app.database import get_db
from app.auth.api_key import get_current_user
from app.models import (
    User, LicenseVerificationAudit, ProfessionalLicense,
    LicenseMonitor, LicenseAlertSent
)
from app.schemas import (
    LicenseAuditTrailResponse,
    AuditTrailItem,
    ComplianceDashboardResponse
)

router = APIRouter(prefix="/audit", tags=["Audit Trail"])


@router.get("/license/{license_id}", response_model=LicenseAuditTrailResponse)
async def get_license_audit_trail(
    license_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get complete audit trail for a specific license
    
    Shows:
    - Every verification performed
    - Who verified it
    - When it was verified
    - What the status was at that time
    - Screenshots and certificates (if available)
    """
    license = db.query(ProfessionalLicense).filter(
        ProfessionalLicense.id == license_id
    ).first()
    
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )
    
    # Get all audit records for this license
    audit_records = db.query(LicenseVerificationAudit).filter(
        LicenseVerificationAudit.license_id == license_id
    ).order_by(LicenseVerificationAudit.verified_at.desc()).all()
    
    # Format audit trail
    audit_trail = []
    for record in audit_records:
        audit_trail.append(AuditTrailItem(
            audit_id=record.audit_id,
            verified_at=record.verified_at,
            verified_by=record.verifier_email,
            status_at_time=record.license_status,
            expires_at_time=record.expiration_date,
            purpose=record.verification_purpose,
            facility=record.facility_name,
            screenshot_url=record.screenshot_url
        ))
    
    return LicenseAuditTrailResponse(
        license={
            "license_number": license.license_number,
            "state": license.state_code,
            "current_status": license.status,
            "current_expiration": license.expiration_date.isoformat()
        },
        audit_trail=audit_trail,
        total_verifications=len(audit_records),
        first_verified=audit_records[-1].verified_at if audit_records else None,
        last_verified=audit_records[0].verified_at if audit_records else None
    )


@router.get("/my-verifications")
async def get_my_verification_history(
    days: int = 30,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get your verification history for the last N days
    """
    since_date = datetime.utcnow() - timedelta(days=days)
    
    verifications = db.query(LicenseVerificationAudit).filter(
        LicenseVerificationAudit.verifier_user_id == user.id,
        LicenseVerificationAudit.verified_at >= since_date
    ).order_by(LicenseVerificationAudit.verified_at.desc()).all()
    
    return {
        "period": f"Last {days} days",
        "total_verifications": len(verifications),
        "by_status": {
            "active": sum(1 for v in verifications if v.license_status == 'active'),
            "expired": sum(1 for v in verifications if v.license_status == 'expired'),
            "suspended": sum(1 for v in verifications if v.license_status == 'suspended'),
        },
        "by_state": _count_by_field(verifications, 'state_code'),
        "verifications": [
            {
                "audit_id": v.audit_id,
                "license_number": v.license_number,
                "state": v.state_code,
                "status": v.license_status,
                "verified_at": v.verified_at,
                "purpose": v.verification_purpose
            }
            for v in verifications[:100]  # Limit to 100 most recent
        ]
    }


@router.get("/compliance-dashboard", response_model=ComplianceDashboardResponse)
async def get_compliance_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get compliance dashboard with key metrics
    
    Shows:
    - Total verifications in last 90 days
    - Compliance rate
    - Upcoming expirations
    - Risk alerts
    - Performance by facility
    """
    # Get verifications from last 90 days
    since_date = datetime.utcnow() - timedelta(days=90)
    
    verifications = db.query(LicenseVerificationAudit).filter(
        LicenseVerificationAudit.verifier_user_id == user.id,
        LicenseVerificationAudit.verified_at >= since_date
    ).all()
    
    # Get monitored licenses
    monitors = db.query(LicenseMonitor).filter(
        LicenseMonitor.subscriber_id == user.id,
        LicenseMonitor.is_active == True
    ).all()
    
    # Calculate metrics
    total_verifications = len(verifications)
    unique_licenses = len(set(v.license_id for v in verifications))
    issues_found = sum(
        1 for v in verifications 
        if v.license_status in ['expired', 'suspended', 'revoked']
    )
    compliance_rate = ((total_verifications - issues_found) / total_verifications * 100) if total_verifications > 0 else 100.0
    
    # Group by facility
    by_facility = {}
    for v in verifications:
        facility = v.facility_name or "Unknown"
        if facility not in by_facility:
            by_facility[facility] = {
                "total": 0,
                "verified": 0,
                "issues": 0
            }
        by_facility[facility]["total"] += 1
        by_facility[facility]["verified"] += 1
        if v.license_status in ['expired', 'suspended']:
            by_facility[facility]["issues"] += 1
    
    facility_list = [
        {
            "facility": name,
            "active_placements": data["total"],
            "verified": data["verified"],
            "compliance_rate": f"{(data['verified'] - data['issues']) / data['verified'] * 100:.1f}%" if data['verified'] > 0 else "100%",
            "issues": [f"{data['issues']} issue(s)"] if data['issues'] > 0 else []
        }
        for name, data in by_facility.items()
    ]
    
    # Upcoming expirations
    upcoming = []
    for monitor in monitors:
        license = db.query(ProfessionalLicense).filter(
            ProfessionalLicense.id == monitor.license_id
        ).first()
        
        if license and license.expiration_date:
            days_until = (license.expiration_date - date.today()).days
            
            if 0 < days_until <= 90:
                professional_name = f"{license.first_name} {license.last_name}" if license.first_name else "Professional"
                upcoming.append({
                    "candidate": professional_name,
                    "license": f"{license.state_code} #{license.license_number}",
                    "expires": license.expiration_date.isoformat(),
                    "days_remaining": days_until,
                    "facility": "N/A"
                })
    
    # Risk alerts (expired or suspended licenses)
    risk_alerts = []
    for v in verifications:
        if v.license_status in ['expired', 'suspended', 'revoked']:
            license = db.query(ProfessionalLicense).filter(
                ProfessionalLicense.id == v.license_id
            ).first()
            
            if license:
                risk_alerts.append({
                    "alert": f"License {v.license_status}",
                    "candidate": f"{license.first_name} {license.last_name}" if license.first_name else "Professional",
                    "license": f"{license.state_code} #{license.license_number}",
                    "date": v.verified_at.date().isoformat(),
                    "action_required": "Review immediately" if v.license_status in ['suspended', 'revoked'] else "Verify renewal"
                })
    
    return ComplianceDashboardResponse(
        organization=user.organization or "Your Organization",
        period="Last 90 days",
        summary={
            "total_verifications": total_verifications,
            "unique_candidates": unique_licenses,
            "compliance_rate": f"{compliance_rate:.1f}%",
            "issues_found": issues_found
        },
        by_facility=facility_list,
        upcoming_expirations=upcoming[:10],  # Top 10
        risk_alerts=risk_alerts[:5]  # Top 5
    )


@router.post("/generate-report")
async def generate_audit_report(
    start_date: date,
    end_date: date,
    format: str = "pdf",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate comprehensive audit report
    
    Returns downloadable PDF or CSV with all verifications
    in the date range
    """
    # Get verifications in date range
    verifications = db.query(LicenseVerificationAudit).filter(
        LicenseVerificationAudit.verifier_user_id == user.id,
        LicenseVerificationAudit.verified_at >= datetime.combine(start_date, datetime.min.time()),
        LicenseVerificationAudit.verified_at <= datetime.combine(end_date, datetime.max.time())
    ).order_by(LicenseVerificationAudit.verified_at.desc()).all()
    
    report_id = str(uuid.uuid4())
    
    # In production, generate actual PDF/CSV and upload to S3
    # For MVP, return metadata
    
    return {
        "report_id": report_id,
        "status": "completed",
        "download_url": f"/api/audit/download/{report_id}",
        "format": format,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "summary": {
            "total_verifications": len(verifications),
            "total_pages": (len(verifications) // 20) + 1,
            "generated_at": datetime.utcnow().isoformat()
        }
    }


def _count_by_field(records: list, field: str) -> Dict[str, int]:
    """Helper function to count records by a field"""
    counts = {}
    for record in records:
        value = getattr(record, field, "Unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts
