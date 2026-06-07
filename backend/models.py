"""
SQLAlchemy models for Mock Test Results.
Uses the same database connection as auth.py.
"""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, String, Integer, Float, DateTime, ForeignKey, Index, Text, func, inspect, text
from sqlalchemy.orm import relationship
from backend.auth import Base


class TestResult(Base):
    """Store overall test attempt results."""
    __tablename__ = "test_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    test_id = Column(String(100), nullable=True, index=True)
    test_name = Column(String(255), nullable=False)
    total_questions = Column(Integer, nullable=False)
    attempted_questions = Column(Integer, nullable=False, default=0)
    correct_answers = Column(Integer, nullable=False, default=0)
    wrong_answers = Column(Integer, nullable=False, default=0)
    unattempted_questions = Column(Integer, nullable=False, default=0)
    score = Column(Float, nullable=False, default=0.0)
    accuracy = Column(Float, nullable=False, default=0.0)
    percentage = Column(Float, nullable=False, default=0.0)
    time_taken_seconds = Column(Integer, nullable=False, default=0)
    attempted_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationship to subject results
    subject_results = relationship("SubjectResult", back_populates="test_result", cascade="all, delete-orphan")
    question_attempts = relationship("QuestionAttempt", back_populates="test_result", cascade="all, delete-orphan")

    @property
    def subjects(self):
        """Expose subject results using the frontend response field name."""
        return self.subject_results

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "test_id": self.test_id,
            "test_name": self.test_name,
            "total_questions": self.total_questions,
            "attempted_questions": self.attempted_questions,
            "correct_answers": self.correct_answers,
            "wrong_answers": self.wrong_answers,
            "unattempted_questions": self.unattempted_questions,
            "score": self.score,
            "accuracy": self.accuracy,
            "percentage": self.percentage,
            "time_taken_seconds": self.time_taken_seconds,
            "attempted_at": self.attempted_at.isoformat() if self.attempted_at else None,
            "subjects": [sr.to_dict() for sr in self.subject_results] if self.subject_results else []
        }


class SubjectResult(Base):
    """Store subject-wise performance within a test."""
    __tablename__ = "subject_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    test_result_id = Column(String(36), ForeignKey("test_results.id"), nullable=False, index=True)
    subject_name = Column(String(255), nullable=False)
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False, default=0)
    wrong_answers = Column(Integer, nullable=False, default=0)
    score = Column(Float, nullable=False, default=0.0)
    accuracy = Column(Float, nullable=False, default=0.0)
    percentage = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationship back to test result
    test_result = relationship("TestResult", back_populates="subject_results")

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "test_result_id": self.test_result_id,
            "subject_name": self.subject_name,
            "total_questions": self.total_questions,
            "correct_answers": self.correct_answers,
            "wrong_answers": self.wrong_answers,
            "score": self.score,
            "accuracy": self.accuracy,
            "percentage": self.percentage
        }


class QuestionAttempt(Base):
    """Store per-question attempt analytics."""
    __tablename__ = "question_attempts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    test_result_id = Column(String(36), ForeignKey("test_results.id"), nullable=False, index=True)
    question_id = Column(String(100), nullable=False, index=True)
    subject = Column(String(255), nullable=False, index=True)
    selected_answer = Column(Text, nullable=True)
    correct_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=False, default=False)
    time_spent = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=func.now(), index=True)

    test_result = relationship("TestResult", back_populates="question_attempts")


Index("idx_test_results_user_created", TestResult.user_id, TestResult.created_at)
Index("idx_subject_results_user_created", SubjectResult.user_id, SubjectResult.created_at)
Index("idx_question_attempts_user_created", QuestionAttempt.user_id, QuestionAttempt.created_at)


def ensure_result_schema(engine):
    """Add new columns to an existing local SQLite database."""
    if not str(engine.url).startswith("sqlite"):
        return

    inspector = inspect(engine)
    with engine.begin() as connection:
        tables = set(inspector.get_table_names())
        if "test_results" in tables:
            columns = {column["name"] for column in inspector.get_columns("test_results")}
            additions = {
                "test_id": "ALTER TABLE test_results ADD COLUMN test_id VARCHAR(100)",
                "attempted_questions": "ALTER TABLE test_results ADD COLUMN attempted_questions INTEGER NOT NULL DEFAULT 0",
                "accuracy": "ALTER TABLE test_results ADD COLUMN accuracy FLOAT NOT NULL DEFAULT 0",
            }
            for column, ddl in additions.items():
                if column not in columns:
                    connection.execute(text(ddl))

        if "subject_results" in tables:
            columns = {column["name"] for column in inspector.get_columns("subject_results")}
            additions = {
                "user_id": "ALTER TABLE subject_results ADD COLUMN user_id VARCHAR(36) NOT NULL DEFAULT ''",
                "accuracy": "ALTER TABLE subject_results ADD COLUMN accuracy FLOAT NOT NULL DEFAULT 0",
            }
            for column, ddl in additions.items():
                if column not in columns:
                    connection.execute(text(ddl))
