"""
========================================================================
Template : Demande d'Autorisation d'Absence (v2 — fidèle au modèle officiel)
========================================================================
Reproduit FIDÈLEMENT le format du document officiel DRENAET de Katiola.

Structure (de haut en bas) :
1. En-tête tri-colonne (Ministère / Armoirie / République + année scolaire)
2. N° de référence à gauche
3. Titre centré et souligné : "DEMANDE D'AUTORISATION D'ABSENCE"
4. Destinataire centré :
       A
       Monsieur le Directeur Régional de l'Éducation Nationale,
       de l'Alphabétisation et l'Enseignement Technique de Katiola
5. Tableau infos demandeur (M./Mme/Mlle, Matricule, Emploi, Fonction, Structure)
6. Phrase d'intro : "J'ai l'honneur de solliciter..."
7. Tableau détails (pour le, allant du, destination, motif)
8. Phrase intérim : "Pendant mon absence, l'intérim sera assuré par :"
9. Tableau infos intérimaire (idem demandeur)
10. Phrase de reprise : "A l'issue de mon autorisation d'absence, je reprendrai..."
11. Tableau signatures (Intéressé / Intérimaire / Décision DR avec cases Favorable/Défavorable)
12. Lieu, date + Le Directeur Régional (aligné à droite)
13. Ampliations (en bas à gauche)
"""

from datetime import date, datetime
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from src.services.document_generator import DocumentTemplate


# ========================================================================
# UTILITAIRES DE FORMATAGE
# ========================================================================
def _format_date_long(d) -> str:
    """Formate une date en 'jeudi 18 juin 2026'."""
    if not d:
        return ""
    if isinstance(d, str):
        try:
            d = datetime.fromisoformat(d).date()
        except (ValueError, TypeError):
            return d
    if not isinstance(d, (date, datetime)):
        return str(d)

    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    mois = ["janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    return f"{jours[d.weekday()]} {d.day} {mois[d.month - 1]} {d.year}"


def _format_date_short(d) -> str:
    """Formate une date en '18 juin 2026'."""
    if not d:
        return ""
    if isinstance(d, str):
        try:
            d = datetime.fromisoformat(d).date()
        except (ValueError, TypeError):
            return d
    if not isinstance(d, (date, datetime)):
        return str(d)

    mois = ["janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    return f"{d.day} {mois[d.month - 1]} {d.year}"


def _format_heure(h: str) -> str:
    """Convertit '07h30' → '07 heures 30 minutes'."""
    if not h:
        return ""
    h = str(h).strip().lower().replace("h", " heures ").replace(":", " heures ")
    if "minutes" not in h:
        h = h + " minutes"
    return h.replace("  ", " ").strip()


def _civilite(sexe: str, sit_matrimoniale: str = "") -> str:
    """Détermine la civilité M./Mme/Mlle."""
    if (sexe or "").upper() == "F":
        if "mar" in (sit_matrimoniale or "").lower() or "veuv" in (sit_matrimoniale or "").lower():
            return "Mme"
        return "Mlle"
    return "M."


# ========================================================================
# TEMPLATE PRINCIPAL
# ========================================================================
class AutorisationAbsenceTemplate(DocumentTemplate):
    """Template de la Demande d'Autorisation d'Absence."""

    type_document = "autorisation_absence"
    titre_document = "DEMANDE D'AUTORISATION D'ABSENCE"
    dossier_sortie = "autorisations"

    # Formule destinataire affichée sous le titre
    destinataire = [
        "A",
        "",
        "Monsieur le Directeur Régional de l'Éducation Nationale,",
        "de l'Alphabétisation et l'Enseignement Technique de Katiola",
    ]

    # ====================================================================
    def build_body(self, context: dict, styles: dict) -> list:
        """Construit le corps du document (entre destinataire et signatures)."""
        agent = context["agent"]
        params = context["parameters"]

        elements = []

        # ----- Tableau infos du demandeur -----
        civilite_agent = _civilite(agent["sexe"], agent["situation_matrimoniale"])
        nom_complet = f"{agent['nom']} {agent['prenoms']}".strip().upper()

        agent_fields = [
            ("M./Mme/Mlle", f"{civilite_agent}  {nom_complet}"),
            ("Matricule", agent["matricule"]),
            ("Emploi", agent["emploi"]),
            ("Fonction", agent["fonction"] or ""),
            ("Structure", agent["structure"]),
        ]
        elements.append(self._render_info_table(agent_fields, styles))
        elements.append(Spacer(1, 0.25 * cm))

        # ----- Phrase d'introduction -----
        elements.append(Paragraph(
            "J'ai l'honneur de solliciter de votre haute bienveillance "
            "une autorisation d'absence,",
            styles["body"]
        ))
        elements.append(Spacer(1, 0.2 * cm))

        # ----- Tableau détails de l'absence -----
        date_debut = params.get("date_debut")
        date_fin = params.get("date_fin")

        # "pour le" : si 1 seul jour (debut = fin), sinon "du..au.."
        if date_debut == date_fin and date_debut:
            pour_le = _format_date_long(date_debut)
            allant_du = ""
        else:
            pour_le = ""
            if date_debut and date_fin:
                allant_du = f"du {_format_date_short(date_debut)} au {_format_date_short(date_fin)}"
            else:
                allant_du = ""

        details_fields = [
            ("pour le", pour_le),
            ("allant du", allant_du),
            ("pour me rendre à", params.get("destination", "")),
            ("motif", params.get("motif", "")),
        ]
        elements.append(self._render_info_table(details_fields, styles))
        elements.append(Spacer(1, 0.25 * cm))

        # ----- Bloc intérimaire (si renseigné) -----
        interim = params.get("interim")
        if interim and interim.get("matricule"):
            elements.append(Paragraph(
                "Pendant mon absence, l'intérim sera assuré par :",
                styles["body"]
            ))
            elements.append(Spacer(1, 0.2 * cm))

            interim_civ = "M."  # par défaut
            interim_nom = (interim.get("nom_complet") or "").upper()
            interim_fields = [
                ("M./Mme/Mlle", f"{interim_civ}  {interim_nom}"),
                ("Matricule", interim.get("matricule", "")),
                ("Emploi", interim.get("emploi", "")),
                ("Fonction", interim.get("fonction", "") or ""),
                ("Structure", interim.get("structure", "")),
            ]
            elements.append(self._render_info_table(interim_fields, styles))
            elements.append(Spacer(1, 0.25 * cm))

        # ----- Phrase de reprise du service -----
        date_reprise = params.get("date_reprise")
        heure_reprise = params.get("heure_reprise", "07h30")
        date_reprise_long = _format_date_long(date_reprise)
        heure_long = _format_heure(heure_reprise)

        elements.append(Paragraph(
            f"À l'issue de mon autorisation d'absence, je reprendrai le service le "
            f"<b>{date_reprise_long}</b> à <b>{heure_long}</b>.",
            styles["body"]
        ))

        return elements

    # ====================================================================
    def build_signature_zone(self, context: dict, styles: dict) -> list:
        """
        Tableau 3 colonnes des signatures :
        | Signature intéressé(e) | Signature intérimaire | Décision Directeur Régional |
        |        (vide)          |       (vide)          |  Favorable ☐  Défavorable ☐ |
        """
        elements = []

        # Style cellules
        cell_label_style = ParagraphStyle(
            "sig_cell_label",
            fontName="Helvetica-Bold", fontSize=10,
            alignment=TA_CENTER, leading=13,
            textColor=colors.HexColor("#000000"),
        )
        cell_dec_style = ParagraphStyle(
            "sig_cell_dec",
            fontName="Helvetica", fontSize=9,
            alignment=TA_LEFT, leading=11,
            textColor=colors.HexColor("#000000"),
        )

        # Petite cellule = case à cocher (Table imbriquée avec bordure)
        case_style = TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#000000")),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
        case_fav = Table([[""]], colWidths=[0.35 * cm], rowHeights=[0.35 * cm])
        case_fav.setStyle(case_style)
        case_def = Table([[""]], colWidths=[0.35 * cm], rowHeights=[0.35 * cm])
        case_def.setStyle(case_style)

        # Décision DR : Favorable [ ] Défavorable [ ]
        decision_table = Table(
            [[
                Paragraph("Favorable", cell_dec_style),
                case_fav,
                Paragraph("Défavorable", cell_dec_style),
                case_def,
            ]],
            colWidths=[1.7 * cm, 0.45 * cm, 1.9 * cm, 0.45 * cm],
        )
        decision_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ]))

        # Ligne 1 : Titres
        # Ligne 2 : Contenu (vide pour signatures, cases pour Décision DR)
        sig_table = Table(
            [
                [
                    Paragraph("<b>Signature</b><br/><b>de l'intéressé(e)</b>", cell_label_style),
                    Paragraph("<b>Signature</b><br/><b>de l'intérimaire</b>", cell_label_style),
                    Paragraph("<b>Décision de Monsieur</b><br/><b>le Directeur Régional</b>", cell_label_style),
                ],
                [
                    "",  # zone signature intéressé (vide)
                    "",  # zone signature intérimaire (vide)
                    decision_table,
                ],
            ],
            colWidths=[4.8 * cm, 4.8 * cm, 7.4 * cm],
            rowHeights=[1.0 * cm, 1.7 * cm],
        )
        sig_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1.0, colors.HexColor("#000000")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#000000")),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("VALIGN", (0, 1), (-1, 1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(sig_table)
        return elements

    # ====================================================================
    def build_directeur_zone(self, context: dict, styles: dict) -> list:
        """
        Lieu, date + Le Directeur Régional (en bas à droite).
        Style :
                                                Katiola, le 24 juin 2026
                                                Le Directeur Régional
        """
        elements = []

        # Date d'aujourd'hui en français
        today_str = _format_date_short(date.today())

        # Style aligné à droite
        right_style = ParagraphStyle(
            "right_aligned",
            fontName="Helvetica", fontSize=11,
            alignment=TA_RIGHT, leading=14,
            textColor=colors.HexColor("#000000"),
        )
        right_bold = ParagraphStyle(
            "right_bold",
            fontName="Helvetica-Bold", fontSize=11,
            alignment=TA_RIGHT, leading=14,
            textColor=colors.HexColor("#000000"),
        )

        # Tableau positionnant la signature DR à droite
        dir_table = Table(
            [
                [Paragraph(f"Katiola, le {today_str}", right_style)],
                [Paragraph("<b>Le Directeur Régional</b>", right_bold)],
            ],
            colWidths=[8.6 * cm],
        )
        dir_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(dir_table)
        return elements

    # ====================================================================
    def build_ampliations(self, context: dict, styles: dict) -> list:
        """Bloc Ampliations en bas à gauche."""
        elements = []

        amp_title_style = ParagraphStyle(
            "amp_title",
            fontName="Helvetica-Bold", fontSize=10,
            alignment=TA_LEFT, leading=12,
            textColor=colors.HexColor("#000000"),
        )
        amp_item_style = ParagraphStyle(
            "amp_item",
            fontName="Helvetica", fontSize=10,
            alignment=TA_LEFT, leading=12,
            textColor=colors.HexColor("#000000"),
        )

        # Petit tableau positionné à gauche
        amp_table = Table(
            [
                [Paragraph("<u>Ampliations</u>", amp_title_style)],
                [Paragraph("L'intéressé(e) ............................. 1", amp_item_style)],
                [Paragraph("SRH/Archives ............................ 1", amp_item_style)],
            ],
            colWidths=[8 * cm],
        )
        amp_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        elements.append(amp_table)
        return elements

    # ====================================================================
    def _render_info_table(self, fields: list, styles: dict) -> Table:
        """
        Rend un tableau d'infos style "Label : Valeur" sans cadre visible.
        fields = [("Matricule", "233329C"), ...]
        """
        rows = []
        for label, value in fields:
            rows.append([
                Paragraph(label, styles["label"]),
                Paragraph(":", styles["label"]),
                Paragraph(f"<b>{value}</b>" if value else "", styles["value"]),
            ])

        tbl = Table(rows, colWidths=[4.5 * cm, 0.4 * cm, 12 * cm])
        tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return tbl