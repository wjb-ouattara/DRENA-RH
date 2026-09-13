"""
========================================================================
Template : Ordre de Mission (v2 — avec hébergement, repas, footer DRENAET)
========================================================================
Reproduit le format officiel ivoirien d'un Ordre de Mission.

Améliorations v2 :
- Ajout HÉBERGEMENT ASSURÉ (Oui/Non)
- Ajout REPAS FOURNI (Oui/Non)
- Footer officiel DRENAET (BP, Tél, Email)
- Nom du Directeur Régional depuis settings.DRENAET_INFO
"""

from datetime import date, datetime
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

from config import settings
from src.services.document_generator import DocumentTemplate


# ========================================================================
# UTILITAIRES
# ========================================================================
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
class OrdreMissionTemplate(DocumentTemplate):
    """Template d'Ordre de Mission."""

    type_document = "ordre_mission"
    titre_document = "ORDRE DE MISSION"
    dossier_sortie = "ordres_mission"
    destinataire = []

    # ====================================================================
    def build_body(self, context: dict, styles: dict) -> list:
        """Construit le corps de l'Ordre de Mission."""
        agent = context["agent"]
        params = context["parameters"]

        elements = []

        # ----- Phrase d'introduction (formule officielle) -----
        elements.append(Paragraph(
            "<b>Le Directeur Régional de l'Éducation Nationale, "
            "de l'Alphabétisation et de l'Enseignement Technique "
            "de Katiola</b>",
            styles["body"]
        ))
        elements.append(Spacer(1, 0.3 * cm))

        # ----- Tableau infos de l'agent missionné -----
        # Libellés en capitales, conformément au modèle officiel de la DRENAET.
        civilite_agent = _civilite(agent["sexe"], agent["situation_matrimoniale"])
        nom_complet = f"{agent['nom']} {agent['prenoms']}".strip().upper()

        agent_fields = [
            ("DONNE L'ORDRE A", f"{civilite_agent}  {nom_complet}"),
            ("MATRICULE", agent["matricule"]),
            ("EMPLOI", agent["emploi"]),
            ("FONCTION", agent["fonction"] or ""),
            ("STRUCTURE", agent["structure"]),
            ("RESIDENCE", agent["residence"]),
        ]
        elements.append(self._render_info_table(agent_fields, styles))
        elements.append(Spacer(1, 0.3 * cm))

        # ----- Phrase de mission -----
        elements.append(Paragraph(
            "Dans les conditions ci-après précisées :",
            styles["body"]
        ))
        elements.append(Spacer(1, 0.25 * cm))

        # ----- Détails de la mission -----
        date_depart = params.get("date_depart")
        date_retour = params.get("date_retour")

        # Hébergement et repas
        hebergement = params.get("hebergement_assure", False)
        repas = params.get("repas_fourni", False)
        hebergement_str = "OUI" if hebergement else "NON"
        repas_str = "OUI" if repas else "NON"

        mission_fields = [
            ("DE SE RENDRE", params.get("destination", "")),
            ("OBJET DE LA MISSION", params.get("objet", "")),
            ("DATE DE DEPART", _format_date_short(date_depart) if date_depart else ""),
            ("DATE DE RETOUR", _format_date_short(date_retour) if date_retour else ""),
            ("MOYEN DE DEPLACEMENT", params.get("moyen_deplacement", "")),
            ("HEBERGEMENT ASSURE", hebergement_str),
            ("REPAS FOURNI", repas_str),
        ]

        # Imputation budgétaire (optionnel)
        if params.get("imputation"):
            mission_fields.append(("IMPUTATION BUDGETAIRE", params.get("imputation", "")))

        elements.append(self._render_info_table(mission_fields, styles))
        elements.append(Spacer(1, 0.4 * cm))

        # ----- Phrase finale -----
        elements.append(Paragraph(
            "Les frais relatifs à cette mission sont à la charge "
            "du budget de la Direction Régionale.",
            styles["body"]
        ))

        return elements

    # ====================================================================
    def build_directeur_zone(self, context: dict, styles: dict) -> list:
        """Lieu, date + Le Directeur Régional (en bas à droite)."""
        elements = []
        today_str = _format_date_short(date.today())
        info = settings.DRENAET_INFO

        # Si signature par procuration (PO)
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
            "amp_title", fontName="Helvetica-Bold", fontSize=10,
            alignment=TA_LEFT, leading=12, textColor=colors.HexColor("#000000"),
        )
        amp_item_style = ParagraphStyle(
            "amp_item", fontName="Helvetica", fontSize=10,
            alignment=TA_LEFT, leading=12, textColor=colors.HexColor("#000000"),
        )

        amp_table = Table(
            [
                [Paragraph("<u>Ampliations</u>", amp_title_style)],
                [Paragraph("L'intéressé(e) ............................. 1", amp_item_style)],
                [Paragraph("Structure d'origine .................... 1", amp_item_style)],
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

        # Les coordonnées officielles de la DRENAET sont désormais portées par
        # le pied de page de chaque page, dessiné par le générateur.
        return elements

    # ====================================================================
    def _render_info_table(self, fields: list, styles: dict) -> Table:
        """Tableau d'infos style 'Label : Valeur' sans cadre."""
        rows = []
        for label, value in fields:
            rows.append([
                Paragraph(label, styles["label"]),
                Paragraph(":", styles["label"]),
                Paragraph(f"<b>{value}</b>" if value else "", styles["value"]),
            ])

        # 5,6 cm pour accueillir les libellés en capitales les plus longs
        # (MOYEN DE DEPLACEMENT, IMPUTATION BUDGETAIRE) sans repli de ligne.
        tbl = Table(rows, colWidths=[5.6 * cm, 0.4 * cm, 10.9 * cm])
        tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return tbl