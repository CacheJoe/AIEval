-- Initial AIALES schema.
-- Primary target: PostgreSQL.
-- SQLite local development is supported through SQLAlchemy metadata creation.

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('ADMIN', 'HOD', 'FACULTY', 'STUDENT')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);
CREATE INDEX IF NOT EXISTS ix_users_is_active ON users (is_active);

CREATE TABLE IF NOT EXISTS classes (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    semester VARCHAR(30) NOT NULL,
    faculty_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_classes_name ON classes (name);
CREATE INDEX IF NOT EXISTS ix_classes_semester ON classes (semester);
CREATE INDEX IF NOT EXISTS ix_classes_faculty_id ON classes (faculty_id);

CREATE TABLE IF NOT EXISTS class_enrollments (
    id VARCHAR(36) PRIMARY KEY,
    class_id VARCHAR(36) NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    student_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_class_enrollment UNIQUE (class_id, student_id)
);

CREATE INDEX IF NOT EXISTS ix_class_enrollments_class_id ON class_enrollments (class_id);
CREATE INDEX IF NOT EXISTS ix_class_enrollments_student_id ON class_enrollments (student_id);

CREATE TABLE IF NOT EXISTS experiments (
    id VARCHAR(36) PRIMARY KEY,
    class_id VARCHAR(36) NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    topic VARCHAR(255) NOT NULL,
    description TEXT NULL,
    locked BOOLEAN NOT NULL DEFAULT FALSE,
    locked_at TIMESTAMP WITH TIME ZONE NULL,
    locked_by_id VARCHAR(36) NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_experiments_class_id ON experiments (class_id);

CREATE TABLE IF NOT EXISTS submissions (
    id VARCHAR(36) PRIMARY KEY,
    experiment_id VARCHAR(36) NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    student_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT NULL,
    checksum VARCHAR(64) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'UPLOADED'
        CHECK (status IN ('UPLOADED', 'PROCESSING', 'EVALUATED', 'REJECTED')),
    uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_submission_experiment_student UNIQUE (experiment_id, student_id)
);

CREATE INDEX IF NOT EXISTS ix_submissions_experiment_id ON submissions (experiment_id);
CREATE INDEX IF NOT EXISTS ix_submissions_student_id ON submissions (student_id);
CREATE INDEX IF NOT EXISTS ix_submissions_checksum ON submissions (checksum);

CREATE TABLE IF NOT EXISTS results (
    id VARCHAR(36) PRIMARY KEY,
    submission_id VARCHAR(36) NOT NULL UNIQUE REFERENCES submissions(id) ON DELETE CASCADE,
    marks DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (marks >= 0 AND marks <= 100),
    plagiarism_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    plagiarism_level VARCHAR(10) NOT NULL DEFAULT 'LOW'
        CHECK (plagiarism_level IN ('LOW', 'MEDIUM', 'HIGH')),
    relevance_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    flags JSON NULL,
    breakdown JSON NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_results_submission_id ON results (submission_id);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE NULL,
    user_agent VARCHAR(255) NULL,
    ip_address VARCHAR(64) NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens (user_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NULL REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL
        CHECK (
            action IN (
                'AUDIT_VIEW',
                'LOGIN',
                'LOGOUT',
                'CLASS_CREATE',
                'CLASS_UPDATE',
                'ENROLL_STUDENT',
                'EVALUATION_RUN',
                'EXPERIMENT_CREATE',
                'EXPERIMENT_LOCK',
                'REPORT_EXPORT',
                'RESULT_VIEW',
                'SETTINGS_VIEW',
                'SUBMISSION_UPLOAD',
                'TOKEN_REFRESH',
                'USER_CREATE',
                'USER_STATUS_UPDATE',
                'LOCK_RESULTS'
            )
        ),
    entity_type VARCHAR(100) NULL,
    entity_id VARCHAR(36) NULL,
    details JSON NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_audit_log_user_id ON audit_log (user_id);
CREATE INDEX IF NOT EXISTS ix_audit_log_action ON audit_log (action);
CREATE INDEX IF NOT EXISTS ix_audit_log_timestamp ON audit_log (timestamp);
