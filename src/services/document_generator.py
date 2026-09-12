"""
========================================================================
DRENAET-RH - Moteur de génération de documents PDF (v2)
========================================================================
Génère des documents PDF de qualité ministérielle avec ReportLab.

Format fidèle au modèle officiel de la DRENAET de Katiola :
- En-tête tri-colonne : Ministère / Armoirie / République + N° de référence
- Titre centré en gras
- Formule de destinataire (A Monsieur le Directeur Régional...)
- Sections avec tableaux d'infos
- Phrases d'introduction et de conclusion
- Tableau de signatures (Intéressé / Intérimaire / Décision DR)
- Lieu, date + bloc signature du Directeur Régional
- Ampliations en bas
- Footer avec QR code et code-barres pour authentification

Architecture :
- DocumentGenerator : classe principale qui orchestre la génération
- DocumentTemplate : classe de base pour chaque type de document
- Les templates spécifiques héritent de DocumentTemplate
"""

import os
import json
import qrcode
import barcode
from barcode.writer import ImageWriter
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, KeepTogether, PageBreak, Flowable
)
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from config import settings
from src.models import get_session, Personnel, DocumentGenere, CompteurDocument


# ========================================================================
# CONSTANTES DE STYLE
# ========================================================================
COLOR_PRIMARY = colors.HexColor("#4338CA")
COLOR_VIOLET = colors.HexColor("#7C3AED")
COLOR_LABEL = colors.HexColor("#1E1B4B")
COLOR_VALUE = colors.HexColor("#1F2937")
COLOR_BORDER = colors.HexColor("#9CA3AF")
COLOR_FOOTER = colors.HexColor("#6B7280")
COLOR_TEXT_BLACK = colors.HexColor("#000000")


# ========================================================================
# CLASSE PRINCIPALE
# ========================================================================
class DocumentGenerator:
    """Générateur de documents PDF DRENAET-RH."""

    def __init__(self):
        self.styles = self._build_styles()

    # ====================================================================
    def _build_styles(self) -> dict:
        """Construit les styles de paragraphes réutilisables."""
        return {
            # En-têtes ministère/république
            "header_admin": ParagraphStyle(
                "header_admin",
                fontName="Helvetica-Bold", fontSize=9,
                textColor=COLOR_TEXT_BLACK, alignment=TA_CENTER, leading=11,
            ),
            "header_separator": ParagraphStyle(
                "header_separator",
                fontName="Helvetica", fontSize=8,
                textColor=COLOR_TEXT_BLACK, alignment=TA_CENTER, leading=10,
            ),
            # Référence du document
            "ref_number": ParagraphStyle(
                "ref_number",
                fontName="Helvetica", fontSize=10,
                textColor=COLOR_TEXT_BLACK, alignment=TA_LEFT, leading=14,
            ),
            # Titre du document
            "doc_title": ParagraphStyle(
                "doc_title",
                fontName="Helvetica-Bold", fontSize=16,
                textColor=COLOR_TEXT_BLACK, alignment=TA_CENTER,
                leading=20, spaceBefore=8, spaceAfter=12,
                underline=True,
            ),
            # Adresse destinataire (A Monsieur le DR...)
            "destinataire": ParagraphStyle(
                "destinataire",
                fontName="Helvetica-Bold", fontSize=11,
                textColor=COLOR_TEXT_BLACK, alignment=TA_CENTER, leading=15,
            ),
            # Texte de corps
            "body": ParagraphStyle(
                "body",
                fontName="Helvetica", fontSize=11,
                textColor=COLOR_TEXT_BLACK, alignment=TA_JUSTIFY,
                leading=15, spaceBefore=4, spaceAfter=4,
            ),
            # Labels / Valeurs des tableaux
            "label": ParagraphStyle(
                "label",
                fontName="Helvetica", fontSize=11,
                textColor=COLOR_TEXT_BLACK, alignment=TA_LEFT, leading=14,
            ),
            "value": ParagraphStyle(
                "value",
                fontName="Helvetica-Bold", fontSize=11,
                textColor=COLOR_TEXT_BLACK, alignment=TA_LEFT, leading=14,
            ),
            # Signature
            "sig_label": ParagraphStyle(
                "sig_label",
                fontName="Helvetica-Bold", fontSize=10,
                textColor=COLOR_TEXT_BLACK, alignment=TA_CENTER, leading=13,
            ),
            "sig_decision": ParagraphStyle(
                "sig_decision",
                fontName="Helvetica", fontSize=10,
                textColor=COLOR_TEXT_BLACK, alignment=TA_CENTER, leading=12,
            ),
            "lieu_date": ParagraphStyle(
                "lieu_date",
                fontName="Helvetica", fontSize=11,
                textColor=COLOR_TEXT_BLACK, alignment=TA_RIGHT, leading=14,
            ),
            "directeur": ParagraphStyle(
                "directeur",
                fontName="Helvetica-Bold", fontSize=11,
                textColor=COLOR_TEXT_BLACK, alignment=TA_CENTER, leading=14,
            ),
            "ampliations_title": ParagraphStyle(
                "ampliations_title",
                fontName="Helvetica-Bold", fontSize=10,
                textColor=COLOR_TEXT_BLACK, alignment=TA_LEFT, leading=12,
                underline=True,
            ),
            "ampliations_item": ParagraphStyle(
                "ampliations_item",
                fontName="Helvetica", fontSize=10,
                textColor=COLOR_TEXT_BLACK, alignment=TA_LEFT, leading=12,
            ),
        }

    # ====================================================================
    def generate(
        self,
        template,
        personnel_id: int,
        parameters: dict,
        user_login: str = "system",
    ) -> tuple[str, str]:
        """Génère un document PDF. Retourne (chemin_pdf, numero)."""
        with get_session() as db:
            agent = db.query(Personnel).filter_by(id=personnel_id).first()
            if not agent:
                raise ValueError(f"Personnel id={personnel_id} introuvable")

            numero, annee = self._generate_document_number(db, template.type_document)
            context = self._build_context(agent, parameters, numero, annee, template)

            output_dir = settings.OUTPUT_DIR / annee / template.dossier_sortie
            output_dir.mkdir(parents=True, exist_ok=True)

            num_only = numero.split("/")[0]
            filename = f"{num_only}_{agent.matricule}.pdf"
            pdf_path = output_dir / filename

            self._render_pdf(pdf_path, context, template)

            doc = DocumentGenere(
                numero=numero,
                type_document=template.type_document,
                annee_scolaire=annee,
                personnel_id=personnel_id,
                interim_personnel_id=parameters.get("interim_personnel_id"),
                parametres_json=json.dumps(parameters, default=str, ensure_ascii=False),
                chemin_pdf=str(pdf_path),
                genere_par=user_login,
            )
            db.add(doc)

            return str(pdf_path), numero

    # ====================================================================
    def _generate_document_number(self, db, type_document: str) -> tuple[str, str]:
        """Génère le numéro officiel d'un document."""
        annee = self._current_school_year()
        compteur = db.query(CompteurDocument).filter_by(
            type_document=type_document,
            annee_scolaire=annee,
        ).first()

        if not compteur:
            compteur = CompteurDocument(
                type_document=type_document,
                annee_scolaire=annee,
                dernier_numero=0,
            )
            db.add(compteur)
            db.flush()

        nouveau = compteur.incrementer()
        numero = settings.DOCUMENT_REF_FORMAT.format(num=nouveau)
        return numero, annee

    # ====================================================================
    def _current_school_year(self) -> str:
        """Retourne l'année scolaire courante (ex: '2025-2026')."""
        today = date.today()
        if today.month >= 9:
            return f"{today.year}-{today.year + 1}"
        else:
            return f"{today.year - 1}-{today.year}"

    # ====================================================================
    def _build_context(self, agent, parameters, numero, annee, template) -> dict:
        """Construit le contexte complet pour le rendu PDF."""
        return {
            "numero": numero,
            "annee_scolaire": annee,
            "date_generation": datetime.now(),
            "doc_id": self._generate_doc_id(template.type_document, annee, numero),
            "agent": {
                "matricule": agent.matricule or "",
                "nom": agent.nom or "",
                "prenoms": agent.prenoms or "",
                "nom_complet": agent.nom_complet,
                "sexe": agent.sexe or "",
                "civilite": agent.civilite,
                "date_naissance": agent.date_naissance,
                "lieu_naissance": agent.lieu_naissance or "",
                "situation_matrimoniale": agent.situation_matrimoniale or "",
                "telephone": agent.telephone or "",
                "email": agent.email or "",
                "emploi": agent.emploi or "",
                "grade": agent.grade or "",
                "fonction": agent.fonction or "",
                "structure": agent.structure.nom if agent.structure else "",
                "structure_type": agent.structure.type if agent.structure else "",
                "residence": agent.residence or (agent.structure.localite if agent.structure else ""),
                "date_prise_service": agent.date_prise_service,
                "date_affectation": agent.date_affectation,
            },
            "parameters": parameters,
        }

    # ====================================================================
    def _generate_doc_id(self, type_doc: str, annee: str, numero: str) -> str:
        """Génère l'ID unique du document (pour QR / barcode)."""
        type_abbr = {
            "autorisation_absence": "AUT",
            "ordre_mission": "OM",
            "attestation_travail": "ATT",
            "attestation_presence": "PRES",
            "titre_conges": "CG",
            "certificat_prise_service": "CPS",
            "certificat_cessation": "CCS",
            "fiche_mutation": "MUT",
        }.get(type_doc, "DOC")

        num_only = numero.split("/")[0]
        try:
            num_int = int(num_only)
            num_padded = f"{num_int:08d}"
        except ValueError:
            num_padded = num_only.zfill(8)

        return f"MENAET-{type_abbr}-{annee}-{num_padded}"

    # ====================================================================
    def _render_pdf(self, pdf_path: Path, context: dict, template):
        """Génère le PDF avec ReportLab."""
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            leftMargin=2.0 * cm,
            rightMargin=2.0 * cm,
            topMargin=1.0 * cm,
            bottomMargin=2.2 * cm,
            title=template.titre_document,
            author=settings.APP_ORGANIZATION,
        )

        story = []

        # 1. EN-TÊTE OFFICIEL (Ministère + Armoirie + République + Année)
        story.append(self._build_header(context))
        story.append(Spacer(1, 0.2 * cm))

        # 2. NUMÉRO DE RÉFÉRENCE (aligné à gauche)
        story.append(Paragraph(
            f"<b>N° {context['numero']}</b>",
            self.styles["ref_number"]
        ))
        story.append(Spacer(1, 0.5 * cm))

        # 3. TITRE DU DOCUMENT (centré, souligné, gras)
        story.append(Paragraph(
            f"<u>{template.titre_document.upper()}</u>",
            self.styles["doc_title"]
        ))
        story.append(Spacer(1, 0.2 * cm))

        # 4. DESTINATAIRE (si défini par le template)
        if hasattr(template, "destinataire") and template.destinataire:
            for line in template.destinataire:
                story.append(Paragraph(line, self.styles["destinataire"]))
        story.append(Spacer(1, 0.35 * cm))

        # 5. CORPS DU DOCUMENT (sections du template)
        body_elements = template.build_body(context, self.styles)
        story.extend(body_elements)

        # 6. ZONE SIGNATURES (si template en définit une)
        if hasattr(template, "build_signature_zone"):
            sig = template.build_signature_zone(context, self.styles)
            if sig:
                story.append(Spacer(1, 0.3 * cm))
                story.extend(sig)

        # 7. LIEU, DATE + DIRECTEUR RÉGIONAL
        if hasattr(template, "build_directeur_zone"):
            dir_zone = template.build_directeur_zone(context, self.styles)
            if dir_zone:
                story.append(Spacer(1, 0.25 * cm))
                story.extend(dir_zone)

        # 8. AMPLIATIONS (en bas à gauche)
        if hasattr(template, "build_ampliations"):
            amp = template.build_ampliations(context, self.styles)
            if amp:
                story.append(Spacer(1, 0.4 * cm))
                story.extend(amp)

        # Construire le PDF avec le footer en bas
        doc.build(
            story,
            onFirstPage=lambda c, d: self._draw_footer(c, d, context),
            onLaterPages=lambda c, d: self._draw_footer(c, d, context),
        )

    # ====================================================================
    def _build_header(self, context: dict) -> Table:
        """En-tête tri-colonne : Ministère | Armoirie | République."""
        # Côté gauche : Ministère + Direction
        ministere_text = Paragraph(
            "<b>MINISTÈRE DE L'ÉDUCATION NATIONALE,</b><br/>"
            "<b>DE L'ALPHABÉTISATION ET</b><br/>"
            "<b>DE L'ENSEIGNEMENT TECHNIQUE</b><br/>"
            "<font size=8>---------------------</font><br/>"
            "<b>DIRECTION RÉGIONALE DE KATIOLA</b><br/>"
            "<font size=8>---------------------</font>",
            self.styles["header_admin"]
        )

        # Centre : Armoirie (image)
        armoirie_path = settings.RESOURCES_DIR / "images" / "armoirie_ci.png"
        if armoirie_path.exists():
            armoirie_element = Image(
                str(armoirie_path),
                width=2.5 * cm, height=2.5 * cm,
            )
            armoirie_element.hAlign = "CENTER"
        else:
            armoirie_element = Paragraph(
                "<font color='#9CA3AF' size=8>[Armoirie]</font>",
                ParagraphStyle("armoirie_ph", fontName="Helvetica", fontSize=8,
                               alignment=TA_CENTER, textColor=COLOR_FOOTER, leading=10)
            )

        # Côté droit : République
        republique_text = Paragraph(
            "<b>RÉPUBLIQUE DE CÔTE D'IVOIRE</b><br/>"
            "<font size=8>---------------------</font><br/>"
            "<i>Union – Discipline – Travail</i><br/>"
            "<font size=8>---------------------</font><br/>"
            f"<b>Année scolaire {context['annee_scolaire']}</b>",
            self.styles["header_admin"]
        )

        tbl = Table(
            [[ministere_text, armoirie_element, republique_text]],
            colWidths=[7 * cm, 3 * cm, 7 * cm],
        )
        tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return tbl

    # ====================================================================
    def render_info_table(self, fields: list, styles: dict, col1_width=5*cm, col2_width=11*cm) -> Table:
        """
        Rend un tableau d'infos style "Label : Valeur" sans cadre visible.
        fields = [("Matricule", "233329C"), ...]
        """
        rows = []
        for label, value in fields:
            rows.append([
                Paragraph(f"{label}", styles["label"]),
                Paragraph(f": <b>{value}</b>" if value else ":", styles["value"]),
            ])

        tbl = Table(rows, colWidths=[col1_width, col2_width])
        tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return tbl

    # ====================================================================
    def _make_barcode_image_bytes(self, data: str) -> BytesIO:
        """Crée un BytesIO d'un code-barres Code128."""
        CODE128 = barcode.get_barcode_class("code128")
        bc = CODE128(data, writer=ImageWriter())

        buf = BytesIO()
        bc.write(buf, options={
            "module_width": 0.25,
            "module_height": 8,
            "font_size": 6,
            "text_distance": 2,
            "quiet_zone": 2,
            "write_text": False,
        })
        buf.seek(0)
        return buf

    # ====================================================================
    def _draw_footer(self, c: canvas.Canvas, doc, context: dict):
        """Dessine le footer (ID + code-barres + QR) en bas de page."""
        page_width, page_height = A4

        # Ligne de séparation grise
        c.setStrokeColor(COLOR_BORDER)
        c.setLineWidth(0.5)
        c.line(2 * cm, 2.0 * cm, page_width - 2 * cm, 2.0 * cm)

        # ID document (gauche)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(COLOR_LABEL)
        c.drawString(2 * cm, 1.5 * cm, f"ID : {context['doc_id']}")

        # Code-barres au centre
        try:
            bc_buf = self._make_barcode_image_bytes(context["doc_id"])
            c.drawImage(
                ImageReader(bc_buf),
                (page_width / 2) - 3 * cm, 0.7 * cm,
                width=6 * cm, height=1.0 * cm,
            )
        except Exception as e:
            print(f"⚠ Erreur code-barres : {e}")

        # QR à droite
        try:
            qr_pil = qrcode.make(context["doc_id"], box_size=3, border=1)
            qr_buf = BytesIO()
            qr_pil.save(qr_buf, format="PNG")
            qr_buf.seek(0)
            c.drawImage(
                ImageReader(qr_buf),
                page_width - 3.8 * cm, 0.55 * cm,
                width=1.6 * cm, height=1.6 * cm,
            )
        except Exception as e:
            print(f"⚠ Erreur QR : {e}")

        # Mention en bas
        c.setFont("Helvetica", 6.5)
        c.setFillColor(COLOR_FOOTER)
        date_str = context["date_generation"].strftime("%d/%m/%Y à %H:%M")
        footer_text = (
            f"Document authentifiable via QR code ou code-barres  |  "
            f"Imprimé par DRENAET-RH le {date_str}"
        )
        c.drawCentredString(page_width / 2, 0.35 * cm, footer_text)


# ========================================================================
# CLASSE DE BASE DES TEMPLATES
# ========================================================================
class DocumentTemplate:
    """Classe de base pour tous les templates."""
    type_document: str = ""
    titre_document: str = ""
    dossier_sortie: str = ""
    destinataire: list = []  # Lignes de la formule d'adresse

    def build_body(self, context: dict, styles: dict) -> list:
        """Retourne la liste des éléments du corps du document."""
        raise NotImplementedError