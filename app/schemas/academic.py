"""Schemas for classes and experiments."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ClassCreate(BaseModel):
    """Create a class."""

    name: str = Field(min_length=2, max_length=120)
    semester: str = Field(min_length=2, max_length=30)
    faculty_id: str = Field(min_length=36, max_length=36)


class ExperimentCreate(BaseModel):
    """Create an experiment."""

    topic: str = Field(min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    context: str | None = Field(default=None, max_length=4000)
    reference_content: str | None = Field(default=None, max_length=12000)


class ExperimentLockResponse(BaseModel):
    """Lock response."""

    experiment_id: str
    locked: bool
    locked_at: datetime | None


class ExperimentRead(BaseModel):
    """Experiment read model."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    class_id: str
    topic: str
    description: str | None
    locked: bool
    locked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ClassRead(BaseModel):
    """Class read model."""

    id: str
    name: str
    semester: str
    faculty_id: str
    faculty_name: str | None
    experiment_count: int
    submission_count: int
    created_at: datetime
    updated_at: datetime


class ClassDetail(ClassRead):
    """Class detail model."""

    experiments: list[ExperimentRead]
