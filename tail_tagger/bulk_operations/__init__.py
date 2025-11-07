"""
Bulk operations module for applying tag changes across all images.

This module provides functionality for performing operations on all images
in a folder at once, bypassing the normal image-by-image workflow for performance.

Currently supports:
- Adding tags to all images (front or end position)
- Removing tags from all images
- Background thread execution with progress tracking
- Automatic backups before modifications
"""

from .manager import BulkOperationsManager
from .tag_operations_dialog import (
    TagBulkOperationDialog,
    BulkOperationWorker,
    WorkerSignals
)

__all__ = [
    'BulkOperationsManager',
    'TagBulkOperationDialog',
    'BulkOperationWorker',
    'WorkerSignals',
]
