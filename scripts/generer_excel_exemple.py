"""
========================================================================
DRENAET-RH — Générateur de fichiers Excel d'exemple pour l'import
========================================================================
Produit trois classeurs dans le dossier `exemples/`, chacun conçu pour
tester un aspect précis du pipeline d'import :

1. import_personnel_valide.xlsx
   20 agents corrects. Les en-têtes utilisent volontairement des SYNONYMES
   (« N° Matricule », « Nom et Prénoms », « Tél », « Affectation »...) pour
   vérifier que le mapping automatique les reconnaît. Une ligne de titre est
   placée au-dessus des en-têtes pour éprouver la détection automatique de
   la ligne d'en-tête.

2. import_personnel_avec_erreurs.xlsx
   12 lignes dont 7 fautives, chacune illustrant une règle de validation
   différente. Sert à vérifier que le mode simulation (dry-run) rejette les
   bonnes lignes en donnant le bon motif, et que les 5 lignes valides
   passent malgré tout.

3. import_mise_a_jour.xlsx
   8 agents déjà présents dans le fichier n°1, avec des valeurs modifiées
   (promotion, mutation, nouveau téléphone). Sert à comparer les quatre
   stratégies de fusion : UPSERT, INSERT_ONLY, UPDATE_ONLY, REPLACE.

Lancer avec :
    venv\\Scripts\\python.exe scripts\\generer_excel_exemple.py
"""

import sys
from datetime import date
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

DOSSIER_SORTIE = ROOT_DIR / "exemples"

# Palette « Light & Ember » transposée dans Excel
ORANGE = "F97316"
ORANGE_FONCE = "C2410C"
GRIS_CLAIR = "F5F5F4"
ROUGE_DOUX = "FEE2E2"

BORDURE_FINE = Border(
    left=Side(style="thin", color="E7E5E4"),
    right=Side(style="thin", color="E7E5E4"),
    top=Side(style="thin", color="E7E5E4"),
    bottom=Side(style="thin", color="E7E5E4"),
)


# ========================================================================
# STRUCTURES RÉELLES DE LA RÉGION DU HAMBOL
# (identiques à celles chargées par le seed, pour que le rattachement
#  se fasse sur des structures existantes et non sur des créations)
# ========================================================================
STRUCTURES = [
    "DRENAET de Katiola",
    "CAFOP Katiola",
    "Lycée Moderne de Katiola",
    "Lycée Moderne de Dabakala",
    "Lycée Moderne de Niakara",
    "Lycée Moderne de Tafiré",
    "Collège Moderne de Fronan",
    "Collège Moderne de Tortiya",
    "IEPP Katiola",
    "IEPP Dabakala 1",
    "IEPP Niakara",
    "IEPP Tafiré",
    "IEPP Fronan",
    "IEPP Tortiya",
    "IEPP Satama-Sokoura",
]


# ========================================================================
# JEU DE DONNÉES PRINCIPAL — 20 cadres administratifs
# ========================================================================
# Colonnes : matricule, nom_prenoms, sexe, ddn, lieu_naissance, situation,
#            telephone, email, emploi, grade, fonction, structure,
#            date_prise_service, date_affectation, residence, statut
AGENTS_VALIDES = [
    ("233329C", "OUATTARA Wahon Jean Baptiste", "M", date(1978, 3, 14), "Katiola",
     "Marié", "0707081420", "wahon.ouattara@menaet.ci",
     "Inspecteur de l'Enseignement Primaire", "A4", "Chef de Service RH",
     "DRENAET de Katiola", date(2003, 10, 1), date(2019, 9, 16), "Katiola", "Actif"),

    ("198745B", "KONE Salimata", "F", date(1981, 7, 22), "Dabakala",
     "Mariée", "0102334455", "salimata.kone@menaet.ci",
     "Inspecteur de l'Enseignement Primaire", "A4", "Secrétaire Général",
     "DRENAET de Katiola", date(2005, 10, 3), date(2020, 9, 14), "Katiola", "Actif"),

    ("204512D", "COULIBALY Adama", "M", date(1975, 11, 5), "Niakara",
     "Marié", "0546778899", "adama.coulibaly@menaet.ci",
     "Professeur de Lycée", "A3", "Directeur de CAFOP",
     "CAFOP Katiola", date(2001, 9, 17), date(2018, 9, 10), "Katiola", "Actif"),

    ("215678E", "TRAORE Ibrahim Souleymane", "M", date(1983, 2, 28), "Katiola",
     "Marié", "0708192021", "ibrahim.traore@menaet.ci",
     "Inspecteur de l'Enseignement Primaire", "A3", "Chef de Circonscription",
     "IEPP Katiola", date(2007, 10, 1), date(2021, 9, 13), "Katiola", "Actif"),

    ("221934F", "DIABATE Fatoumata", "F", date(1986, 5, 17), "Bouaké",
     "Célibataire", "0555443322", "fatoumata.diabate@menaet.ci",
     "Conseiller Pédagogique", "A2", "Conseiller Pédagogique",
     "IEPP Dabakala 1", date(2010, 10, 4), date(2019, 9, 16), "Dabakala", "Actif"),

    ("189023A", "SILUE Yacouba", "M", date(1972, 9, 3), "Korhogo",
     "Marié", "0102030405", "yacouba.silue@menaet.ci",
     "Inspecteur de l'Enseignement Secondaire", "A4", "Chef de Circonscription",
     "IEPP Niakara", date(1998, 10, 1), date(2017, 9, 11), "Niakara", "Actif"),

    ("240187G", "SORO Mariam Aïcha", "F", date(1990, 12, 11), "Katiola",
     "Mariée", "0787654321", "mariam.soro@menaet.ci",
     "Attaché d'Administration", "B3", "Chef de Bureau du Personnel",
     "DRENAET de Katiola", date(2014, 10, 6), date(2022, 9, 12), "Katiola", "Actif"),

    ("227845H", "YEO Bakary", "M", date(1984, 4, 9), "Tafiré",
     "Marié", "0141525354", "bakary.yeo@menaet.ci",
     "Professeur de Collège", "A2", "Censeur",
     "Lycée Moderne de Tafiré", date(2009, 9, 21), date(2020, 9, 14), "Tafiré", "Actif"),

    ("236901J", "TUO Awa", "F", date(1988, 8, 25), "Ferkessédougou",
     "Divorcée", "0596857412", "awa.tuo@menaet.ci",
     "Conseiller Pédagogique", "A2", "Conseiller Pédagogique",
     "IEPP Tafiré", date(2012, 10, 1), date(2021, 9, 13), "Tafiré", "Actif"),

    ("212340K", "DAGNOGO Moussa", "M", date(1980, 1, 30), "Dabakala",
     "Marié", "0708070605", "moussa.dagnogo@menaet.ci",
     "Professeur de Lycée", "A3", "Proviseur",
     "Lycée Moderne de Dabakala", date(2006, 9, 18), date(2019, 9, 16), "Dabakala", "Actif"),

    ("245672L", "BAKAYOKO Kadidja", "F", date(1992, 6, 7), "Katiola",
     "Célibataire", "0102938475", "kadidja.bakayoko@menaet.ci",
     "Secrétaire de Direction", "B2", "Secrétaire du Directeur Régional",
     "DRENAET de Katiola", date(2016, 10, 3), date(2022, 9, 12), "Katiola", "Actif"),

    ("207893M", "CISSE Lassina", "M", date(1977, 10, 19), "Niakara",
     "Marié", "0545362718", "lassina.cisse@menaet.ci",
     "Inspecteur de l'Enseignement Primaire", "A3", "Chef de Circonscription",
     "IEPP Tortiya", date(2002, 10, 1), date(2018, 9, 10), "Tortiya", "Actif"),

    ("231456N", "FOFANA Aminata", "F", date(1987, 3, 2), "Katiola",
     "Mariée", "0776655443", "aminata.fofana@menaet.ci",
     "Professeur de Collège", "A2", "Éducatrice",
     "Collège Moderne de Fronan", date(2011, 9, 19), date(2020, 9, 14), "Fronan", "Actif"),

    ("219087P", "KAMAGATE Drissa", "M", date(1982, 12, 24), "Tortiya",
     "Marié", "0708091011", "drissa.kamagate@menaet.ci",
     "Attaché d'Administration", "B3", "Chef de Service Comptabilité",
     "DRENAET de Katiola", date(2008, 10, 1), date(2021, 9, 13), "Katiola", "Actif"),

    ("242318Q", "SEKONGO Nadège", "F", date(1991, 9, 15), "Korhogo",
     "Célibataire", "0596041238", "nadege.sekongo@menaet.ci",
     "Conseiller Pédagogique", "A2", "Conseillère Pédagogique",
     "IEPP Fronan", date(2015, 10, 5), date(2022, 9, 12), "Fronan", "Actif"),

    ("196574R", "GNAGBO Serge Emmanuel", "M", date(1974, 5, 8), "Abidjan",
     "Marié", "0102030607", "serge.gnagbo@menaet.ci",
     "Professeur de Lycée", "A4", "Proviseur",
     "Lycée Moderne de Katiola", date(2000, 9, 18), date(2017, 9, 11), "Katiola", "Actif"),

    ("238765S", "OUEDRAOGO Alimata", "F", date(1989, 11, 28), "Katiola",
     "Mariée", "0787412589", "alimata.ouedraogo@menaet.ci",
     "Instituteur Ordinaire", "B3", "Directrice d'École",
     "IEPP Satama-Sokoura", date(2013, 10, 1), date(2021, 9, 13), "Satama-Sokoura", "Actif"),

    ("223019T", "KOFFI N'Guessan Bernard", "M", date(1985, 7, 4), "Bouaké",
     "Marié", "0546372819", "bernard.koffi@menaet.ci",
     "Professeur de Collège", "A2", "Principal",
     "Collège Moderne de Tortiya", date(2010, 9, 20), date(2019, 9, 16), "Tortiya", "Actif"),

    ("248902U", "TOURE Ramata", "F", date(1993, 2, 13), "Dabakala",
     "Célibataire", "0708112233", "ramata.toure@menaet.ci",
     "Adjoint Administratif", "C2", "Agent de Bureau",
     "DRENAET de Katiola", date(2017, 10, 2), date(2022, 9, 12), "Katiola", "Actif"),

    ("201765V", "ZAGBAYOU Célestin", "M", date(1976, 8, 21), "Daloa",
     "Marié", "0102837465", "celestin.zagbayou@menaet.ci",
     "Professeur de Lycée", "A3", "Censeur",
     "Lycée Moderne de Niakara", date(2003, 9, 22), date(2018, 9, 10), "Niakara", "Actif"),
]


# ========================================================================
# UTILITAIRES DE MISE EN FORME
# ========================================================================
def _ecrire_titre(ws, texte: str, nb_colonnes: int, ligne: int = 1):
    """Ligne de titre fusionnée au-dessus des en-têtes."""
    ws.cell(ligne, 1, texte)
    ws.merge_cells(
        start_row=ligne, start_column=1,
        end_row=ligne, end_column=nb_colonnes,
    )
    cellule = ws.cell(ligne, 1)
    cellule.font = Font(bold=True, size=13, color=ORANGE_FONCE)
    cellule.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[ligne].height = 26


def _ecrire_entetes(ws, entetes: list, ligne: int):
    """En-têtes sur fond orange, texte blanc."""
    for colonne, libelle in enumerate(entetes, start=1):
        cellule = ws.cell(ligne, colonne, libelle)
        cellule.font = Font(bold=True, color="FFFFFF", size=10)
        cellule.fill = PatternFill("solid", fgColor=ORANGE)
        cellule.alignment = Alignment(horizontal="center", vertical="center",
                                      wrap_text=True)
        cellule.border = BORDURE_FINE
    ws.row_dimensions[ligne].height = 32
    ws.freeze_panes = ws.cell(ligne + 1, 1)


def _ajuster_largeurs(ws, ligne_entetes: int):
    """Largeur de colonne adaptée au contenu, plafonnée."""
    for colonne in range(1, ws.max_column + 1):
        largeur_max = 10
        for ligne in range(ligne_entetes, ws.max_row + 1):
            valeur = ws.cell(ligne, colonne).value
            if valeur is not None:
                largeur_max = max(largeur_max, min(len(str(valeur)) + 2, 34))
        ws.column_dimensions[get_column_letter(colonne)].width = largeur_max


def _formater_lignes_donnees(ws, ligne_debut: int):
    """Bordures fines et format de date sur les lignes de données."""
    for ligne in range(ligne_debut, ws.max_row + 1):
        for colonne in range(1, ws.max_column + 1):
            cellule = ws.cell(ligne, colonne)
            cellule.border = BORDURE_FINE
            cellule.font = Font(size=10)
            if isinstance(cellule.value, date):
                cellule.number_format = "DD/MM/YYYY"
                cellule.alignment = Alignment(horizontal="center")


# ========================================================================
# FICHIER 1 — JEU VALIDE, EN-TÊTES EN SYNONYMES
# ========================================================================
def creer_fichier_valide(chemin: Path):
    """
    20 agents corrects.

    Les en-têtes sont volontairement des synonymes plutôt que les noms
    canoniques : c'est ainsi que se présentent les fichiers reçus des
    établissements, et cela vérifie le mapping automatique.
    Une colonne « Observations » non reconnue est ajoutée pour contrôler
    qu'elle est signalée sans bloquer l'import.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Personnel"

    entetes = [
        "N° Matricule",          # → matricule
        "Nom et Prénoms",        # → nom + prenoms (colonne combinée)
        "Sexe",                  # → sexe
        "Date de naissance",     # → date_naissance
        "Lieu de naissance",     # → lieu_naissance
        "Situation matrimoniale",  # → situation_matrimoniale
        "Tél",                   # → telephone
        "E-mail",                # → email
        "Emploi",                # → emploi
        "Catégorie",             # → grade
        "Fonction actuelle",     # → fonction
        "Affectation",           # → structure
        "Date de prise de service",  # → date_prise_service
        "Date d'affectation",    # → date_affectation
        "Résidence",             # → residence
        "Statut",                # → statut
        "Observations",          # non reconnue : doit être signalée, pas bloquante
    ]

    _ecrire_titre(
        ws,
        "DRENAET DE KATIOLA — ÉTAT NOMINATIF DES CADRES ADMINISTRATIFS "
        "(année scolaire 2026-2027)",
        len(entetes),
    )
    ws.cell(2, 1, "Service des Ressources Humaines — document de travail")
    ws.cell(2, 1).font = Font(italic=True, size=9, color="78716C")

    ligne_entetes = 4
    _ecrire_entetes(ws, entetes, ligne_entetes)

    for decalage, agent in enumerate(AGENTS_VALIDES):
        ligne = ligne_entetes + 1 + decalage
        for colonne, valeur in enumerate(agent, start=1):
            ws.cell(ligne, colonne, valeur)
        ws.cell(ligne, len(entetes), "")

    _formater_lignes_donnees(ws, ligne_entetes + 1)
    _ajuster_largeurs(ws, ligne_entetes)

    _ajouter_feuille_notice(wb, [
        "FICHIER 1 — JEU DE DONNÉES VALIDE",
        "",
        f"{len(AGENTS_VALIDES)} cadres administratifs, tous conformes.",
        "",
        "CE QUE CE FICHIER PERMET DE VÉRIFIER",
        "",
        "1. Détection automatique de la ligne d'en-tête",
        "   Les en-têtes sont en ligne 4, sous un titre et un sous-titre.",
        "   L'application doit les trouver seule.",
        "",
        "2. Reconnaissance des synonymes de colonnes",
        "   Aucun en-tête ne porte le nom interne du champ. Correspondances",
        "   attendues :",
        "     « N° Matricule »            -> matricule",
        "     « Nom et Prénoms »          -> nom + prénoms (séparés automatiquement)",
        "     « Tél »                     -> téléphone",
        "     « Catégorie »               -> grade",
        "     « Affectation »             -> structure",
        "     « Fonction actuelle »       -> fonction",
        "",
        "3. Séparation du nom et des prénoms",
        "   « OUATTARA Wahon Jean Baptiste » doit donner",
        "   nom = OUATTARA et prénoms = Wahon Jean Baptiste.",
        "   La convention est : le mot en MAJUSCULES est le nom.",
        "",
        "4. Colonne non reconnue",
        "   « Observations » ne correspond à aucun champ. Elle doit être",
        "   signalée dans l'écran de configuration SANS empêcher l'import.",
        "",
        "5. Rattachement aux structures existantes",
        "   Les 15 structures citées existent déjà en base : aucune création",
        "   ne doit avoir lieu.",
        "",
        "RÉSULTAT ATTENDU EN SIMULATION",
        f"   {len(AGENTS_VALIDES)} lignes valides, 0 rejet.",
    ])

    wb.save(chemin)
    return len(AGENTS_VALIDES)


# ========================================================================
# FICHIER 2 — CAS D'ERREUR
# ========================================================================
def creer_fichier_avec_erreurs(chemin: Path):
    """
    12 lignes dont 7 fautives, chacune ciblant une règle de validation.

    L'objectif est de vérifier que la simulation rejette précisément les
    lignes fautives, avec le bon motif, et laisse passer les 5 correctes.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Personnel"

    entetes = [
        "Matricule", "Nom", "Prénoms", "Sexe", "Date de naissance",
        "Téléphone", "Email", "Emploi", "Grade", "Fonction",
        "Structure", "Date de prise de service", "Statut",
        "ERREUR ATTENDUE",
    ]

    lignes = [
        # --- 5 lignes correctes ---
        ("250001A", "BAMBA", "Sekou", "M", date(1985, 4, 12), "0707010203",
         "sekou.bamba@menaet.ci", "Professeur de Collège", "A2", "Éducateur",
         "Collège Moderne de Fronan", date(2011, 10, 1), "Actif",
         "aucune — ligne valide"),

        ("250002B", "koulibaly", "aya marie", "féminin", date(1990, 8, 3), "01 02 03 04 05",
         "aya.koulibaly@menaet.ci", "Conseiller Pédagogique", "A2", "Conseillère",
         "IEPP Katiola", date(2015, 10, 5), "en service",
         "aucune — vérifie la normalisation : nom en majuscules, prénoms en "
         "Capitales, « féminin » -> F, « en service » -> Actif"),

        ("250003C", "N'DRI", "Kouamé Paul", "M", "17/06/1979", "0546778890",
         "paul.ndri@menaet.ci", "Professeur de Lycée", "A3", "Proviseur",
         "Lycée Moderne de Niakara", "01/10/2004", "Actif",
         "aucune — vérifie les dates au format texte JJ/MM/AAAA"),

        ("250004D", "GBAGBO", "Estelle", "F", date(1994, 1, 25), "0787001122",
         "", "Adjoint Administratif", "C2", "Agent de Bureau",
         "DRENAET de Katiola", date(2018, 10, 1), "Actif",
         "aucune — l'e-mail est facultatif, la ligne doit passer"),

        ("250005E", "ASSAMOI", "Jean-Claude", "M", date(1982, 11, 9), "0102030408",
         "jc.assamoi@menaet.ci", "Instituteur Ordinaire", "B3", "Directeur d'École",
         "Direction Régionale de Bouaké", date(2009, 10, 1), "Actif",
         "aucune — mais la structure est INCONNUE : elle doit être créée "
         "automatiquement, ce qui mérite d'être signalé"),

        # --- 7 lignes fautives ---
        ("", "KONATE", "Ali", "M", date(1988, 5, 5), "0708001122",
         "ali.konate@menaet.ci", "Professeur de Collège", "A2", "Éducateur",
         "IEPP Katiola", date(2013, 10, 1), "Actif",
         "REJET : matricule obligatoire manquant"),

        ("250007G", "", "Bintou", "F", date(1991, 3, 18), "0596001122",
         "bintou@menaet.ci", "Conseiller Pédagogique", "A2", "Conseillère",
         "IEPP Niakara", date(2016, 10, 1), "Actif",
         "REJET : nom obligatoire manquant"),

        ("250008H", "DOUMBIA", "Karim", "Masculin ?", date(1986, 7, 2), "0102001122",
         "karim.doumbia@menaet.ci", "Professeur de Lycée", "A3", "Censeur",
         "Lycée Moderne de Katiola", date(2010, 10, 1), "Actif",
         "REJET : sexe « Masculin ? » non reconnu (attendu M ou F)"),

        ("250009J", "SANOGO", "Mamadou", "M", "32/13/1985", "0546001122",
         "mamadou.sanogo@menaet.ci", "Instituteur Ordinaire", "B3", "Directeur",
         "IEPP Tafiré", date(2012, 10, 1), "Actif",
         "REJET : date de naissance invalide (32/13/1985 n'existe pas)"),

        ("250010K", "KOUASSI", "Affoué", "F", date(2015, 6, 10), "0787001133",
         "affoue.kouassi@menaet.ci", "Adjoint Administratif", "C2", "Agent",
         "DRENAET de Katiola", date(2020, 10, 1), "Actif",
         "REJET : agent âgé de 11 ans (minimum 18)"),

        ("250011L", "ZOUMANA", "Ibrahim", "M", date(1990, 4, 4), "0708001144",
         "ibrahim.zoumana@menaet.ci", "Professeur de Collège", "A2", "Éducateur",
         "Collège Moderne de Tortiya", date(1985, 10, 1), "Actif",
         "REJET : prise de service (1985) antérieure à la naissance (1990)"),

        ("250012M", "DIALLO", "Salif", "M", date(1987, 9, 21), "0102001155",
         "salif.diallo(at)menaet.ci", "Professeur de Lycée", "A3", "Proviseur",
         "Lycée Moderne de Dabakala", date(2011, 10, 1), "Actif",
         "REJET : e-mail au format invalide (« (at) » au lieu de « @ »)"),
    ]

    _ecrire_titre(ws, "JEU D'ESSAI — CONTRÔLE DES RÈGLES DE VALIDATION",
                  len(entetes))

    ligne_entetes = 3
    _ecrire_entetes(ws, entetes, ligne_entetes)

    for decalage, ligne_donnees in enumerate(lignes):
        ligne = ligne_entetes + 1 + decalage
        for colonne, valeur in enumerate(ligne_donnees, start=1):
            ws.cell(ligne, colonne, valeur)
        # Colorer en rouge doux les lignes censées être rejetées
        if str(ligne_donnees[-1]).startswith("REJET"):
            for colonne in range(1, len(entetes) + 1):
                ws.cell(ligne, colonne).fill = PatternFill("solid", fgColor=ROUGE_DOUX)

    _formater_lignes_donnees(ws, ligne_entetes + 1)
    _ajuster_largeurs(ws, ligne_entetes)

    nb_rejets = sum(1 for l in lignes if str(l[-1]).startswith("REJET"))
    nb_valides = len(lignes) - nb_rejets

    _ajouter_feuille_notice(wb, [
        "FICHIER 2 — CONTRÔLE DES RÈGLES DE VALIDATION",
        "",
        f"{len(lignes)} lignes : {nb_valides} valides, {nb_rejets} à rejeter.",
        "Les lignes sur fond rouge sont celles qui doivent être refusées.",
        "",
        "MODE D'EMPLOI",
        "",
        "1. Personnel > Importer depuis Excel",
        "2. Choisir ce fichier, puis lancer la SIMULATION",
        "3. Comparer le rapport à la colonne « ERREUR ATTENDUE »",
        "",
        "IMPORTANT : ne pas valider l'import après la simulation, sinon les",
        f"{nb_valides} lignes valides seront réellement créées en base.",
        "",
        "RÉSULTAT ATTENDU",
        "",
        f"   {nb_valides} lignes acceptées",
        f"   {nb_rejets} lignes rejetées, avec pour motifs :",
        "     - matricule obligatoire manquant",
        "     - nom obligatoire manquant",
        "     - sexe non reconnu",
        "     - date de naissance invalide",
        "     - âge inférieur à 18 ans",
        "     - prise de service antérieure à la naissance",
        "     - format d'e-mail invalide",
        "",
        "À SURVEILLER AUSSI",
        "",
        "   La colonne « ERREUR ATTENDUE » n'est pas un champ connu : elle",
        "   doit apparaître comme non reconnue, sans bloquer le traitement.",
        "",
        "   La ligne 250005E cite « Direction Régionale de Bouaké », qui",
        "   n'existe pas en base. L'application crée les structures inconnues",
        "   automatiquement : vérifier qu'elle apparaît ensuite dans la liste",
        "   des structures. C'est le comportement voulu, mais il mérite",
        "   attention car une faute de frappe dans un nom d'établissement",
        "   crée une structure en double.",
    ])

    wb.save(chemin)
    return nb_valides, nb_rejets


# ========================================================================
# FICHIER 3 — MISE À JOUR
# ========================================================================
def creer_fichier_mise_a_jour(chemin: Path):
    """
    8 agents du fichier n°1, avec des valeurs modifiées, plus 2 nouveaux.

    Permet de distinguer concrètement les quatre stratégies de fusion.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Personnel"

    entetes = [
        "Matricule", "Nom et Prénoms", "Sexe", "Emploi", "Grade",
        "Fonction", "Structure", "Téléphone", "Statut",
        "CHANGEMENT PAR RAPPORT AU FICHIER 1",
    ]

    lignes = [
        ("233329C", "OUATTARA Wahon Jean Baptiste", "M",
         "Inspecteur de l'Enseignement Primaire", "A4",
         "Directeur Régional", "DRENAET de Katiola", "0707081420", "Actif",
         "promotion : Chef de Service RH -> Directeur Régional"),

        ("198745B", "KONE Salimata", "F",
         "Inspecteur de l'Enseignement Primaire", "A4",
         "Secrétaire Général", "DRENAET de Katiola", "0102334466", "Actif",
         "nouveau numéro de téléphone (…455 -> …466)"),

        ("221934F", "DIABATE Fatoumata", "F",
         "Inspecteur de l'Enseignement Primaire", "A3",
         "Chef de Circonscription", "IEPP Fronan", "0555443322", "Actif",
         "triple changement : emploi, grade et mutation vers IEPP Fronan"),

        ("227845H", "YEO Bakary", "M",
         "Professeur de Collège", "A2",
         "Proviseur", "Lycée Moderne de Tafiré", "0141525354", "Actif",
         "promotion : Censeur -> Proviseur"),

        ("236901J", "TUO Awa", "F",
         "Conseiller Pédagogique", "A2",
         "Conseiller Pédagogique", "IEPP Tafiré", "0596857412", "En congé",
         "changement de statut : Actif -> En congé"),

        ("212340K", "DAGNOGO Moussa", "M",
         "Professeur de Lycée", "A3",
         "Proviseur", "Lycée Moderne de Dabakala", "0708070605", "Muté",
         "changement de statut : Actif -> Muté"),

        ("207893M", "CISSE Lassina", "M",
         "Inspecteur de l'Enseignement Primaire", "A4",
         "Chef de Circonscription", "IEPP Tortiya", "0545362718", "Actif",
         "avancement de grade : A3 -> A4"),

        ("196574R", "GNAGBO Serge Emmanuel", "M",
         "Professeur de Lycée", "A4",
         "Proviseur", "Lycée Moderne de Katiola", "0102030607", "Retraité",
         "changement de statut : Actif -> Retraité"),

        ("251001W", "ADOU Yao Vincent", "M",
         "Professeur de Collège", "A2",
         "Éducateur", "Collège Moderne de Fronan", "0708445566", "Actif",
         "AGENT NOUVEAU : absent du fichier 1"),

        ("251002X", "BROU Akissi Céline", "F",
         "Secrétaire de Direction", "B2",
         "Secrétaire", "IEPP Katiola", "0102556677", "Actif",
         "AGENT NOUVEAU : absent du fichier 1"),
    ]

    _ecrire_titre(ws, "JEU D'ESSAI — MISE À JOUR ET STRATÉGIES DE FUSION",
                  len(entetes))

    ligne_entetes = 3
    _ecrire_entetes(ws, entetes, ligne_entetes)

    for decalage, ligne_donnees in enumerate(lignes):
        ligne = ligne_entetes + 1 + decalage
        for colonne, valeur in enumerate(ligne_donnees, start=1):
            ws.cell(ligne, colonne, valeur)
        if "NOUVEAU" in str(ligne_donnees[-1]):
            for colonne in range(1, len(entetes) + 1):
                ws.cell(ligne, colonne).fill = PatternFill("solid", fgColor=GRIS_CLAIR)

    _formater_lignes_donnees(ws, ligne_entetes + 1)
    _ajuster_largeurs(ws, ligne_entetes)

    _ajouter_feuille_notice(wb, [
        "FICHIER 3 — MISE À JOUR ET STRATÉGIES DE FUSION",
        "",
        "8 agents déjà importés (fichier 1) avec des valeurs modifiées,",
        "et 2 agents nouveaux (sur fond gris).",
        "",
        "PRÉREQUIS : avoir importé le fichier 1 auparavant.",
        "",
        "CE QUE CHAQUE STRATÉGIE DOIT PRODUIRE",
        "",
        "UPSERT (recommandé au quotidien)",
        "   met à jour les 8 agents existants",
        "   crée les 2 nouveaux",
        "   -> 8 modifications, 2 créations",
        "",
        "INSERT_ONLY (n'ajouter que le nouveau personnel)",
        "   ignore les 8 agents existants",
        "   crée les 2 nouveaux",
        "   -> 0 modification, 2 créations, 8 ignorés",
        "",
        "UPDATE_ONLY (corriger sans rien ajouter)",
        "   met à jour les 8 agents existants",
        "   ignore les 2 nouveaux",
        "   -> 8 modifications, 0 création, 2 ignorés",
        "",
        "REPLACE (à manipuler avec précaution)",
        "   vide la structure concernée avant de réimporter.",
        "   À réserver à une reprise complète des données d'un établissement,",
        "   et à tester seulement après une sauvegarde de la base.",
        "",
        "MÉTHODE DE VÉRIFICATION",
        "",
        "1. Lancer la SIMULATION et lire le décompte annoncé",
        "2. Le comparer au tableau ci-dessus",
        "3. Valider, puis contrôler dans la liste du Personnel",
        "   Exemple : le matricule 233329C doit afficher",
        "   « Directeur Régional » et non plus « Chef de Service RH ».",
        "",
        "La colonne « CHANGEMENT PAR RAPPORT AU FICHIER 1 » indique, ligne",
        "par ligne, ce qui doit avoir bougé.",
    ])

    wb.save(chemin)
    return len(lignes)


# ========================================================================
# FEUILLE DE NOTICE
# ========================================================================
def _ajouter_feuille_notice(wb: Workbook, lignes: list):
    """Ajoute une feuille « Mode d'emploi » lisible sans outil externe."""
    ws = wb.create_sheet("Mode d'emploi")
    ws.column_dimensions["A"].width = 82

    for index, texte in enumerate(lignes, start=1):
        cellule = ws.cell(index, 1, texte)
        if index == 1:
            cellule.font = Font(bold=True, size=13, color=ORANGE_FONCE)
        elif texte.isupper() and texte.strip():
            cellule.font = Font(bold=True, size=10, color=ORANGE_FONCE)
        elif texte.startswith("   "):
            cellule.font = Font(size=10, color="44403C")
        else:
            cellule.font = Font(size=10)
        cellule.alignment = Alignment(vertical="top", wrap_text=False)


# ========================================================================
def main():
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

    fichier1 = DOSSIER_SORTIE / "import_personnel_valide.xlsx"
    fichier2 = DOSSIER_SORTIE / "import_personnel_avec_erreurs.xlsx"
    fichier3 = DOSSIER_SORTIE / "import_mise_a_jour.xlsx"

    nb1 = creer_fichier_valide(fichier1)
    nb_valides, nb_rejets = creer_fichier_avec_erreurs(fichier2)
    nb3 = creer_fichier_mise_a_jour(fichier3)

    print(f"Dossier : {DOSSIER_SORTIE}\n")
    print(f"  {fichier1.name:<40} {nb1} agents valides")
    print(f"  {fichier2.name:<40} {nb_valides} valides / {nb_rejets} a rejeter")
    print(f"  {fichier3.name:<40} {nb3} lignes (8 maj + 2 nouveaux)")
    print("\nChaque classeur contient une feuille « Mode d'emploi ».")
    return 0


if __name__ == "__main__":
    sys.exit(main())
