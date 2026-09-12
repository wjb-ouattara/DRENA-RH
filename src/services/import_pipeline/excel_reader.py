"""
========================================================================
DRENAET-RH — ExcelReader
========================================================================
Lecteur de fichiers Excel pour l'import du personnel.

Responsabilité UNIQUE : lire un fichier .xlsx et extraire les données
sous forme de listes/dictionnaires Python. Aucune logique métier.

Fonctionnalités :
- Détection auto de la ligne d'en-tête (skip des lignes vides / titres)
- Extraction de toutes les feuilles disponibles
- Conversion typée des valeurs (dates, nombres, strings)
- Gestion des cellules fusionnées

Utilise openpyxl (déjà dans requirements pour ReportLab).
"""

from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import hashlib

try:
    import openpyxl
    from openpyxl.utils import get_column_letter
except ImportError:
    raise ImportError(
        "openpyxl est requis. Installez-le avec : pip install openpyxl"
    )


# ========================================================================
# EXCEPTIONS
# ========================================================================
class ExcelReaderException(Exception):
    """Exception de base pour ExcelReader."""
    pass


class FichierIntrouvableError(ExcelReaderException):
    pass


class FichierInvalideError(ExcelReaderException):
    """Le fichier n'est pas un Excel valide."""
    pass


class FeuilleIntrouvableError(ExcelReaderException):
    pass


# ========================================================================
class ExcelReader:
    """Lecteur de fichiers Excel."""

    def __init__(self, file_path: str):
        """
        Args:
            file_path: chemin vers le fichier .xlsx

        Raises:
            FichierIntrouvableError: si le fichier n'existe pas
            FichierInvalideError: si le fichier n'est pas un Excel valide
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FichierIntrouvableError(
                f"Fichier introuvable : {file_path}"
            )

        try:
            # data_only=True → récupère les valeurs calculées des formules
            self.workbook = openpyxl.load_workbook(
                str(self.file_path),
                data_only=True,
                read_only=False,  # False pour supporter les cellules fusionnées
            )
        except Exception as e:
            raise FichierInvalideError(
                f"Impossible d'ouvrir le fichier Excel : {e}"
            ) from e

    # ====================================================================
    def get_sheet_names(self) -> List[str]:
        """Retourne la liste des noms de feuilles."""
        return self.workbook.sheetnames

    # ====================================================================
    def get_file_info(self) -> Dict[str, Any]:
        """Retourne les métadonnées du fichier."""
        stat = self.file_path.stat()
        return {
            "nom_fichier": self.file_path.name,
            "chemin": str(self.file_path.absolute()),
            "taille_octets": stat.st_size,
            "date_modification": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "hash_sha256": self._compute_file_hash(),
            "nb_feuilles": len(self.workbook.sheetnames),
            "feuilles": self.workbook.sheetnames,
        }

    def _compute_file_hash(self) -> str:
        """Calcule le hash SHA-256 du fichier (pour détecter re-imports)."""
        sha = hashlib.sha256()
        with open(self.file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()

    # ====================================================================
    def detect_header_row(
        self,
        sheet_name: str,
        max_scan_rows: int = 15,
        min_cols_filled: int = 3,
    ) -> Optional[int]:
        """
        Détecte automatiquement la ligne d'en-tête d'une feuille.

        Stratégie : scanne les N premières lignes, retourne la première
        ligne qui a au moins `min_cols_filled` cellules non-vides.

        Args:
            sheet_name: nom de la feuille
            max_scan_rows: nombre de lignes à scanner
            min_cols_filled: nb minimum de colonnes remplies pour être un header

        Returns:
            Numéro de ligne (1-indexed) ou None si non détecté
        """
        if sheet_name not in self.workbook.sheetnames:
            raise FeuilleIntrouvableError(
                f"Feuille '{sheet_name}' non trouvée. "
                f"Disponibles : {self.workbook.sheetnames}"
            )

        ws = self.workbook[sheet_name]
        max_row = min(max_scan_rows, ws.max_row)

        for r in range(1, max_row + 1):
            filled = sum(
                1 for c in range(1, ws.max_column + 1)
                if ws.cell(r, c).value not in (None, "")
            )
            if filled >= min_cols_filled:
                # Vérifier que la ligne suivante contient au moins 1 donnée non-header
                # (évite de prendre une ligne de titre isolée)
                if r + 1 <= ws.max_row:
                    next_row_filled = sum(
                        1 for c in range(1, ws.max_column + 1)
                        if ws.cell(r + 1, c).value not in (None, "")
                    )
                    if next_row_filled >= 1:
                        return r
        return None

    # ====================================================================
    def read_sheet(
        self,
        sheet_name: str,
        header_row: Optional[int] = None,
        skip_empty_rows: bool = True,
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Lit une feuille et retourne (headers, rows).

        Args:
            sheet_name: nom de la feuille
            header_row: ligne d'en-tête (1-indexed). Si None, détection auto.
            skip_empty_rows: ignorer les lignes complètement vides

        Returns:
            (headers, rows) où :
            - headers = liste des noms de colonnes tels quels dans l'Excel
            - rows = liste de dict {header_name: value, "_row_number": N}

        Chaque row inclut "_row_number" (numéro de ligne réel dans Excel)
        pour permettre au reste du pipeline de référencer les erreurs.
        """
        if sheet_name not in self.workbook.sheetnames:
            raise FeuilleIntrouvableError(
                f"Feuille '{sheet_name}' non trouvée."
            )

        ws = self.workbook[sheet_name]

        # Détection auto si header_row non fourni
        if header_row is None:
            header_row = self.detect_header_row(sheet_name)
            if header_row is None:
                raise ExcelReaderException(
                    f"Impossible de détecter la ligne d'en-tête dans '{sheet_name}'. "
                    f"Spécifiez header_row manuellement."
                )

        # Lire les headers
        headers = []
        for c in range(1, ws.max_column + 1):
            v = ws.cell(header_row, c).value
            # Normaliser (retirer espaces multiples, trim)
            if v is None:
                headers.append(f"_col_{get_column_letter(c)}")
            else:
                headers.append(str(v).strip())

        # Lire les data rows
        rows = []
        for r in range(header_row + 1, ws.max_row + 1):
            row_dict = {"_row_number": r}
            is_empty = True

            for c in range(1, ws.max_column + 1):
                value = ws.cell(r, c).value
                header = headers[c - 1]

                # Conversion / nettoyage des valeurs
                cleaned = self._clean_value(value)
                row_dict[header] = cleaned

                if cleaned not in (None, ""):
                    is_empty = False

            if not is_empty or not skip_empty_rows:
                rows.append(row_dict)

        return headers, rows

    # ====================================================================
    def _clean_value(self, value: Any) -> Any:
        """Nettoie une valeur brute d'Excel."""
        if value is None:
            return None
        # Datetime → date si l'heure est 00:00:00
        if isinstance(value, datetime):
            if value.hour == 0 and value.minute == 0 and value.second == 0:
                return value.date()
            return value
        # Strings : trim + gestion NaN string
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed == "" or trimmed.lower() in ("nan", "null", "n/a"):
                return None
            return trimmed
        return value

    # ====================================================================
    def preview_sheet(
        self,
        sheet_name: str,
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """
        Aperçu rapide d'une feuille (pour l'UI de sélection).

        Returns:
            {
                "sheet_name": str,
                "detected_header_row": int,
                "headers": [str],
                "sample_rows": [dict],  # 5 premières lignes
                "estimated_total_rows": int,
            }
        """
        header_row = self.detect_header_row(sheet_name)
        headers, rows = self.read_sheet(sheet_name, header_row=header_row)

        return {
            "sheet_name": sheet_name,
            "detected_header_row": header_row,
            "headers": headers,
            "sample_rows": rows[:max_rows],
            "estimated_total_rows": len(rows),
        }

    # ====================================================================
    def close(self):
        """Ferme le workbook (libère les ressources)."""
        try:
            self.workbook.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()