"""
Database models for SkillLedger License Verification System
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Text, 
    ForeignKey, ARRAY, JSON, Numeric, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from app.database import Base


class User(Base):
    """User accounts (recruiters, agencies)"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255))
    full_name = Column(String(500))
    organization = Column(String(500))
    
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    api_keys = relationship("APIKey", back_populates="user")
    subscriptions = relationship("UserSubscription", back_populates="user")
    monitors = relationship("LicenseMonitor", back_populates="subscriber")


class APIKey(Base):
    """API keys for programmatic access"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    key = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255))  # Human-readable name for the key
    
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime)
    usage_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")


class SubscriptionPlan(Base):
    """Subscription plans and pricing"""
    __tablename__ = "subscription_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    price_monthly = Column(Numeric(10, 2))
    
    max_verifications_per_month = Column(Integer)  # NULL = unlimited
    includes_alerts = Column(Boolean, default=True)
    includes_api_access = Column(Boolean, default=True)
    includes_bulk_verification = Column(Boolean, default=False)
    includes_ats_integration = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class UserSubscription(Base):
    """User subscription records"""
    __tablename__ = "user_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"))
    
    # Billing
    stripe_subscription_id = Column(String(255))
    status = Column(String(50), default="active")  # active, past_due, canceled
    current_period_start = Column(Date)
    current_period_end = Column(Date)
    
    # Usage tracking
    verifications_this_month = Column(Integer, default=0)
    last_reset_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan")


class ProfessionalLicense(Base):
    """Professional licenses (RN, LPN, CDL, etc.)"""
    __tablename__ = "professional_licenses"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # License identification
    license_number = Column(String(255), nullable=False, index=True)
    state_code = Column(String(2), nullable=False, index=True)
    license_type = Column(String(50), nullable=False)  # 'RN', 'LPN', 'CDL', etc.
    
    # Verification data
    status = Column(String(50), nullable=False, index=True)  # 'active', 'expired', 'suspended', 'revoked'
    issue_date = Column(Date)
    expiration_date = Column(Date, nullable=False, index=True)
    
    # Professional info (optional)
    first_name = Column(String(255))
    last_name = Column(String(255))
    middle_name = Column(String(255))
    
    # Additional info
    discipline_record = Column(Boolean, default=False)
    restrictions = Column(Text)
    board_url = Column(String(500))
    
    # Metadata
    last_verified_at = Column(DateTime, index=True)
    verification_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    verifications = relationship("LicenseVerificationAudit", back_populates="license")
    monitors = relationship("LicenseMonitor", back_populates="license")
    
    __table_args__ = (
        Index('idx_license_lookup', 'license_number', 'state_code'),
    )


class LicenseVerificationAudit(Base):
    """Audit trail for all license verifications"""
    __tablename__ = "license_verification_audit"
    
    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    
    # Who verified
    verifier_user_id = Column(Integer, ForeignKey("users.id"))
    verifier_name = Column(String(500))
    verifier_email = Column(String(500))
    verifier_organization = Column(String(500))
    
    # What was verified
    license_id = Column(Integer, ForeignKey("professional_licenses.id"))
    license_number = Column(String(255), nullable=False, index=True)
    state_code = Column(String(2), nullable=False)
    
    # When
    verified_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Where (network info)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # What was found (immutable snapshot)
    verification_result = Column(JSON, nullable=False)
    license_status = Column(String(50))
    expiration_date = Column(Date)
    discipline_record = Column(Boolean)
    
    # Data source
    data_source = Column(String(100))  # 'nursys', 'ca_dca', etc.
    source_url = Column(String(500))
    confidence_level = Column(String(20))  # 'high', 'medium', 'low'
    
    # Supporting evidence
    screenshot_url = Column(String(500))
    raw_api_response = Column(Text)
    
    # Purpose
    verification_purpose = Column(String(100))  # 'hiring', 'renewal', 'compliance_check'
    notes = Column(Text)
    facility_name = Column(String(500))
    
    # Tamper-proof hash
    verification_hash = Column(String(64), index=True)
    previous_audit_hash = Column(String(64))
    
    # Relationships
    license = relationship("ProfessionalLicense", back_populates="verifications")


class LicenseMonitor(Base):
    """Expiration monitoring subscriptions"""
    __tablename__ = "license_monitors"
    
    id = Column(Integer, primary_key=True, index=True)
    monitor_id = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    
    # What to monitor
    license_id = Column(Integer, ForeignKey("professional_licenses.id"), nullable=False)
    
    # Who is monitoring
    subscriber_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Alert configuration
    alert_at_days = Column(ARRAY(Integer), default=[90, 60, 30, 7, 1, 0])
    alert_methods = Column(ARRAY(String), default=['email', 'webhook'])
    
    # Contact info
    email_addresses = Column(ARRAY(String))
    webhook_url = Column(String(500))
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    last_checked_at = Column(DateTime)
    last_alert_sent_at = Column(DateTime)
    next_check_scheduled_at = Column(DateTime, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    license = relationship("ProfessionalLicense", back_populates="monitors")
    subscriber = relationship("User", back_populates="monitors")
    alerts = relationship("LicenseAlertSent", back_populates="monitor")


class LicenseAlertSent(Base):
    """History of alerts sent"""
    __tablename__ = "license_alerts_sent"
    
    id = Column(Integer, primary_key=True, index=True)
    monitor_id = Column(Integer, ForeignKey("license_monitors.id"))
    license_id = Column(Integer, ForeignKey("professional_licenses.id"))
    
    # Alert details
    alert_type = Column(String(50))  # 'expiring_soon', 'expired', 'status_change'
    days_until_expiration = Column(Integer)
    severity = Column(String(20))  # 'info', 'warning', 'critical'
    
    # Message
    message_subject = Column(Text)
    message_body = Column(Text)
    
    # Delivery
    sent_via = Column(String(50))  # 'email', 'webhook'
    sent_to = Column(Text)
    delivery_status = Column(String(50))  # 'sent', 'delivered', 'failed'
    
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    monitor = relationship("LicenseMonitor", back_populates="alerts")


class BulkVerificationJob(Base):
    """Bulk verification job tracking"""
    __tablename__ = "bulk_verification_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    
    # Who requested
    requester_id = Column(Integer, ForeignKey("users.id"))
    
    # Job details
    total_licenses = Column(Integer, nullable=False)
    completed_licenses = Column(Integer, default=0)
    successful_verifications = Column(Integer, default=0)
    failed_verifications = Column(Integer, default=0)
    
    # Status
    status = Column(String(50), default='queued', index=True)  # 'queued', 'processing', 'completed', 'failed'
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Files
    input_file_url = Column(String(500))
    output_file_url = Column(String(500))
    
    # Progress
    progress_percentage = Column(Numeric(5, 2), default=0.00)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    results = relationship("BulkVerificationResult", back_populates="job")


class BulkVerificationResult(Base):
    """Individual results within bulk job"""
    __tablename__ = "bulk_verification_results"
    
    id = Column(Integer, primary_key=True, index=True)
    bulk_job_id = Column(Integer, ForeignKey("bulk_verification_jobs.id"))
    
    # Input data
    row_number = Column(Integer)
    license_number = Column(String(255))
    state_code = Column(String(2))
    candidate_name = Column(String(500))
    
    # Result
    verification_status = Column(String(50))  # 'verified', 'not_found', 'error'
    license_id = Column(Integer, ForeignKey("professional_licenses.id"))
    
    # Result data
    license_type = Column(String(50))
    status = Column(String(50))
    expiration_date = Column(Date)
    discipline_record = Column(Boolean)
    
    verified_at = Column(DateTime)
    error_message = Column(Text)
    
    # Relationships
    job = relationship("BulkVerificationJob", back_populates="results")


class StateBoardCache(Base):
    """Cache for state board API responses"""
    __tablename__ = "state_board_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    
    license_number = Column(String(255), nullable=False)
    state_code = Column(String(2), nullable=False)
    
    cached_response = Column(JSON, nullable=False)
    cache_expires_at = Column(DateTime, nullable=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_cache_lookup', 'license_number', 'state_code'),
    )
