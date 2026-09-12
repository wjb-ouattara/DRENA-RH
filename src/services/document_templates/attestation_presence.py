"""
========================================================================
Template : Attestation de Présence au Poste
========================================================================
Document quasi identique à l'Attestation de Travail, mais avec un focus
sur la présence effective au poste (utilisé pour la paie, RH, etc.).

Différences avec Attestation de Travail :
- Titre : "ATTESTATION DE PRÉSENCE AU POSTE"
- Structure listée dans le tableau (au lieu de "Est en service à")
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


def _pronom(sexe: str) -> str:
    return "elle" if (sexe or "").upper() == "F" else "il"


# ========================================================================
class AttestationPresenceTemplate(DocumentTemplate):
    """Template d'Attestation de Présence au Poste."""

    type_document = "attestation_presence"
    titre_document = "ATTESTATION DE PRÉSENCE AU POSTE"
    dossier_sortie = "attestations_presence"
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
            f"de l'Alphabétisation et de l'Enseignement Technique de Katiola, "
            f"soussigné {directeur_nom}, atteste par la présente que,</b>",
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
            ("Grade", agent["grade"] or "—"),
            ("Fonction", agent["fonction"] or "—"),
            ("Est en service au", agent["structure"]),
        ]
        elements.append(self._render_info_table(agent_fields, styles))
        elements.append(Spacer(1, 0.3 * cm))

        # Phrase certificative
        pronom = _pronom(agent["sexe"])
        date_prise = agent["date_prise_service"]
        date_prise_str = _format_date_short(date_prise) if date_prise else "—"

        elements.append(Paragraph(
            f"Où <b>{pronom}</b> assure régulièrement ses fonctions "
            f"depuis le <b>{date_prise_str}</b>.",
            styles["body"]
        ))
        elements.append(Spacer(1, 0.3 * cm))

        # But (optionnel)
        but = params.get("but")
        if but:
            elements.append(Paragraph(
                f"La présente attestation est délivrée à l'intéressé(e) "
                f"pour servir et valoir <b>{but}</b>.",
                styles["body"]
            ))
        else:
            elements.append(Paragraph(
                "En foi de quoi, la présente attestation lui est délivrée "
                "pour servir et valoir ce que de droit.",
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
        ], colWidths=[17 * cm])
        dir_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(dir_table)
        return elements

    # ====================================================================
    def build_ampliations(self, context: dict, styles: dict) -> list:
        elements = []
        info = settings.DRENAET_INFO

        sep_line = Table([[""]], colWidths=[8 * cm], rowHeights=[0.1 * cm])
        sep_line.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.HexColor("#4338CA")),
        ]))
        sep_line.hAlign = "CENTER"
        elements.append(sep_line)
        elements.append(Spacer(1, 0.2 * cm))

        official_footer_style = ParagraphStyle(
            "official_footer", fontName="Helvetica-Oblique", fontSize=8,
            alignment=TA_CENTER, leading=11, textColor=colors.HexColor("#4338CA"),
        )
        footer_text = (
            f"<i><b>Direction Régionale de l'Éducation Nationale, de l'Alphabétisation "
            f"et de l'Enseignement Technique de Katiola</b></i><br/>"
            f"<i>{info['bp']}  •  Tél. : {info['telephone']}  •  "
            f"E-mail : {info['email']}</i>"
        )
        elements.append(Paragraph(footer_text, official_footer_style))
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