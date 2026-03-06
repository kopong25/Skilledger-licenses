"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class LicenseStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    INACTIVE = "inactive"


class LicenseType(str, Enum):
    RN = "RN"
    LPN = "LPN"
    CDL = "CDL"
    PHARMACY = "pharmacy"
    TEACHING = "teaching"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ============================================================================
# User & Auth Schemas
# ============================================================================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    organization: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    organization: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class APIKeyCreate(BaseModel):
    name: str = Field(..., description="Human-readable name for the API key")


class APIKeyResponse(BaseModel):
    id: int
    key: str
    name: str
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ============================================================================
# License Schemas
# ============================================================================

class LicenseVerificationRequest(BaseModel):
    license_number: str = Field(..., min_length=1, max_length=255)
    state_code: str = Field(..., min_length=2, max_length=2)
    license_type: Optional[LicenseType] = None


class LicenseVerificationResponse(BaseModel):
    verified: bool
    license_number: str
    state: str
    status: Optional[LicenseStatus]
    license_type: Optional[str]
    expiration_date: Optional[date]
    discipline_record: Optional[bool]
    restrictions: Optional[str]
    last_verified: datetime
    confidence: str = "high"
    source: str
    verification_id: str


class LicenseDetailResponse(BaseModel):
    id: int
    license_number: str
    state_code: str
    license_type: str
    status: str
    issue_date: Optional[date]
    expiration_date: date
    discipline_record: bool
    restrictions: Optional[str]
    last_verified_at: Optional[datetime]
    verification_count: int
    
    class Config:
        from_attributes = True


# ============================================================================
# Multi-State Search Schemas
# ============================================================================

class MultiStateSearchRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    license_number: Optional[str] = None
    license_type: Optional[LicenseType] = None
    states: Optional[List[str]] = None  # If None, search all 50 states
    include_expired: bool = False


class StateSearchResult(BaseModel):
    state: str
    status: str  # 'success', 'no_match', 'error'
    license: Optional[LicenseVerificationResponse] = None
    error: Optional[str] = None


class MultiStateSearchResponse(BaseModel):
    search_id: str
    total_states_searched: int
    total_licenses_found: int
    search_duration_ms: int
    results: List[StateSearchResult]
    cached_until: datetime


# ============================================================================
# Bulk Verification Schemas
# ============================================================================

class BulkVerificationStart(BaseModel):
    notify_on_completion: bool = True
    webhook_url: Optional[str] = None
    priority: str = "normal"


class BulkJobStatus(BaseModel):
    job_id: str
    status: str
    total: int
    completed: int
    successful: int
    failed: int
    percentage: float
    estimated_completion_time: Optional[datetime]


class BulkResultItem(BaseModel):
    row: int
    license_number: str
    state: str
    candidate_name: Optional[str]
    status: str
    license_type: Optional[str]
    expiration_date: Optional[date]
    discipline_record: Optional[bool]
    verified_at: Optional[datetime]
    error_message: Optional[str]


class BulkVerificationResults(BaseModel):
    job_id: str
    status: str
    results_url: Optional[str]
    summary: Dict[str, int]
    download_formats: List[str] = ["csv", "xlsx", "json"]


# ============================================================================
# Monitoring Schemas
# ============================================================================

class MonitoringSubscribeRequest(BaseModel):
    license_id: int
    alert_at_days: List[int] = [90, 60, 30, 7, 1]
    email: Optional[EmailStr] = None
    webhook_url: Optional[str] = None
    alert_for: List[str] = ["expiration", "status_change"]


class MonitoringSubscribeResponse(BaseModel):
    monitor_id: str
    status: str
    monitoring: Dict[str, Any]
    next_alert: Optional[date]
    alerts_configured: List[str]


class MonitoredLicenseResponse(BaseModel):
    monitor_id: str
    professional_name: Optional[str]
    license_number: str
    state: str
    type: str
    status: str
    expires: date
    days_until_expiration: int
    next_alert: Optional[date]
    priority: str


class MonitoringListResponse(BaseModel):
    total_monitoring: int
    by_status: Dict[str, int]
    monitors: List[MonitoredLicenseResponse]


# ============================================================================
# Audit Trail Schemas
# ============================================================================

class AuditRecordRequest(BaseModel):
    license_number: str
    state: str
    result: Dict[str, Any]
    purpose: Optional[str] = "verification"
    facility: Optional[str] = None
    notes: Optional[str] = None


class AuditRecordResponse(BaseModel):
    audit_id: str
    recorded_at: datetime
    verification_hash: str
    screenshot_saved: bool
    certificate_available: bool


class AuditTrailItem(BaseModel):
    audit_id: str
    verified_at: datetime
    verified_by: str
    status_at_time: str
    expires_at_time: date
    purpose: Optional[str]
    facility: Optional[str]
    screenshot_url: Optional[str]


class LicenseAuditTrailResponse(BaseModel):
    license: Dict[str, Any]
    audit_trail: List[AuditTrailItem]
    total_verifications: int
    first_verified: Optional[datetime]
    last_verified: Optional[datetime]


class AuditReportRequest(BaseModel):
    report_type: str = "compliance"
    date_range: Dict[str, date]
    filters: Optional[Dict[str, Any]] = None
    format: str = "pdf"
    include_screenshots: bool = False


class AuditReportResponse(BaseModel):
    report_id: str
    status: str
    estimated_completion: str
    webhook_on_complete: bool


class ComplianceDashboardResponse(BaseModel):
    organization: str
    period: str
    summary: Dict[str, Any]
    by_facility: List[Dict[str, Any]]
    upcoming_expirations: List[Dict[str, Any]]
    risk_alerts: List[Dict[str, Any]]


# ============================================================================
# Generic Response Schemas
# ============================================================================

class HealthCheckResponse(BaseModel):
    status: str
    version: str
    database: str
    cache: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SuccessResponse(BaseModel):
    message: str
    data: Optional[Dict[str, Any]] = None
