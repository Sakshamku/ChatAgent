"""
Service layer for Mock Test Results.
Handles all business logic for test results and analytics.
"""
from typing import List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from backend.models import QuestionAttempt, TestResult, SubjectResult
from backend.schemas import (
    TestResultCreate,
    TestResultResponse,
    SubjectResultCreate,
    AnalyticsResponse,
    SubjectPerformance,
    TestSubmitRequest,
)


class TestResultService:
    """Service class for test result operations."""

    @staticmethod
    def create_test_result(
        db: Session,
        user_id: str,
        test_data: TestResultCreate
    ) -> TestResultResponse:
        """Create a new test result with subject-wise breakdown."""
        attempted_questions = (
            test_data.attempted_questions
            if test_data.attempted_questions is not None
            else test_data.correct_answers + test_data.wrong_answers
        )
        accuracy = (
            test_data.accuracy
            if test_data.accuracy is not None
            else round((test_data.correct_answers / max(1, attempted_questions)) * 100, 2)
        )
        test_result = TestResult(
            user_id=user_id,
            test_id=test_data.test_id,
            test_name=test_data.test_name,
            total_questions=test_data.total_questions,
            attempted_questions=attempted_questions,
            correct_answers=test_data.correct_answers,
            wrong_answers=test_data.wrong_answers,
            unattempted_questions=test_data.unattempted_questions,
            score=test_data.score,
            accuracy=accuracy,
            percentage=test_data.percentage,
            time_taken_seconds=test_data.time_taken_seconds,
        )
        db.add(test_result)
        db.flush()  # Flush to get the ID without committing

        # Create subject results
        for subject_data in test_data.subjects:
            subject_result = SubjectResult(
                user_id=user_id,
                test_result_id=test_result.id,
                subject_name=subject_data.subject_name,
                total_questions=subject_data.total_questions,
                correct_answers=subject_data.correct_answers,
                wrong_answers=subject_data.wrong_answers,
                score=subject_data.score,
                accuracy=subject_data.accuracy if subject_data.accuracy is not None else subject_data.percentage,
                percentage=subject_data.percentage,
            )
            db.add(subject_result)

        db.commit()
        db.refresh(test_result)
        return TestResultResponse.model_validate(test_result)

    @staticmethod
    def submit_test(db: Session, user_id: str, payload: TestSubmitRequest) -> dict:
        """Validate submitted answers and persist result, subject rows, and question attempts."""
        subject_stats: dict[str, dict] = {}
        correct_answers = 0
        attempted_questions = 0

        for question in payload.questions:
            selected = str(question.selected_answer or "").strip()
            correct = str(question.correct_answer or "").strip()
            is_attempted = bool(selected)
            is_correct = is_attempted and selected.upper() == correct.upper()
            subject = question.subject or "General"

            if is_attempted:
                attempted_questions += 1
            if is_correct:
                correct_answers += 1

            subject_stats.setdefault(
                subject,
                {"total_questions": 0, "correct_answers": 0, "wrong_answers": 0},
            )
            subject_stats[subject]["total_questions"] += 1
            if is_correct:
                subject_stats[subject]["correct_answers"] += 1
            elif is_attempted:
                subject_stats[subject]["wrong_answers"] += 1

        total_questions = payload.total_questions or len(payload.questions)
        wrong_answers = max(0, attempted_questions - correct_answers)
        unattempted = max(0, total_questions - attempted_questions)
        percentage = round((correct_answers / max(1, total_questions)) * 100, 2)
        accuracy = round((correct_answers / max(1, attempted_questions)) * 100, 2)

        test_result = TestResult(
            user_id=user_id,
            test_id=payload.test_id,
            test_name=payload.test_name,
            total_questions=total_questions,
            attempted_questions=attempted_questions,
            correct_answers=correct_answers,
            wrong_answers=wrong_answers,
            unattempted_questions=unattempted,
            score=float(correct_answers),
            accuracy=accuracy,
            percentage=percentage,
            time_taken_seconds=payload.time_taken_seconds,
        )
        db.add(test_result)
        db.flush()

        for subject_name, stats in subject_stats.items():
            subject_total = stats["total_questions"]
            subject_correct = stats["correct_answers"]
            subject_wrong = stats["wrong_answers"]
            subject_attempted = subject_correct + subject_wrong
            subject_accuracy = round((subject_correct / max(1, subject_attempted)) * 100, 2)
            subject_percentage = round((subject_correct / max(1, subject_total)) * 100, 2)
            db.add(
                SubjectResult(
                    user_id=user_id,
                    test_result_id=test_result.id,
                    subject_name=subject_name,
                    total_questions=subject_total,
                    correct_answers=subject_correct,
                    wrong_answers=subject_wrong,
                    score=float(subject_correct),
                    accuracy=subject_accuracy,
                    percentage=subject_percentage,
                )
            )

        for question in payload.questions:
            selected = str(question.selected_answer or "").strip()
            correct = str(question.correct_answer or "").strip()
            db.add(
                QuestionAttempt(
                    user_id=user_id,
                    test_result_id=test_result.id,
                    question_id=str(question.question_id),
                    subject=question.subject or "General",
                    selected_answer=selected,
                    correct_answer=correct,
                    is_correct=bool(selected) and selected.upper() == correct.upper(),
                    time_spent=question.time_spent,
                )
            )

        db.commit()
        db.refresh(test_result)
        return {
            "result": TestResultResponse.model_validate(test_result),
            "dashboard": TestResultService.get_dashboard(db, user_id),
            "profile": TestResultService.get_complete_profile(db, user_id),
        }

    @staticmethod
    def get_test_results(
        db: Session,
        user_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[TestResultResponse]:
        """Get all test results for a user (latest first)."""
        results = db.query(TestResult).filter(
            TestResult.user_id == user_id
        ).order_by(desc(TestResult.attempted_at)).offset(skip).limit(limit).all()

        return [TestResultResponse.model_validate(r) for r in results]

    @staticmethod
    def get_test_result_by_id(
        db: Session,
        user_id: str,
        result_id: str
    ) -> Optional[TestResultResponse]:
        """Get a specific test result (only if user owns it)."""
        result = db.query(TestResult).filter(
            TestResult.id == result_id,
            TestResult.user_id == user_id
        ).first()

        return TestResultResponse.model_validate(result) if result else None

    @staticmethod
    def delete_test_result(
        db: Session,
        user_id: str,
        result_id: str
    ) -> bool:
        """Delete a test result and its subject results (only if user owns it)."""
        result = db.query(TestResult).filter(
            TestResult.id == result_id,
            TestResult.user_id == user_id
        ).first()

        if not result:
            return False

        db.delete(result)  # Cascade delete will remove subject_results
        db.commit()
        return True

    @staticmethod
    def calculate_analytics(db: Session, user_id: str) -> AnalyticsResponse:
        """Calculate overall analytics for a user."""
        results = db.query(TestResult).filter(
            TestResult.user_id == user_id
        ).all()

        if not results:
            return AnalyticsResponse(
                total_tests=0,
                average_score=0.0,
                best_score=0.0,
                worst_score=0.0,
                average_accuracy=0.0
            )

        total_tests = len(results)
        scores = [r.score for r in results]
        percentages = [r.accuracy or r.percentage for r in results]

        average_score = sum(scores) / total_tests if total_tests > 0 else 0.0
        best_score = max(scores) if scores else 0.0
        worst_score = min(scores) if scores else 0.0
        average_accuracy = sum(percentages) / total_tests if total_tests > 0 else 0.0

        return AnalyticsResponse(
            total_tests=total_tests,
            average_score=round(average_score, 2),
            best_score=round(best_score, 2),
            worst_score=round(worst_score, 2),
            average_accuracy=round(average_accuracy, 2)
        )

    @staticmethod
    def get_progress_data(db: Session, user_id: str) -> List[dict]:
        """Get progress data for graphing."""
        results = db.query(TestResult).filter(
            TestResult.user_id == user_id
        ).order_by(TestResult.attempted_at).all()

        return [
            {
                "test_name": r.test_name,
                "score": r.score,
                "percentage": r.percentage,
                "accuracy": r.accuracy,
                "attempted_at": r.attempted_at.strftime("%Y-%m-%d")
            }
            for r in results
        ]

    @staticmethod
    def calculate_subject_performance(db: Session, user_id: str) -> List[SubjectPerformance]:
        """Calculate subject-wise average performance."""
        # Get all subject results for the user
        subject_results = db.query(SubjectResult).join(
            TestResult,
            SubjectResult.test_result_id == TestResult.id
        ).filter(TestResult.user_id == user_id).all()

        if not subject_results:
            return []

        # Group by subject name
        subject_data = {}
        for sr in subject_results:
            if sr.subject_name not in subject_data:
                subject_data[sr.subject_name] = {
                    "percentages": [],
                    "best_percentage": 0.0,
                    "total_tests": 0,
                    "total_questions": 0,
                    "total_correct": 0,
                    "total_wrong": 0,
                }
            subject_data[sr.subject_name]["percentages"].append(sr.percentage)
            subject_data[sr.subject_name]["best_percentage"] = max(
                subject_data[sr.subject_name]["best_percentage"], sr.percentage
            )
            subject_data[sr.subject_name]["total_tests"] += 1
            subject_data[sr.subject_name]["total_questions"] += sr.total_questions
            subject_data[sr.subject_name]["total_correct"] += sr.correct_answers
            subject_data[sr.subject_name]["total_wrong"] += sr.wrong_answers

        # Calculate averages
        performance = []
        for subject_name, data in subject_data.items():
            avg_percentage = sum(data["percentages"]) / len(data["percentages"])
            performance.append(
                SubjectPerformance(
                    subject=subject_name,
                    average_percentage=round(avg_percentage, 2),
                    best_percentage=round(data["best_percentage"], 2),
                    total_tests=data["total_tests"],
                    total_questions=data["total_questions"],
                    total_correct=data["total_correct"],
                    total_wrong=data["total_wrong"],
                )
            )

        # Sort by average percentage (descending)
        performance.sort(key=lambda x: x.average_percentage, reverse=True)
        return performance

    @staticmethod
    def get_profile_overview(db: Session, user_id: str) -> dict:
        """Build dashboard overview statistics for a user."""
        results = db.query(TestResult).filter(TestResult.user_id == user_id).all()

        total_tests = len(results)
        if total_tests == 0:
            return {
                "total_tests": 0,
                "average_score": 0.0,
                "best_score": 0.0,
                "lowest_score": 0.0,
                "accuracy": 0.0,
                "total_questions": 0,
                "correct_answers": 0,
                "wrong_answers": 0,
                "total_time_spent_seconds": 0,
            }

        total_questions = sum(r.total_questions for r in results)
        total_correct = sum(r.correct_answers for r in results)
        total_wrong = sum(r.wrong_answers for r in results)
        average_score = sum(r.percentage for r in results) / total_tests
        best_score = max(r.percentage for r in results)
        lowest_score = min(r.percentage for r in results)
        accuracy = round(
            (total_correct / max(1, total_correct + total_wrong)) * 100,
            2,
        )
        total_time = sum(r.time_taken_seconds for r in results)

        return {
            "total_tests": total_tests,
            "average_score": round(average_score, 2),
            "best_score": round(best_score, 2),
            "lowest_score": round(lowest_score, 2),
            "accuracy": accuracy,
            "total_questions": total_questions,
            "correct_answers": total_correct,
            "wrong_answers": total_wrong,
            "total_time_spent_seconds": total_time,
        }

    @staticmethod
    def get_profile_history(
        db: Session,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        query_text: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        min_score: float | None = None,
        max_score: float | None = None,
        sort_by: str = "attempted_at",
        sort_dir: str = "desc",
    ) -> dict:
        """Get paginated mock test history with filters."""
        query = db.query(TestResult).filter(TestResult.user_id == user_id)

        if query_text:
            query = query.filter(TestResult.test_name.ilike(f"%{query_text}%"))
        if date_from:
            query = query.filter(TestResult.attempted_at >= date_from)
        if date_to:
            query = query.filter(TestResult.attempted_at <= date_to)
        if min_score is not None:
            query = query.filter(TestResult.percentage >= min_score)
        if max_score is not None:
            query = query.filter(TestResult.percentage <= max_score)

        total = query.count()
        order_target = {
            "attempted_at": TestResult.attempted_at,
            "score": TestResult.score,
            "percentage": TestResult.percentage,
            "time_taken_seconds": TestResult.time_taken_seconds,
            "test_name": TestResult.test_name,
        }.get(sort_by, TestResult.attempted_at)

        if sort_dir.lower() == "asc":
            query = query.order_by(order_target)
        else:
            query = query.order_by(desc(order_target))

        results = query.offset(skip).limit(limit).all()

        return {
            "results": [TestResultResponse.model_validate(r) for r in results],
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    @staticmethod
    def get_recent_activity(db: Session, user_id: str, limit: int = 5) -> List[dict]:
        """Get recent test activity for the profile timeline."""
        results = db.query(TestResult).filter(
            TestResult.user_id == user_id
        ).order_by(desc(TestResult.attempted_at)).limit(limit).all()

        return [
            {
                "id": r.id,
                "test_name": r.test_name,
                "percentage": r.percentage,
                "attempted_at": r.attempted_at.strftime("%Y-%m-%d %H:%M"),
            }
            for r in results
        ]

    @staticmethod
    def get_accuracy_trend(db: Session, user_id: str) -> List[dict]:
        """Get accuracy trend data for graphing."""
        results = db.query(TestResult).filter(
            TestResult.user_id == user_id
        ).order_by(TestResult.attempted_at).all()

        return [
            {
                "test_name": r.test_name,
                "accuracy": r.accuracy or r.percentage,
                "attempted_at": r.attempted_at.strftime("%Y-%m-%d"),
            }
            for r in results
        ]

    @staticmethod
    def get_strength_analysis(db: Session, user_id: str) -> dict:
        """Calculate strongest and weakest subject areas."""
        subject_stats = TestResultService.calculate_subject_performance(db, user_id)
        if not subject_stats:
            return {
                "strongest_subject": "-",
                "strongest_score": 0.0,
                "weakest_subject": "-",
                "weakest_score": 0.0,
                "top_subjects": [],
                "bottom_subjects": [],
            }

        top_subjects = sorted(subject_stats, key=lambda s: s.average_percentage, reverse=True)[:3]
        bottom_subjects = sorted(subject_stats, key=lambda s: s.average_percentage)[:3]

        strongest = top_subjects[0]
        weakest = bottom_subjects[0]

        return {
            "strongest_subject": strongest.subject,
            "strongest_score": strongest.average_percentage,
            "weakest_subject": weakest.subject,
            "weakest_score": weakest.average_percentage,
            "top_subjects": [s for s in top_subjects],
            "bottom_subjects": [s for s in bottom_subjects],
        }

    @staticmethod
    def get_test_results_count(db: Session, user_id: str) -> int:
        """Get total count of test results for a user."""
        return db.query(func.count(TestResult.id)).filter(
            TestResult.user_id == user_id
        ).scalar() or 0

    @staticmethod
    def get_complete_profile(db: Session, user_id: str) -> dict:
        """Return profile identity plus analytics in the requested API shape."""
        from backend.auth import User

        user = db.query(User).filter(User.id == user_id).first()
        overview = TestResultService.get_profile_overview(db, user_id)
        strength = TestResultService.get_strength_analysis(db, user_id)
        return {
            "id": user.id if user else user_id,
            "fullName": user.full_name if user else "",
            "email": user.email if user else "",
            "registrationDate": user.created_at.isoformat() if user and user.created_at else None,
            "totalTestsAttempted": overview["total_tests"],
            "averageScore": overview["average_score"],
            "highestScore": overview["best_score"],
            "lowestScore": overview["lowest_score"],
            "overallAccuracy": overview["accuracy"],
            "strongestSubject": strength["strongest_subject"],
            "weakestSubject": strength["weakest_subject"],
            "recentTests": TestResultService.get_recent_activity(db, user_id, limit=5),
            "performanceTrend": TestResultService.get_progress_data(db, user_id),
            "subjectPerformance": TestResultService.calculate_subject_performance(db, user_id),
        }

    @staticmethod
    def get_dashboard(db: Session, user_id: str) -> dict:
        """Return dashboard analytics in a chart-ready camelCase shape."""
        overview = TestResultService.get_profile_overview(db, user_id)
        strength = TestResultService.get_strength_analysis(db, user_id)
        recent_tests = TestResultService.get_test_results(db, user_id, skip=0, limit=5)
        trend = TestResultService.get_progress_data(db, user_id)
        latest_score = trend[-1]["percentage"] if trend else 0.0
        improvement = 0.0
        if len(trend) >= 2:
            improvement = round(latest_score - trend[-2]["percentage"], 2)

        return {
            "totalTests": overview["total_tests"],
            "averageScore": overview["average_score"],
            "highestScore": overview["best_score"],
            "lowestScore": overview["lowest_score"],
            "overallAccuracy": overview["accuracy"],
            "strongestSubject": strength["strongest_subject"],
            "weakestSubject": strength["weakest_subject"],
            "latestScore": latest_score,
            "improvementPercentage": improvement,
            "recentTests": recent_tests,
            "performanceTrend": trend,
            "subjectPerformance": TestResultService.calculate_subject_performance(db, user_id),
        }
