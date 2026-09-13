"""
========================================================================
DRENAET-RH - Moteur de génération de documents PDF (v2)
========================================================================
Génère des documents PDF de qualité ministérielle avec ReportLab.

Format fidèle au modèle officiel de la DRENAET de Katiola :
- Bandeau d'en-tête à dégradé tricolore (orange pâle / blanc / vert pâle)
  portant l'armoirie de Côte d'Ivoire au centre, le Ministère à gauche
  et la République à droite
- N° de référence à gauche, puis bandeau de titre sur fond orange pâle
- Formule de destinataire (A Monsieur le Directeur Régional...)
- Sections avec tableaux d'infos
- Phrases d'introduction et de conclusion
- Tableau de signatures (Intéressé / Intérimaire / Décision DR)
- Ampliations à gauche et signature du Directeur Régional à droite,
  côte à côte comme sur le document officiel signé
- Pied de page sobre : coordonnées officielles de la DRENAET, ID et pagination

Architecture :
- DocumentGenerator : classe principale qui orchestre la génération
- DocumentTemplate : classe de base pour chaque type de document
- Les templates spécifiques héritent de DocumentTemplate
"""

import os
import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional

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

# --- Palette « Light & Ember » appliquée aux documents ---------------------
# Le dégradé de l'en-tête reprend les couleurs du drapeau ivoirien, mais
# volontairement très désaturées : le texte noir doit rester parfaitement
# lisible par-dessus, y compris à l'impression en noir et blanc.
COLOR_ORANGE = colors.HexColor("#F97316")        # accents
COLOR_ORANGE_DARK = colors.HexColor("#C2410C")
COLOR_BAND_ORANGE = colors.HexColor("#FDEBD3")   # fond du bandeau de titre
COLOR_GRADIENT_ORANGE = colors.HexColor("#FDEBD3")
COLOR_GRADIENT_GREEN = colors.HexColor("#E3F2E8")
COLOR_GREEN = colors.HexColor("#128A4D")
COLOR_SECTION_BAND = colors.HexColor("#7F7F7F")   # bandeaux de section (gris)

# Géométrie de l'en-tête. Le bandeau dégradé et le bandeau de titre sont
# dessinés sur le canevas, bord à bord : ils ont donc exactement la même
# largeur, celle de la page. Le flux démarre à l'intérieur du dégradé
# (topMargin) puis un Spacer le fait passer sous le bandeau de titre.
HEADER_BAND_TOP = 0.45 * cm
HEADER_BAND_HEIGHT = 3.05 * cm
TITLE_BAND_HEIGHT = 0.85 * cm
TITLE_BAND_GAP = 0.28 * cm      # respiration entre l'en-tête et le titre
BAND_SIDE_MARGIN = 2.0 * cm     # les bandeaux s'alignent sur les marges
BAND_WIDTH = A4[0] - 2 * BAND_SIDE_MARGIN
HEADER_ROW_HEIGHT = 2.45 * cm   # hauteur fixe du flowable d'en-tête


# ========================================================================
# CLASSE PRINCIPALE
# ========================================================================
class DocumentGenerator:
    """Générateur de documents PDF DRENAET-RH."""

    def __init__(self):
        self.styles = self._build_styles()
        # Renseignés par _render_pdf(), lus par _draw_header_band().
        self._titre_bandeau = ""
        self._annee_bandeau = ""

    # ====================================================================
    def _build_styles(self) -> dict:
        """Construit les styles de paragraphes réutilisables."""
        return {
            # En-têtes ministère/république
            "header_admin": ParagraphStyle(
                "header_admin",
                fontName="Helvetica-Bold", fontSize=8,
                textColor=COLOR_TEXT_BLACK, alignment=TA_CENTER, leading=9.8,
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
            # Titre du document (conserv\u00e9 pour compatibilit\u00e9 des templates)
            "doc_title": ParagraphStyle(
                "doc_title",
                fontName="Helvetica-Bold", fontSize=16,
                textColor=COLOR_TEXT_BLACK, alignment=TA_CENTER,
                leading=20, spaceBefore=8, spaceAfter=12,
                underline=True,
            ),
            # Titre du document : dessiné directement sur le canevas pour
            # occuper toute la largeur de la page, comme le bandeau d'en-tête.
            "title_band": ParagraphStyle(
                "title_band",
                fontName="Helvetica-Bold", fontSize=10.5,
                textColor=COLOR_TEXT_BLACK, alignment=TA_CENTER, leading=13,
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
        """Génère l'identifiant unique du document (traçabilité interne)."""
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
            # Le flux démarre à l'intérieur du bandeau d'en-tête, dessiné en
            # arrière-plan par _draw_header_band().
            topMargin=0.62 * cm,
            bottomMargin=2.2 * cm,
            title=template.titre_document,
            author=settings.APP_ORGANIZATION,
        )

        # Libellés repris par _draw_header_band() pour le bandeau de titre,
        # qui est dessiné sur le canevas et non ajouté au flux.
        self._titre_bandeau = self._titre_bandeau_texte(context, template)
        self._annee_bandeau = context["annee_scolaire"]

        story = []

        # 1. EN-TÊTE OFFICIEL (Ministère + Armoirie + République + Année)
        #    Le bandeau dégradé et le bandeau de titre sont dessinés en
        #    arrière-plan ; ce Spacer fait redémarrer le flux juste en dessous.
        #    Il vaut la hauteur cumulée des deux bandeaux et de leur écart,
        #    moins la hauteur du flowable d'en-tête. Toute modification de
        #    HEADER_ROW_HEIGHT, TITLE_BAND_GAP ou TITLE_BAND_HEIGHT s'y reporte
        #    automatiquement.
        story.append(self._build_header(context))
        story.append(Spacer(1, (
            HEADER_BAND_TOP + HEADER_BAND_HEIGHT + TITLE_BAND_GAP
            + TITLE_BAND_HEIGHT + 0.35 * cm
            - doc.topMargin - HEADER_ROW_HEIGHT
        )))

        # 2. NUMÉRO DE RÉFÉRENCE (aligné à gauche)
        story.append(Paragraph(
            f"<b>N° {context['numero']}</b>",
            self.styles["ref_number"]
        ))
        story.append(Spacer(1, 0.3 * cm))

        # 4. DESTINATAIRE (si défini par le template)
        if hasattr(template, "destinataire") and template.destinataire:
            for line in template.destinataire:
                story.append(Paragraph(line, self.styles["destinataire"]))
        story.append(Spacer(1, 0.35 * cm))

        # 5. CORPS DU DOCUMENT (sections du template)
        body_elements = template.build_body(context, self.styles)
        story.extend(body_elements)

        # 6. ZONE SIGNATURES (si template en définit une)
        #    KeepTogether évite que le tableau ne se coupe entre deux pages.
        if hasattr(template, "build_signature_zone"):
            sig = template.build_signature_zone(context, self.styles)
            if sig:
                story.append(Spacer(1, 0.3 * cm))
                story.append(KeepTogether(sig))

        # 7. AMPLIATIONS (gauche) et SIGNATURE DU DIRECTEUR (droite)
        #    Les deux blocs sont côte à côte, comme sur le document officiel
        #    signé. Les empiler verticalement coûtait environ 4 cm et faisait
        #    déborder l'autorisation d'absence avec intérim sur une 2e page.
        story.extend(self._build_closing_block(context, template))

        # Construire le PDF avec le bandeau d'en-tête et le pied de page
        doc.build(
            story,
            onFirstPage=lambda c, d: self._draw_page_decorations(c, d, context),
            onLaterPages=lambda c, d: self._draw_page_decorations(c, d, context),
        )

    # ====================================================================
    def _draw_page_decorations(self, c: canvas.Canvas, doc, context: dict):
        """Dessine le bandeau d'en-tête puis le pied de page."""
        self._draw_header_band(c, doc)
        self._draw_footer(c, doc, context)

    # ====================================================================
    def _build_closing_block(self, context: dict, template) -> list:
        """
        Assemble les ampliations et la zone de signature du Directeur Régional
        sur une seule ligne, à deux colonnes. Si le template ne fournit qu'un
        seul des deux blocs, celui-ci est rendu seul, pleine largeur.
        """
        amp = []
        if hasattr(template, "build_ampliations"):
            amp = template.build_ampliations(context, self.styles) or []

        dirzone = []
        if hasattr(template, "build_directeur_zone"):
            dirzone = template.build_directeur_zone(context, self.styles) or []

        if not amp and not dirzone:
            return []

        if not amp or not dirzone:
            return [Spacer(1, 0.4 * cm)] + (amp or dirzone)

        bloc = Table(
            [[amp, dirzone]],
            colWidths=[8.4 * cm, 8.6 * cm],
        )
        bloc.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return [Spacer(1, 0.4 * cm), bloc]

    # ====================================================================
    def _draw_header_band(self, c: canvas.Canvas, doc):
        """
        Dessine le bandeau d'en-tête à dégradé tricolore ET le bandeau de
        titre, séparés par une respiration et alignés tous deux sur les marges
        du texte : ils ont donc la même largeur, sans occuper toute la feuille.

        Le dégradé va de l'orange très pâle (gauche) au blanc (centre) puis au
        vert très pâle (droite) : les couleurs du drapeau ivoirien, désaturées
        pour préserver la lisibilité du texte noir posé par-dessus. Aucun filet
        ni bordure : le format de référence n'en comporte pas.

        Le bandeau de titre est dessiné ici, et non ajouté au flux, parce qu'un
        flowable ReportLab ne peut pas dépasser la largeur du cadre de texte
        (17 cm). Le dessiner sur le canevas garantit qu'il a exactement la même
        largeur que le bandeau d'en-tête au-dessus.
        Le dessin a lieu dans les callbacks de page, donc AVANT le contenu du
        flux : les bandes se retrouvent bien en arrière-plan.
        """
        page_width, page_height = A4

        # Le bandeau n'apparaît que sur la première page : l'en-tête officiel
        # ne se répète pas sur les pages de continuation.
        if doc.page != 1:
            return

        y_bas = page_height - HEADER_BAND_TOP - HEADER_BAND_HEIGHT
        x_gauche = BAND_SIDE_MARGIN

        c.saveState()
        try:
            # Le dégradé est clippé sur le rectangle de la bande.
            path = c.beginPath()
            path.rect(x_gauche, y_bas, BAND_WIDTH, HEADER_BAND_HEIGHT)
            c.clipPath(path, stroke=0, fill=0)
            c.linearGradient(
                x_gauche, y_bas, x_gauche + BAND_WIDTH, y_bas,
                [COLOR_GRADIENT_ORANGE, colors.white, COLOR_GRADIENT_GREEN],
                positions=[0.0, 0.5, 1.0],
                extend=True,
            )
        except Exception as e:
            # Repli : aplat blanc. Un document doit toujours pouvoir sortir.
            print(f"⚠ Dégradé d'en-tête indisponible, repli sur un aplat : {e}")
            c.setFillColor(colors.white)
            c.rect(x_gauche, y_bas, BAND_WIDTH, HEADER_BAND_HEIGHT,
                   stroke=0, fill=1)
        finally:
            c.restoreState()

        # --- Bandeau de titre, détaché de l'en-tête, même largeur -----------
        y_titre = y_bas - TITLE_BAND_GAP - TITLE_BAND_HEIGHT
        c.saveState()
        c.setFillColor(COLOR_BAND_ORANGE)
        c.rect(x_gauche, y_titre, BAND_WIDTH, TITLE_BAND_HEIGHT,
               stroke=0, fill=1)

        # Titre et année sur une seule ligne, en noir, comme le modèle :
        #   FICHE D'INSCRIPTION | MUTATION - CHEF DE CIRCONSCRIPTION | 2025-2026
        titre = f"{self._titre_bandeau} | {self._annee_bandeau}"
        c.setFillColor(COLOR_TEXT_BLACK)
        taille = 10.5
        # Réduit la police si le titre est trop long pour la largeur utile.
        while taille > 7 and c.stringWidth(titre, "Helvetica-Bold", taille) > BAND_WIDTH - 0.6 * cm:
            taille -= 0.5
        c.setFont("Helvetica-Bold", taille)
        c.drawCentredString(
            page_width / 2,
            y_titre + (TITLE_BAND_HEIGHT - taille) / 2 + 1,
            titre,
        )
        c.restoreState()

    # ====================================================================
    def _build_header(self, context: dict) -> Table:
        """
        En-tête tri-colonne posé sur le bandeau dégradé :
        Ministère / Direction  |  Armoirie  |  République / Année scolaire.
        """
        # Tirets séparateurs en noir, comme sur les documents de référence.
        tirets = "<font size=7 color='#000000'>———————————</font>"

        # Côté gauche : Ministère, Direction des Ressources Humaines, DRENAET
        ministere_text = Paragraph(
            "<b>MINISTÈRE DE L'ÉDUCATION NATIONALE,</b><br/>"
            "<b>DE L'ALPHABÉTISATION ET</b><br/>"
            "<b>DE L'ENSEIGNEMENT TECHNIQUE</b><br/>"
            f"{tirets}<br/>"
            "<b>DIRECTION DES RESSOURCES HUMAINES</b><br/>"
            f"{tirets}<br/>"
            "<b>DRENAET KATIOLA</b>",
            self.styles["header_admin"]
        )

        # Centre : armoirie de Côte d'Ivoire
        armoirie_path = settings.RESOURCES_DIR / "images" / "armoirie_ci.png"
        if armoirie_path.exists():
            armoirie_element = Image(
                str(armoirie_path),
                width=2.3 * cm, height=2.3 * cm,
            )
            armoirie_element.hAlign = "CENTER"
        else:
            armoirie_element = Paragraph(
                "<font color='#9CA3AF' size=8>[Armoirie]</font>",
                ParagraphStyle("armoirie_ph", fontName="Helvetica", fontSize=8,
                               alignment=TA_CENTER, textColor=COLOR_FOOTER, leading=10)
            )

        # Côté droit : République + devise + année scolaire
        republique_text = Paragraph(
            "<b>RÉPUBLIQUE DE CÔTE D'IVOIRE</b><br/>"
            f"{tirets}<br/>"
            "<i>Union - Discipline - Travail</i><br/>"
            f"{tirets}<br/>"
            f"<b>{context['annee_scolaire']}</b>",
            self.styles["header_admin"]
        )

        # Hauteur fixée : la position du bandeau de titre dessiné sur le
        # canevas est calculée en dur, le flowable ne doit donc pas varier.
        tbl = Table(
            [[ministere_text, armoirie_element, republique_text]],
            colWidths=[7.1 * cm, 2.8 * cm, 7.1 * cm],
            rowHeights=[HEADER_ROW_HEIGHT],
        )
        tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return tbl

    # ====================================================================
    def _titre_bandeau_texte(self, context: dict, template) -> str:
        """Libellé du bandeau de titre, en majuscules."""
        return template.titre_document.upper()

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
    def _draw_footer(self, c: canvas.Canvas, doc, context: dict):
        """
        Pied de page sobre, fidèle au document officiel : filet, nom complet
        de la Direction Régionale, coordonnées, puis l'identifiant du document
        à gauche et la pagination à droite.

        L'identifiant sert uniquement à retrouver la pièce dans le journal de
        l'application : il ne prétend pas authentifier le document.
        """
        page_width, _ = A4
        info = settings.DRENAET_INFO

        # Filet de séparation, en noir comme sur les documents de référence.
        c.saveState()
        c.setStrokeColor(COLOR_TEXT_BLACK)
        c.setLineWidth(0.7)
        c.line(2 * cm, 1.75 * cm, page_width - 2 * cm, 1.75 * cm)

        # Nom officiel de la structure
        c.setFont("Helvetica-BoldOblique", 7.5)
        c.setFillColor(COLOR_TEXT_BLACK)
        c.drawCentredString(page_width / 2, 1.42 * cm, info.get("nom_officiel", ""))

        # Coordonnées
        coordonnees = " · ".join(part for part in (
            info.get("bp", ""),
            f"Tél. : {info.get('telephone', '')}" if info.get("telephone") else "",
            info.get("email", ""),
        ) if part)
        c.setFont("Helvetica-Oblique", 7.5)
        c.drawCentredString(page_width / 2, 1.10 * cm, coordonnees)

        # Identifiant à gauche, pagination à droite
        c.setFont("Helvetica", 6.5)
        c.setFillColor(COLOR_FOOTER)
        date_str = context["date_generation"].strftime("%d/%m/%Y à %H:%M")
        c.drawString(2 * cm, 0.62 * cm, f"ID : {context['doc_id']}")
        c.drawRightString(page_width - 2 * cm, 0.62 * cm,
                          f"Édité par DRENAET-RH le {date_str}")
        c.restoreState()


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