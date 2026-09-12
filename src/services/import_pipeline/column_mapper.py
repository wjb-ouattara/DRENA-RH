"""
========================================================================
DRENAET-RH — ColumnMapper
========================================================================
Mapping intelligent des colonnes Excel vers les champs de la BD.

Problème résolu : chaque établissement peut nommer ses colonnes
différemment. Exemples :
- "Matricule", "N° Matricule", "MAT", "N°Mat", "Numéro matricule"
- "Téléphone", "Tél", "Cellulaire", "Portable"
- "Date de naissance", "DDN", "Date naissance"

Le ColumnMapper :
1. Reconnaît automatiquement les colonnes via des synonymes (auto_map)
2. Signale les colonnes obligatoires manquantes
3. Signale les colonnes non reconnues (l'UI proposera un mapping manuel)
4. Applique le mapping pour transformer une row Excel → dict standardisé

Normalisation : les comparaisons sont insensibles à la casse, aux accents,
aux espaces multiples et à la ponctuation.
"""

import unicodedata
import re
from typing import Dict, List, Any, Set, Tuple


# ========================================================================
# DICTIONNAIRE DE MAPPING PAR DÉFAUT
# ========================================================================
# Chaque clé = nom canonique du champ dans la BD
# Chaque valeur = liste de variantes possibles (synonymes)
# Ces variantes seront normalisées pour comparaison
DEFAULT_MAPPING = {
    # ── Identité (matricule = OBLIGATOIRE) ────────────────────────────
    "matricule": [
        "Matricule", "N° Matricule", "MAT", "N°Mat",
        "Numéro matricule", "Numero matricule", "Numero de matricule",
        "Num matricule", "Mat.", "N° Mat", "IM", "ID Agent",
    ],
    "nom": [
        "Nom", "NOM", "Nom de famille", "Patronyme", "Last name", "Surname",
    ],
    "prenoms": [
        "Prénoms", "Prenoms", "PRENOMS", "Prénom", "Prenom",
        "First name", "Given name",
    ],
    # Colonne combinée "Nom & Prénoms" - géré comme cas spécial
    "nom_prenoms": [
        "Nom et Prénoms", "Nom & Prénoms", "Nom et prenoms",
        "Nom Prénoms", "Nom Prenom", "Nom complet",
        "NOM ET PRENOMS",
    ],
    "sexe": [
        "Sexe", "Genre", "SEXE", "GENRE", "Sex", "M/F", "H/F", "F/M",
    ],
    "date_naissance": [
        "Date de naissance", "Date naissance", "DDN", "DateNaissance",
        "Née le", "Né le", "Date de naiss.", "DOB",
    ],
    "lieu_naissance": [
        "Lieu de naissance", "Lieu naissance", "Ville naissance",
        "Née à", "Né à", "POB",
    ],
    "situation_matrimoniale": [
        "Situation matrimoniale", "Situation", "Statut matrimonial",
        "État civil", "Etat civil", "Matrimoniale",
    ],

    # ── Contact ───────────────────────────────────────────────────────
    "telephone": [
        "Téléphone", "Telephone", "Tel", "Tél", "Tél.",
        "Cellulaire", "Portable", "Contact", "N° Téléphone",
        "Mobile", "Phone",
    ],
    "email": [
        "Email", "E-mail", "Mail", "Adresse email", "Courriel",
        "E mail", "Adresse mail",
    ],
    "residence": [
        "Résidence", "Residence", "Résidence administrative",
        "Ville", "Adresse", "Domicile", "Localité",
    ],

    # ── Carrière (emploi, structure = OBLIGATOIRES) ───────────────────
    "emploi": [
        "Emploi", "EMPLOI", "Poste", "Corps", "Fonction publique",
        "Job title", "Position",
    ],
    "grade": [
        "Grade", "GRADE", "Catégorie", "Categorie", "Échelle", "Echelle",
        "Classement",
    ],
    "fonction": [
        "Fonction", "FONCTION", "Fonction actuelle", "Poste actuel",
        "Titre", "Titre poste",
    ],

    # Structure - plusieurs synonymes courants dans les Excel DRENAET
    "structure": [
        "Structure", "STRUCTURE", "Établissement", "Etablissement",
        "École", "Ecole", "IEPP", "CAFOP", "Circonscription",
        "Affectation", "Service", "Direction", "Lieu de service",
        "Rattachement",
    ],
    "structure_type": [
        "Type structure", "Type d'établissement", "Type", "Nature",
        "Catégorie structure",
    ],
    "structure_localite": [
        "Localité", "Localite", "Ville structure", "Commune",
    ],

    "date_prise_service": [
        "Date de prise de service", "Date prise service",
        "Prise de service", "Date d'entrée", "Entrée en fonction",
        "Date embauche", "Date recrutement",
    ],
    "date_affectation": [
        "Date d'affectation", "Date affectation",
        "Affectation actuelle", "Date poste actuel",
    ],
    "statut": [
        "Statut", "STATUT", "État", "Etat", "Situation",
        "Actif/Inactif", "Status",
    ],
}


# Champs obligatoires (le mapping doit les résoudre, sinon erreur)
CHAMPS_OBLIGATOIRES = {
    "matricule", "nom", "prenoms", "sexe", "emploi", "structure",
}

# Colonne "nom_prenoms" est un cas spécial : si présente, elle résout
# nom + prénoms en même temps (via split au moment de la validation)
CHAMPS_SUBSTITUTS = {
    "nom_prenoms": {"nom", "prenoms"},
}


# ========================================================================
# UTILITAIRES DE NORMALISATION
# ========================================================================
def _normalize(text: str) -> str:
    """
    Normalise un texte pour comparaison de colonnes.

    Étapes :
    1. Supprime les accents (é → e, à → a, ç → c...)
    2. Passe en minuscules
    3. Supprime la ponctuation
    4. Réduit les espaces multiples à un seul
    5. Trim

    Exemples :
        "N°  Matricule "  → "n matricule"
        "Téléphone"       → "telephone"
        "Prénoms/Prenoms" → "prenoms prenoms"
    """
    if not text:
        return ""

    # 1. Supprime les accents (NFD = décompose)
    normalized = unicodedata.normalize("NFD", str(text))
    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Mn")

    # 2. Minuscules
    normalized = normalized.lower()

    # 3. Remplace ponctuation et caractères spéciaux par espace
    normalized = re.sub(r"[^\w\s]", " ", normalized)

    # 4. Espaces multiples → un seul
    normalized = re.sub(r"\s+", " ", normalized)

    # 5. Trim
    return normalized.strip()


# ========================================================================
class ColumnMapper:
    """Mappe les colonnes Excel vers les champs canoniques de la BD."""

    def __init__(self, custom_mapping: Dict[str, List[str]] = None):
        """
        Args:
            custom_mapping: mapping personnalisé (fusionné avec DEFAULT_MAPPING).
                Format : {"champ_canonique": ["Variante 1", "Variante 2", ...]}
        """
        self.mapping = dict(DEFAULT_MAPPING)
        if custom_mapping:
            for k, v in custom_mapping.items():
                if k in self.mapping:
                    # Fusionner en évitant les doublons
                    existing = set(self.mapping[k])
                    self.mapping[k] = self.mapping[k] + [
                        x for x in v if x not in existing
                    ]
                else:
                    self.mapping[k] = list(v)

        # Index normalisé pour recherche rapide
        # Format : {"variante_normalisée": "champ_canonique"}
        self._reverse_index = {}
        for canonical, variantes in self.mapping.items():
            for variante in variantes:
                self._reverse_index[_normalize(variante)] = canonical

    # ====================================================================
    def auto_map(self, excel_headers: List[str]) -> Dict[str, Any]:
        """
        Mappe automatiquement les colonnes Excel vers les champs canoniques.

        Args:
            excel_headers: liste des noms de colonnes lus dans l'Excel

        Returns:
            dict avec 4 clés :
            - "mapping" : {champ_canonique: nom_colonne_excel}
            - "unmapped_excel_columns" : colonnes Excel non reconnues
            - "missing_required_fields" : champs obligatoires non trouvés
            - "warnings" : messages d'avertissement (colonnes ambiguës...)
        """
        mapping: Dict[str, str] = {}
        unmapped: List[str] = []
        warnings: List[str] = []

        for header in excel_headers:
            # Skip les colonnes techniques (générées par ExcelReader pour cellules vides)
            if header.startswith("_col_") or header.startswith("_row_"):
                continue

            normalized = _normalize(header)
            if not normalized:
                continue

            canonical = self._reverse_index.get(normalized)

            if canonical:
                # Colonne reconnue
                if canonical in mapping:
                    # Conflit : 2 colonnes Excel pointent vers le même champ
                    warnings.append(
                        f"Conflit : les colonnes '{mapping[canonical]}' et '{header}' "
                        f"pointent toutes les 2 vers le champ '{canonical}'. "
                        f"Utilisation de '{header}'."
                    )
                mapping[canonical] = header
            else:
                # Colonne non reconnue
                unmapped.append(header)

        # Résoudre les substituts (ex: "nom_prenoms" fournit "nom" + "prenoms")
        for substitut, fournit in CHAMPS_SUBSTITUTS.items():
            if substitut in mapping:
                for champ in fournit:
                    if champ not in mapping:
                        # Marquer comme "fourni par substitut"
                        mapping[champ] = f"__SUBSTITUT__{substitut}"

        # Détecter les champs obligatoires manquants
        missing = [
            champ for champ in CHAMPS_OBLIGATOIRES
            if champ not in mapping
        ]

        return {
            "mapping": mapping,
            "unmapped_excel_columns": unmapped,
            "missing_required_fields": missing,
            "warnings": warnings,
        }

    # ====================================================================
    def apply_mapping(
        self,
        row: Dict[str, Any],
        mapping: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Applique un mapping à une row Excel pour produire un dict standardisé.

        Args:
            row: row lue par ExcelReader (dict avec noms Excel comme clés)
            mapping: dict {champ_canonique: nom_colonne_excel}

        Returns:
            dict {champ_canonique: valeur}
            + "_row_number" préservé
        """
        result = {"_row_number": row.get("_row_number")}

        for canonical, excel_col in mapping.items():
            # Cas spécial : substitut (nom_prenoms → nom + prenoms)
            if isinstance(excel_col, str) and excel_col.startswith("__SUBSTITUT__"):
                substitut_key = excel_col.replace("__SUBSTITUT__", "")
                if substitut_key == "nom_prenoms":
                    combined = mapping.get("nom_prenoms")
                    if combined and combined in row:
                        nom, prenoms = self._split_nom_prenoms(row[combined])
                        if canonical == "nom":
                            result["nom"] = nom
                        elif canonical == "prenoms":
                            result["prenoms"] = prenoms
                continue

            # Cas normal
            if excel_col in row:
                result[canonical] = row[excel_col]

        return result

    # ====================================================================
    def _split_nom_prenoms(self, full_name: str) -> Tuple[str, str]:
        """
        Sépare 'Nom & Prénoms' en (nom, prénoms).

        Convention DRENAET : le premier mot en MAJUSCULES est le nom,
        le reste (première lettre uniquement en majuscule) est les prénoms.

        Exemples :
            "BABO Assomane David"       → ("BABO", "Assomane David")
            "OUATTARA Aminata Marie"    → ("OUATTARA", "Aminata Marie")
            "TRAORE Ibrahim"            → ("TRAORE", "Ibrahim")

        Si pas de majuscules détectables : premier mot = nom, reste = prénoms.
        """
        if not full_name:
            return "", ""

        parts = str(full_name).strip().split()
        if len(parts) == 0:
            return "", ""
        if len(parts) == 1:
            return parts[0].upper(), ""

        # Détection des mots en MAJUSCULES au début
        nom_parts = []
        prenoms_parts = []
        for i, word in enumerate(parts):
            if i == 0 or (word.isupper() and not prenoms_parts):
                nom_parts.append(word)
            else:
                prenoms_parts.append(word)

        nom = " ".join(nom_parts).upper()
        prenoms = " ".join(prenoms_parts).title() if prenoms_parts else ""
        return nom, prenoms

    # ====================================================================
    def get_all_canonical_fields(self) -> List[str]:
        """Retourne la liste de tous les champs canoniques disponibles."""
        return list(self.mapping.keys())

    def get_variants(self, canonical: str) -> List[str]:
        """Retourne toutes les variantes acceptées pour un champ canonique."""
        return list(self.mapping.get(canonical, []))