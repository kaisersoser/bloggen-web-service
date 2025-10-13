"""
Core Audit Tracking Components

Refactored audit tracking system following our coding principles.
"""

from .enhanced_audit_tracker import EnhancedDatabaseAuditTracker
from .audit_session import AuditSession
from .database_worker import DatabaseWorker
from .database_manager import DatabaseConnectionManager
from .cost_calculator import CostCalculator

# Backward compatibility for legacy imports
RefactoredAuditTracker = EnhancedDatabaseAuditTracker

__all__ = [
    "EnhancedDatabaseAuditTracker",
    "RefactoredAuditTracker",  # Backward compatibility alias
    "AuditSession",
    "DatabaseWorker",
    "DatabaseConnectionManager",
    "CostCalculator",
]
