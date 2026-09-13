"""
========================================================================
Template : Titre de Congés
========================================================================
Document délivré pour autoriser un agent à prendre ses congés
sur une période donnée, avec une destination (lieu de villégiature).

Structure :
1. Préambule : "Le DR ... atteste être favorable au titre de congés que sollicite :"
2. Tableau infos agent
3. Phrase de période : "Sur la période du ... au ... inclus, pour se rendre à ..."
4. Phrase finale standard
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


def _titre_civil(sexe: str) -> str:
    return "Madame" if (sexe or "").upper() == "F" else "Monsieur"


# ========================================================================
class TitreCongesTemplate(DocumentTemplate):
    """Template du Titre de Congés."""

    type_document = "titre_conges"
    titre_document = "TITRE DE CONGÉS"
    dossier_sortie = "titres_conges"
    destinataire = []

    # ====================================================================
    def build_body(self, context: dict, styles: dict) -> list:
        agent = context["agent"]
        params = context["parameters"]
        info = settings.DRENAET_INFO

        elements = []

        # Préambule
        directeur_nom = info.get("directeur_regional_nom", "Monsieur le Directeur Régional")
        elements.append(Paragraph(
            f"<b>Le Directeur Régional de l'Éducation Nationale, "
            f"de l'Alphabétisation et de l'Enseignement Technique (DRENAET) de Katiola, "
            f"soussigné {directeur_nom}, atteste être favorable au titre "
            f"de congés que sollicite :</b>",
            styles["body"]
        ))
        elements.append(Spacer(1, 0.3 * cm))

        # Infos agent
        titre = _titre_civil(agent["sexe"])
        nom_complet = f"{agent['nom']} {agent['prenoms']}".strip().upper()

        agent_fields = [
            (titre, nom_complet),
            ("Matricule", agent["matricule"]),
            ("Emploi", agent["emploi"]),
            ("Fonction", agent["fonction"] or ""),
            ("Structure", agent["structure"]),
        ]
        elements.append(self._render_info_table(agent_fields, styles))
        elements.append(Spacer(1, 0.3 * cm))

        # Phrase de période + destination
        date_debut = params.get("date_debut")
        date_fin = params.get("date_fin")
        destination = params.get("destination", "")

        date_debut_str = _format_date_short(date_debut) if date_debut else ""
        date_fin_str = _format_date_short(date_fin) if date_fin else ""

        elements.append(Paragraph(
            f"Sur la période du <b>{date_debut_str}</b> "
            f"au <b>{date_fin_str}</b> inclus, "
            f"pour se rendre à <b>{destination}</b>.",
            styles["body"]
        ))
        elements.append(Spacer(1, 0.3 * cm))

        # Phrase finale
        elements.append(Paragraph(
            "En foi de quoi, le présent document lui est délivré pour servir "
            "et valoir ce que de droit.",
            styles["body"]
        ))

        return elements

    # ====================================================================
    def build_directeur_zone(self, context: dict, styles: dict) -> list:
        elements = []
        today_str = _format_date_short(date.today())
        info = settings.DRENAET_INFO
        titre_signataire = info.get("directeur_regional_titre", "Directeur Régional")
        if info.get("directeur_par_procuration"):
            titre_signataire = f"{titre_signataire} P/O"

        right_style = ParagraphStyle("right", fontName="Helvetica", fontSize=11,
            alignment=TA_RIGHT, leading=14, textColor=colors.HexColor("#000000"))
        right_bold = ParagraphStyle("right_b", fontName="Helvetica-Bold", fontSize=11,
            alignment=TA_RIGHT, leading=14, textColor=colors.HexColor("#000000"))

        dir_table = Table([
            [Paragraph(f"Fait à Katiola, le {today_str}", right_style)],
            [Paragraph(f"<b>Le {titre_signataire}</b>", right_bold)],
        ], colWidths=[8.6 * cm])
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