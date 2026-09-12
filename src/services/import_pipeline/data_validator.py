"""
========================================================================
DRENAET-RH — DataValidator
========================================================================
Validation ligne par ligne des données prêtes à être importées.

Après ColumnMapper, chaque row est un dict {champ_canonique: valeur_brute}.
Le DataValidator :
1. NORMALISE les valeurs (dates en date Python, matricule en majuscules, sexe M/F...)
2. VALIDE les règles métier (dates cohérentes, formats, valeurs autorisées)
3. RETOURNE un tuple (valid_row, errors) pour chaque ligne

Résultat :
- Si valid_row est retourné → prêt pour MergeStrategy
- Si errors non vide → ligne rejetée + raisons

Le validator ne LÈVE PAS d'exception : il collecte les erreurs et
retourne un rapport. Le pipeline continue à traiter les autres lignes.
"""

import re
from datetime import date, datetime
from typing import Dict, Any, List, Tuple, Optional


# ========================================================================
# CONSTANTES DE VALIDATION
# ========================================================================
SEXES_VALIDES = {"M", "F"}

# Alias reconnus pour normaliser le sexe
SEXE_ALIASES = {
    "M": "M", "MASCULIN": "M", "MALE": "M", "H": "M", "HOMME": "M",
    "F": "F", "FEMININ": "F", "FÉMININ": "F", "FEMALE": "F", "FEMME": "F",
}

# Situations matrimoniales acceptées (avec normalisation)
SITUATIONS_MATRIMONIALES = {
    "CELIBATAIRE": "Célibataire",
    "CÉLIBATAIRE": "Célibataire",
    "MARIE": "Marié(e)",
    "MARIÉ": "Marié(e)",
    "MARIEE": "Marié(e)",
    "MARIÉE": "Marié(e)",
    "MARIE(E)": "Marié(e)",
    "MARIÉ(E)": "Marié(e)",
    "DIVORCE": "Divorcé(e)",
    "DIVORCÉ": "Divorcé(e)",
    "DIVORCEE": "Divorcé(e)",
    "DIVORCÉE": "Divorcé(e)",
    "VEUF": "Veuf(ve)",
    "VEUVE": "Veuf(ve)",
    "VEUF(VE)": "Veuf(ve)",
}

STATUTS_VALIDES = {"Actif", "Inactif", "En congé", "Muté", "Retraité"}
STATUT_ALIASES = {
    "ACTIF": "Actif", "ACTIVE": "Actif", "EN SERVICE": "Actif",
    "INACTIF": "Inactif", "INACTIVE": "Inactif",
    "EN CONGE": "En congé", "EN CONGÉ": "En congé", "CONGE": "En congé",
    "MUTE": "Muté", "MUTÉ": "Muté", "MUTEE": "Muté", "MUTÉE": "Muté",
    "RETRAITE": "Retraité", "RETRAITÉ": "Retraité", "RETRAITEE": "Retraité",
}

# Formats de matricule acceptés (regex flexible)
# Ex : "233329C", "12345", "M-2023-045", "IPP-001"
MATRICULE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9\-_/]{1,19}$", re.IGNORECASE)


# ========================================================================
# EXCEPTION INTERNE (utilisée pour flow de validation)
# ========================================================================
class FieldValidationError(Exception):
    """Erreur de validation sur un champ précis."""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


# ========================================================================
class DataValidator:
    """Validateur des données d'un agent."""

    def __init__(
        self,
        required_fields: List[str] = None,
        strict_matricule_format: bool = False,
    ):
        """
        Args:
            required_fields: liste des champs OBLIGATOIRES.
                Par défaut : matricule, nom, prenoms, sexe, emploi, structure
            strict_matricule_format: si True, applique MATRICULE_PATTERN.
                Sinon, accepte tout matricule non vide.
        """
        self.required_fields = required_fields or [
            "matricule", "nom", "prenoms", "sexe", "emploi", "structure"
        ]
        self.strict_matricule_format = strict_matricule_format

    # ====================================================================
    def validate_row(
        self,
        row: Dict[str, Any],
    ) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        """
        Valide et normalise une row.

        Args:
            row: dict {champ_canonique: valeur_brute}

        Returns:
            (row_normalisée, liste_erreurs)
            Si des erreurs : row_normalisée = None
            Sinon : row_normalisée avec toutes les valeurs propres
        """
        errors: List[str] = []
        cleaned: Dict[str, Any] = {"_row_number": row.get("_row_number")}

        # 1. Valider et normaliser CHAQUE champ
        for field, value in row.items():
            if field.startswith("_"):
                continue

            try:
                cleaned_value = self._validate_field(field, value)
                cleaned[field] = cleaned_value
            except FieldValidationError as e:
                errors.append(str(e))

        # 2. Vérifier les champs obligatoires
        for field in self.required_fields:
            val = cleaned.get(field)
            if val is None or val == "":
                errors.append(f"{field}: champ obligatoire manquant")

        # 3. Validations croisées (relations entre champs)
        cross_errors = self._validate_cross_fields(cleaned)
        errors.extend(cross_errors)

        if errors:
            return None, errors
        return cleaned, []

    # ====================================================================
    def _validate_field(self, field: str, value: Any) -> Any:
        """Valide et normalise UN champ. Lève FieldValidationError si erreur."""
        # Si vide → laisser tel quel (les obligatoires sont vérifiés après)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None

        # Dispatch par champ
        if field == "matricule":
            return self._validate_matricule(value)
        if field == "nom":
            return self._validate_nom(value)
        if field == "prenoms":
            return self._validate_prenoms(value)
        if field == "sexe":
            return self._validate_sexe(value)
        if field in ("date_naissance", "date_prise_service", "date_affectation"):
            return self._validate_date(field, value)
        if field == "telephone":
            return self._validate_telephone(value)
        if field == "email":
            return self._validate_email(value)
        if field == "situation_matrimoniale":
            return self._normalize_situation_matrimoniale(value)
        if field == "statut":
            return self._normalize_statut(value)

        # Autres champs : juste trim si string
        if isinstance(value, str):
            return value.strip()
        return value

    # ====================================================================
    # VALIDATEURS SPÉCIFIQUES
    # ====================================================================
    def _validate_matricule(self, value: Any) -> str:
        """Matricule : trim + majuscules + format (optionnel)."""
        s = str(value).strip().upper()
        if not s:
            raise FieldValidationError("matricule", "vide")

        # Retirer les espaces internes
        s = re.sub(r"\s+", "", s)

        if self.strict_matricule_format:
            if not MATRICULE_PATTERN.match(s):
                raise FieldValidationError(
                    "matricule",
                    f"format invalide '{s}' (attendu : lettres, chiffres, tirets)"
                )
        return s

    def _validate_nom(self, value: Any) -> str:
        """Nom : trim + majuscules."""
        s = str(value).strip()
        if not s:
            raise FieldValidationError("nom", "vide")
        return s.upper()

    def _validate_prenoms(self, value: Any) -> str:
        """Prénoms : trim + Title Case."""
        s = str(value).strip()
        if not s:
            raise FieldValidationError("prenoms", "vide")
        # Title Case en gérant les prénoms composés ("jean-paul" → "Jean-Paul")
        parts = re.split(r"([-\s])", s)
        return "".join(p.capitalize() for p in parts)

    def _validate_sexe(self, value: Any) -> str:
        """Sexe : normalise vers 'M' ou 'F'."""
        s = str(value).strip().upper()
        if s in SEXE_ALIASES:
            return SEXE_ALIASES[s]
        raise FieldValidationError(
            "sexe",
            f"valeur '{value}' non reconnue (attendu : M ou F)"
        )

    def _validate_date(self, field: str, value: Any) -> date:
        """Convertit vers un objet date Python."""
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()

        # String : essayer plusieurs formats français
        if isinstance(value, str):
            s = value.strip()
            # Formats acceptés (du plus commun au plus rare)
            formats = [
                "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
                "%Y-%m-%d", "%Y/%m/%d",
                "%d/%m/%y", "%d-%m-%y",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(s, fmt).date()
                except ValueError:
                    continue
            raise FieldValidationError(
                field,
                f"date invalide '{value}' (formats acceptés : JJ/MM/AAAA, JJ-MM-AAAA, AAAA-MM-JJ)"
            )

        raise FieldValidationError(field, f"type inattendu {type(value).__name__}")

    def _validate_telephone(self, value: Any) -> str:
        """Téléphone : conservation du format d'origine, juste trim."""
        s = str(value).strip()
        # Nettoyer les caractères parasites courants
        s = re.sub(r"[^\d\s+\-().]", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s if s else None

    def _validate_email(self, value: Any) -> str:
        """Email : format basique."""
        s = str(value).strip().lower()
        if not s:
            return None
        # Regex email basique (pas parfaite mais suffisante)
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", s):
            raise FieldValidationError(
                "email",
                f"format invalide '{value}'"
            )
        return s

    def _normalize_situation_matrimoniale(self, value: Any) -> str:
        """Normalise vers 'Célibataire' / 'Marié(e)' / 'Divorcé(e)' / 'Veuf(ve)'."""
        s = str(value).strip().upper()
        if s in SITUATIONS_MATRIMONIALES:
            return SITUATIONS_MATRIMONIALES[s]
        # Si non reconnu, laisser tel quel (Title Case)
        return str(value).strip().title()

    def _normalize_statut(self, value: Any) -> str:
        """Normalise le statut vers une valeur canonique."""
        s = str(value).strip().upper()
        return STATUT_ALIASES.get(s, str(value).strip())

    # ====================================================================
    # VALIDATIONS CROISÉES
    # ====================================================================
    def _validate_cross_fields(self, row: Dict[str, Any]) -> List[str]:
        """Valide les relations entre plusieurs champs."""
        errors: List[str] = []

        # Cohérence des dates
        naissance = row.get("date_naissance")
        prise_service = row.get("date_prise_service")
        affectation = row.get("date_affectation")

        if naissance and prise_service and prise_service <= naissance:
            errors.append(
                f"date_prise_service ({prise_service}) doit être postérieure à "
                f"date_naissance ({naissance})"
            )

        if prise_service and affectation and affectation < prise_service:
            errors.append(
                f"date_affectation ({affectation}) doit être postérieure ou "
                f"égale à date_prise_service ({prise_service})"
            )

        # Âge cohérent (entre 18 et 75 ans à la date d'aujourd'hui)
        if naissance:
            age = (date.today() - naissance).days // 365
            if age < 18:
                errors.append(f"date_naissance : agent âgé de {age} ans (min 18)")
            elif age > 75:
                errors.append(f"date_naissance : agent âgé de {age} ans (max 75)")

        return errors