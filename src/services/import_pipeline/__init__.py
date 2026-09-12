"""
DRENAET-RH — Pipeline d'import Excel

Exports principaux :
    from src.services.import_pipeline import (
        ImportService,      # orchestrateur principal
        ExcelReader,        # lecture Excel
        ColumnMapper,       # mapping colonnes
        DataValidator,      # validation
        MergeStrategy, Strategy,  # stratégies de merge
    )
"""

from src.services.import_pipeline.excel_reader import ExcelReader
from src.services.import_pipeline.column_mapper import ColumnMapper
from src.services.import_pipeline.data_validator import DataValidator
from src.services.import_pipeline.merge_strategy import (
    MergeStrategy, Strategy, Action, MergeDecision,
)
from src.services.import_pipeline.import_service import (
    ImportService, ImportPreviewReport, ImportExecutionReport,
)

__all__ = [
    "ExcelReader",
    "ColumnMapper",
    "DataValidator",
    "MergeStrategy", "Strategy", "Action", "MergeDecision",
    "ImportService", "ImportPreviewReport", "ImportExecutionReport",
]