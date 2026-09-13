"""
========================================================================
Template : Attestation de Travail (v2 — fidèle au modèle officiel)
========================================================================
Améliorations v2 :
- Préambule "Madame/Monsieur" adapté au sexe de l'agent
- Nom du Directeur Régional depuis settings.DRENAET_INFO
- Phrase officielle "Où il/elle assure régulièrement ses fonctions..."
- Footer officiel DRENAET (BP, Tél, Email)
"""

from datetime import date, datetime
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

from config import settings
from src.services.document_generator import DocumentTemplate


def _format_date_short(d) -> str:
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


def _titre_civil(sexe: str, sit_matrimoniale: str = "") -> str:
    """Détermine 'Madame' ou 'Monsieur' selon le sexe."""
    if (sexe or "").upper() == "F":
        return "Madame"
    return "Monsieur"


def _pronom(sexe: str) -> str:
    """Détermine 'il' ou 'elle' selon le sexe."""
    if (sexe or "").upper() == "F":
        return "elle"
    return "il"


# ========================================================================
# TEMPLATE PRINCIPAL
# ========================================================================
class AttestationTravailTemplate(DocumentTemplate):
    """Template d'Attestation de Travail."""

    type_document = "attestation_travail"
    titre_document = "ATTESTATION DE TRAVAIL"
    dossier_sortie = "attestations_travail"
    destinataire = []

    # ====================================================================
    def build_body(self, context: dict, styles: dict) -> list:
        """Construit le corps de l'attestation."""
        agent = context["agent"]
        params = context["parameters"]
        info = settings.DRENAET_INFO

        elements = []

        # ----- Préambule -----
        directeur_nom = info.get("directeur_regional_nom", "Monsieur le Directeur Régional")

        elements.append(Paragraph(
            f"<b>Le Directeur Régional de l'Éducation Nationale, "
            f"de l'Alphabétisation et de l'Enseignement Technique de Katiola, "
            f"soussigné {directeur_nom}, atteste par la présente que,</b>",
            styles["body"]
        ))
        elements.append(Spacer(1, 0.3 * cm))

        # ----- Infos agent (avec civilité Madame/Monsieur) -----
        titre = _titre_civil(agent["sexe"], agent["situation_matrimoniale"])
        nom_complet = f"{agent['nom']} {agent['prenoms']}".strip().upper()

        agent_fields = [
            (titre, nom_complet),
            ("Matricule", agent["matricule"]),
            ("Emploi", agent["emploi"]),
            ("Grade", agent["grade"] or ""),
            ("Fonction", agent["fonction"] or ""),
            ("Est en service à", agent["structure"]),
        ]
        elements.append(self._render_info_table(agent_fields, styles))
        elements.append(Spacer(1, 0.3 * cm))

        # ----- Phrase certificative (genrée) -----
        pronom = _pronom(agent["sexe"])
        date_prise = agent["date_prise_service"]
        date_prise_str = _format_date_short(date_prise) if date_prise else ""

        elements.append(Paragraph(
            f"Où <b>{pronom}</b> assure régulièrement ses fonctions "
            f"depuis le <b>{date_prise_str}</b>.",
            styles["body"]
        ))
        elements.append(Spacer(1, 0.3 * cm))

        # ----- Formule de clôture officielle -----
        # Le modèle officiel de la DRENAET ne prévoit aucun « but » à
        # préciser : la formule est fermée et toujours identique.
        elements.append(Paragraph(
            "En foi de quoi, la présente attestation lui est délivrée pour "
            "servir et valoir ce que de droit.",
            styles["body"]
        ))

        return elements

    # ====================================================================
    def build_directeur_zone(self, context: dict, styles: dict) -> list:
        """Lieu, date + signataire."""
        elements = []
        today_str = _format_date_short(date.today())
        info = settings.DRENAET_INFO

        titre_signataire = info.get("directeur_regional_titre", "Directeur Régional")
        if info.get("directeur_par_procuration"):
            titre_signataire = f"{titre_signataire} P/O"

        right_style = ParagraphStyle(
            "right_aligned", fontName="Helvetica", fontSize=11,
            alignment=TA_RIGHT, leading=14, textColor=colors.HexColor("#000000"),
        )
        right_bold = ParagraphStyle(
            "right_bold", fontName="Helvetica-Bold", fontSize=11,
            alignment=TA_RIGHT, leading=14, textColor=colors.HexColor("#000000"),
        )

        dir_table = Table(
            [
                [Paragraph(f"Fait à Katiola, le {today_str}", right_style)],
                [Paragraph(f"<b>Le {titre_signataire}</b>", right_bold)],
            ],
            colWidths=[8.6 * cm],
        )
        dir_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(dir_table)
        return elements

    # ====================================================================
    def _render_info_table(self, fields: list, styles: dict) -> Table:
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