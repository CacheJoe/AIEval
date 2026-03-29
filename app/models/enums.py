"""Shared enums."""

from enum import StrEnum


class UserRole(StrEnum):
    """Application user roles."""

    ADMIN = "ADMIN"
    HOD = "HOD"
    FACULTY = "FACULTY"
    STUDENT = "STUDENT"


class SimilarityLevel(StrEnum):
    """Plagiarism severity labels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SubmissionStatus(StrEnum):
    """Submission processing states."""

    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    EVALUATED = "EVALUATED"
    REJECTED = "REJECTED"


class AuditAction(StrEnum):
    """Tracked audit actions."""

    AUDIT_VIEW = "AUDIT_VIEW"
    CLASS_CREATE = "CLASS_CREATE"
    CLASS_UPDATE = "CLASS_UPDATE"
    ENROLL_STUDENT = "ENROLL_STUDENT"
    EVALUATION_RUN = "EVALUATION_RUN"
    EXPERIMENT_CREATE = "EXPERIMENT_CREATE"
    EXPERIMENT_LOCK = "EXPERIMENT_LOCK"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    REPORT_EXPORT = "REPORT_EXPORT"
    RESULT_VIEW = "RESULT_VIEW"
    SETTINGS_VIEW = "SETTINGS_VIEW"
    SUBMISSION_UPLOAD = "SUBMISSION_UPLOAD"
    LOCK_RESULTS = "LOCK_RESULTS"
    TOKEN_REFRESH = "TOKEN_REFRESH"
    USER_CREATE = "USER_CREATE"
    USER_STATUS_UPDATE = "USER_STATUS_UPDATE"
