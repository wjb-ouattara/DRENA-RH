"""
DRENAET-RH — Module Personnel (UI)

Expose la vue principale du module Personnel avec tous ses onglets.
"""

from src.ui.personnel.personnel_view import PersonnelView
from src.ui.personnel.personnel_list_view import PersonnelListView
from src.ui.personnel.personnel_form_dialog import PersonnelFormDialog
from src.ui.personnel.personnel_detail_dialog import PersonnelDetailDialog

__all__ = [
    "PersonnelView",
    "PersonnelListView",
    "PersonnelFormDialog",
    "PersonnelDetailDialog",
]