"""
Pydantic schemas for Mock Test Results validation and serialization.
"""
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field, RootModel, validator


class SubjectResultCreate(BaseModel):
    """Schema for creating a subject result."""
    subject_name: str = Field(..., min_length=1, max_length=255)
    total_questions: int = Field(..., gt=0)
    correct_answers: int = Field(..., ge=0)
    wrong_answers: int = Field(..., ge=0)
    score: float = Field(..., ge=0)
    accuracy: Optional[float] = Field(None, ge=0, le=100)
    percentage: float = Field(..., ge=0, le=100)

    @validator("correct_answers", "wrong_answers", pre=True, always=True)
    def validate_answers(cls, v):
        """Ensure answers are non-negative integers."""
        return int(v) if v is not None else 0

    @validator("percentage", pre=True, always=True)
    def validate_percentage(cls, v):
        """Ensure percentage is between 0 and 100."""
        v = float(v) if v is not None else 0
        if not (0 <= v <= 100):
            raise ValueError("Percentage must be between 0 and 100")
        return v


class SubjectResultResponse(BaseModel):
    """Schema for subject result response."""
    id: str
    user_id: Optional[str] = None
    test_result_id: str
    subject_name: str
    total_questions: int
    correct_answers: int
    wrong_answers: int
    score: float
    accuracy: float = 0.0
    percentage: float

    class Config:
        from_attributes = True


class TestResultCreate(BaseModel):
    """Schema for creating a test result."""
    test_id: Optional[str] = None
    test_name: str = Field(..., min_length=1, max_length=255)
    total_questions: int = Field(..., gt=0)
    attempted_questions: Optional[int] = Field(None, ge=0)
    correct_answers: int = Field(..., ge=0)
    wrong_answers: int = Field(..., ge=0)
    unattempted_questions: int = Field(..., ge=0)
    score: float = Field(..., ge=0)
    accuracy: Optional[float] = Field(None, ge=0, le=100)
    percentage: float = Field(..., ge=0, le=100)
    time_taken_seconds: int = Field(..., ge=0)
    subjects: List[SubjectResultCreate] = Field(default_factory=list)

    @validator("correct_answers", "wrong_answers", "unattempted_questions", pre=True, always=True)
    def validate_counts(cls, v):
        """Ensure counts are non-negative integers."""
        return int(v) if v is not None else 0

    @validator("percentage", pre=True, always=True)
    def validate_percentage(cls, v):
        """Ensure percentage is between 0 and 100."""
        v = float(v) if v is not None else 0
        if not (0 <= v <= 100):
            raise ValueError("Percentage must be between 0 and 100")
        return v

    @validator("total_questions")
    def validate_total_questions(cls, v):
        """Ensure total questions is positive."""
        if v <= 0:
            raise ValueError("Total questions must be greater than 0")
        return v


class TestResultResponse(BaseModel):
    """Schema for test result response."""
    id: str
    user_id: str
    test_id: Optional[str] = None
    test_name: str
    total_questions: int
    attempted_questions: int = 0
    correct_answers: int
    wrong_answers: int
    unattempted_questions: int
    score: float
    accuracy: float = 0.0
    percentage: float
    time_taken_seconds: int
    attempted_at: datetime
    subjects: List[SubjectResultResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class AnalyticsResponse(BaseModel):
    """Schema for overall analytics."""
    total_tests: int
    average_score: float
    best_score: float
    worst_score: float
    average_accuracy: float


class ProgressDataPoint(BaseModel):
    """Data point for progress tracking."""
    test_name: str
    score: float
    attempted_at: str
    percentage: Optional[float] = None


class ProgressResponse(RootModel[List[ProgressDataPoint]]):
    """Schema for progress data (for graphing)."""


class SubjectPerformance(BaseModel):
    """Schema for subject-wise performance."""
    subject: str
    average_percentage: float
    best_percentage: float
    total_tests: int = 0
    total_questions: int = 0
    total_correct: int = 0
    total_wrong: int = 0


class ProfileOverviewResponse(BaseModel):
    total_tests: int
    average_score: float
    best_score: float
    lowest_score: float
    accuracy: float
    total_questions: int
    correct_answers: int
    wrong_answers: int
    total_time_spent_seconds: int


class RecentActivityItem(BaseModel):
    id: str
    test_name: str
    percentage: float
    attempted_at: str


class AccuracyTrendPoint(BaseModel):
    test_name: str
    accuracy: float
    attempted_at: str


class StrengthAnalysisResponse(BaseModel):
    strongest_subject: str
    strongest_score: float
    weakest_subject: str
    weakest_score: float
    top_subjects: List[SubjectPerformance]
    bottom_subjects: List[SubjectPerformance]


class SubjectPerformanceResponse(RootModel[List[SubjectPerformance]]):
    """Schema for subject performance list."""


class SubmittedQuestion(BaseModel):
    question_id: str | int
    subject: str = "General"
    selected_answer: Optional[str] = ""
    correct_answer: Optional[str] = ""
    time_spent: int = Field(0, ge=0)


class TestSubmitRequest(BaseModel):
    test_id: Optional[str] = None
    test_name: str = Field(..., min_length=1, max_length=255)
    total_questions: int = Field(..., gt=0)
    time_taken_seconds: int = Field(0, ge=0)
    questions: List[SubmittedQuestion]
