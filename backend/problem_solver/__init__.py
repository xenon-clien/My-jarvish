"""JARVIS AI Universal PC Problem Solver & Advanced Diagnostic Engine."""
from backend.problem_solver.models import (
    ProblemCategory, DiagnosticStatus, RiskLevel,
    DiagnosticItem, DiagnosticReport, RootCauseHypothesis,
    RootCauseAnalysis, RepairStep, RepairPlan,
    VerificationResult, SnapshotData, RepairHistoryEntry
)
from backend.problem_solver.safety import CommandSafetyEngine
from backend.problem_solver.system_health import SystemHealthEngine
from backend.problem_solver.root_cause_engine import RootCauseEngine
from backend.problem_solver.repair_planner import RepairPlanner
from backend.problem_solver.repair_executor import RepairExecutor
from backend.problem_solver.repair_verifier import RepairVerifier
from backend.problem_solver.rollback_manager import RollbackManager
from backend.problem_solver.history import RepairHistory
from backend.problem_solver.problem_solver_engine import ProblemSolverEngine, problem_solver_engine

__all__ = [
    "ProblemCategory", "DiagnosticStatus", "RiskLevel",
    "DiagnosticItem", "DiagnosticReport", "RootCauseHypothesis",
    "RootCauseAnalysis", "RepairStep", "RepairPlan",
    "VerificationResult", "SnapshotData", "RepairHistoryEntry",
    "CommandSafetyEngine", "SystemHealthEngine", "RootCauseEngine",
    "RepairPlanner", "RepairExecutor", "RepairVerifier",
    "RollbackManager", "RepairHistory", "ProblemSolverEngine",
    "problem_solver_engine"
]
