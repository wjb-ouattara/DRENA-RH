"""
========================================================================
Template : Fiche d'inscription Mutation - Chef de Circonscription
========================================================================
Document moderne style "Fiche d'inscription" avec sections bandeau gris.
Inspiré du modèle SYGMUTE (mena-sygmute.com) du Ministère.

⚠️ Différence notable : pas de photo (comme demandé par le client),
juste le QR code pour authentification (déjà dans le footer du moteur).

Structure :
1. Bandeau gris "INFORMATIONS PERSONNELLES" + tableau 2 colonnes
2. Bandeau gris "INFORMATIONS PROFESSIONNELLES" + tableau 2 colonnes
3. Bandeau gris "LISTE DES VŒUX DE L'INTÉRESSÉ" + tableau 3 colonnes
   (N° | DRENAET souhaitée | IEPP souhaitée)
"""

from datetime import date, datetime
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from config import settings
from src.services.document_generator import DocumentTemplate


def _format_date_short(d) -> str:
    if not d:
        return "—"
    if isinstance(d, str):
        try:
            d = datetime.fromisoformat(d).date()
        except (ValueError, TypeError):
            return d
    if not isinstance(d, (date, datetime)):
        return str(d)
    return d.strftime("%d-%m-%Y")


def _titre_civil(sexe: str) -> str:
    return "Madame" if (sexe or "").upper() == "F" else "Monsieur"


def _genre(sexe: str) -> str:
    return "FÉMININ" if (sexe or "").upper() == "F" else "MASCULIN"


# ========================================================================
class FicheMutationTemplate(DocumentTemplate):
    """Template de la Fiche d'inscription Mutation - Chef de Circonscription."""

    type_document = "fiche_mutation"
    titre_document = "FICHE D'INSCRIPTION | MUTATION - CHEF DE CIRCONSCRIPTION"
    dossier_sortie = "fiches_mutation"
    destinataire = []

    # ====================================================================
    def build_body(self, context: dict, styles: dict) -> list:
        agent = context["agent"]
        params = context["parameters"]

        elements = []

        # ============================================================
        # SECTION 1 : INFORMATIONS PERSONNELLES
        # ============================================================
        elements.append(self._section_band("INFORMATIONS PERSONNELLES"))
        elements.append(Spacer(1, 0.1 * cm))

        nom_complet = f"{agent['nom']} {agent['prenoms']}".strip().upper()
        infos_perso = [
            ("Matricule", agent["matricule"]),
            ("Genre", _genre(agent["sexe"])),
            ("Nom & Prénoms", nom_complet),
            ("Date de naissance", _format_date_short(agent["date_naissance"])),
            ("Lieu de naissance", agent["lieu_naissance"] or "—"),
            ("Situation matrimoniale", (agent["situation_matrimoniale"] or "—").upper()),
            ("Cellulaire", agent["telephone"] or "—"),
            ("Email", agent["email"] or "—"),
        ]
        elements.append(self._render_info_table(infos_perso, styles))
        elements.append(Spacer(1, 0.4 * cm))

        # ============================================================
        # SECTION 2 : INFORMATIONS PROFESSIONNELLES
        # ============================================================
        elements.append(self._section_band("INFORMATIONS PROFESSIONNELLES"))
        elements.append(Spacer(1, 0.1 * cm))

        infos_pro = [
            ("DRENAET", "DRENAET KATIOLA"),
            ("Structure actuelle", agent["structure"] or "—"),
            ("Emploi", (agent["emploi"] or "").upper()),
            ("Grade", agent["grade"] or "—"),
            ("Fonction actuelle", (agent["fonction"] or "—").upper()),
            ("Date d'entrée à la Fonction Publique",
             _format_date_short(params.get("date_entree_fp"))),
            ("Date d'entrée à la DRENAET",
             _format_date_short(params.get("date_entree_drenaet") or agent["date_prise_service"])),
            ("Date fonction actuelle",
             _format_date_short(params.get("date_fonction_actuelle") or agent["date_affectation"])),
            ("Date de départ à la retraite",
             _format_date_short(params.get("date_retraite"))),
        ]
        elements.append(self._render_info_table(infos_pro, styles))
        elements.append(Spacer(1, 0.4 * cm))

        # ============================================================
        # SECTION 3 : LISTE DES VŒUX
        # ============================================================
        elements.append(self._section_band("INFORMATIONS SUR LA DEMANDE DE L'AGENT"))
        elements.append(Spacer(1, 0.15 * cm))
        elements.append(self._section_band("LISTE DES VŒUX DE L'INTÉRESSÉ"))
        elements.append(Spacer(1, 0.1 * cm))

        voeux = params.get("voeux", [])
        elements.append(self._render_voeux_table(voeux))

        return elements

    # ====================================================================
    def _section_band(self, title: str) -> Table:
        """Crée un bandeau gris pour titre de section (style officiel SYGMUTE)."""
        section_style = ParagraphStyle(
            "section_band", fontName="Helvetica-Bold", fontSize=10,
            textColor=colors.HexColor("#FFFFFF"),
            alignment=TA_LEFT, leading=14,
        )
        tbl = Table(
            [[Paragraph(f"  <b>{title}</b>", section_style)]],
            colWidths=[16 * cm],
            rowHeights=[0.65 * cm],
        )
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#6B7280")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        return tbl

    # ====================================================================
    def _render_info_table(self, fields: list, styles: dict) -> Table:
        """Tableau infos sans cadre, lignes de séparation discrètes.

        Utilise des strings directes (pas de Paragraph) pour éviter
        les problèmes de calcul de largeur avec les labels longs.
        Le style est appliqué via TableStyle.
        """
        rows = []
        for label, value in fields:
            rows.append([
                str(label),
                ":",
                str(value) if value else "",
            ])

        tbl = Table(rows, colWidths=[6.8 * cm, 0.4 * cm, 8.8 * cm])
        tbl.setStyle(TableStyle([
            # Police pour tout le tableau
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1F2937")),
            # Label en bold (colonne 0)
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1E1B4B")),
            # Valeur en bold (colonne 2)
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            # Alignements et paddings
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#E5E7EB")),
        ]))
        return tbl

    # ====================================================================
    def _render_voeux_table(self, voeux: list) -> Table:
        """
        Tableau des vœux : N° | DRENAET souhaitée | IEPP souhaitée
        voeux = [{"drenaet": "...", "iepp": "..."}, ...]
        """
        # En-tête
        header_style = ParagraphStyle(
            "voeux_header", fontName="Helvetica-Bold", fontSize=10,
            textColor=colors.HexColor("#FFFFFF"),
            alignment=TA_CENTER, leading=12,
        )
        cell_style = ParagraphStyle(
            "voeux_cell", fontName="Helvetica-Bold", fontSize=10,
            textColor=colors.HexColor("#000000"),
            alignment=TA_LEFT, leading=12,
        )
        num_style = ParagraphStyle(
            "voeux_num", fontName="Helvetica-Bold", fontSize=10,
            textColor=colors.HexColor("#1E1B4B"),
            alignment=TA_CENTER, leading=12,
        )

        rows = [
            [
                Paragraph("<b>N°</b>", header_style),
                Paragraph("<b>DRENAET souhaitée</b>", header_style),
                Paragraph("<b>IEPP souhaitée</b>", header_style),
            ]
        ]

        # Lignes de vœux (3 maximum, on remplit avec — si vide)
        for i in range(3):
            if i < len(voeux):
                v = voeux[i]
                drenaet = v.get("drenaet", "—") or "—"
                iepp = v.get("iepp", "—") or "—"
            else:
                drenaet = "—"
                iepp = "—"

            rows.append([
                Paragraph(str(i + 1), num_style),
                Paragraph(drenaet.upper(), cell_style),
                Paragraph(iepp.upper(), cell_style),
            ])

        tbl = Table(rows, colWidths=[1.5 * cm, 7.5 * cm, 7 * cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6B7280")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFFFFF")),
            ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#F3F4F6")),  # ligne 2 grisée
        ]))
        return tbl

    # ====================================================================
    def build_ampliations(self, context: dict, styles: dict) -> list:
        """Footer officiel DRENAET (BP, Tél, Email)."""
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