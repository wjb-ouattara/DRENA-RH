"""
Constantes métier de l'application DRENAET-RH.

Listes utilisées dans les formulaires (emplois, fonctions, motifs...).
Centralisées ici pour faciliter les évolutions.
"""

# ============================================================
# TYPES DE STRUCTURES
# ============================================================
TYPES_STRUCTURE = [
    "CAFOP",           # Centre d'Animation et de Formation Pédagogique
    "Lycée",
    "Collège",
    "Lycée-Collège",
    "IEPP",            # Inspection de l'Enseignement Préscolaire et Primaire
    "EPP",             # École Primaire Publique
    "École Préscolaire",
    "DRENAET",         # Direction Régionale
    "Service",
    "Autre",
]

# ============================================================
# EMPLOIS (corps de métier de l'éducation nationale)
# ============================================================
EMPLOIS = [
    # Encadrement et inspection
    "Inspecteur Principal",
    "Inspecteur de l'Éducation",
    "Inspecteur Pédagogique",
    "Conseiller Pédagogique",

    # Enseignement secondaire
    "Professeur de Lycée",
    "Professeur de Collège",
    "Professeur Technique",
    "PROFESSEUR DE CAFOP",

    # Enseignement primaire
    "Instituteur",
    "Instituteur Adjoint",
    "Éducateur Préscolaire",

    # Administration
    "Administrateur des Services Financiers",
    "Attaché des Services Financiers",
    "Secrétaire Administratif",
    "Agent Administratif",

    # Autres
    "Autre",
]

# ============================================================
# FONCTIONS (rôles administratifs)
# ============================================================
FONCTIONS = [
    # Direction régionale
    "Directeur Régional",
    "Sous-Directeur",
    "Chef de Service",
    "Chef de Service RH",

    # Établissements secondaires
    "Proviseur",
    "Censeur",
    "Surveillant Général",
    "Directeur d'études",

    # CAFOP
    "Directeur du CAFOP",
    "Adjoint au Directeur de CAFOP",

    # Primaire / IEPP
    "Inspecteur",
    "Chef de Circonscription",
    "Directeur",
    "Adjoint au Directeur",
    "Enseignant de classe",

    # Sans fonction administrative
    "Sans fonction administrative",
    "Autre",
]

# ============================================================
# DISCIPLINES (pour les enseignants du secondaire)
# ============================================================
DISCIPLINES = [
    "Mathématiques",
    "Physique-Chimie",
    "Sciences de la Vie et de la Terre",
    "Français",
    "Anglais",
    "Espagnol",
    "Allemand",
    "Histoire-Géographie",
    "Philosophie",
    "Économie",
    "Éducation Physique et Sportive",
    "Arts Plastiques",
    "Musique",
    "Informatique",
    "Technologie",
    "Comptabilité",
    "Économie Familiale et Sociale",
    "Autre",
]

# ============================================================
# SEXE
# ============================================================
SEXES = ["M", "F"]

# ============================================================
# STATUTS DU PERSONNEL
# ============================================================
STATUTS = [
    "actif",
    "conge",         # En congé
    "mutation",      # En cours de mutation
    "detachement",   # Détaché
    "disponibilite", # En disponibilité
    "retraite",
    "decede",
]

STATUT_LABELS = {
    "actif":         "En activité",
    "conge":         "En congé",
    "mutation":      "En mutation",
    "detachement":   "Détaché",
    "disponibilite": "En disponibilité",
    "retraite":      "À la retraite",
    "decede":        "Décédé",
}

# ============================================================
# TYPES DE DOCUMENTS GÉNÉRABLES
# ============================================================
TYPES_DOCUMENT = {
    "autorisation_absence": {
        "label":         "Demande d'Autorisation d'Absence",
        "template":      "autorisation_absence.docx",
        "output_folder": "autorisations",
        "icon":          "fa5s.calendar-times",
    },
    "ordre_mission": {
        "label":         "Ordre de Mission",
        "template":      "ordre_de_mission.docx",
        "output_folder": "ordres_mission",
        "icon":          "fa5s.route",
    },
    "attestation_service": {
        "label":         "Attestation de Service",
        "template":      "attestation_service.docx",
        "output_folder": "attestations",
        "icon":          "fa5s.file-alt",
    },
    "decision": {
        "label":         "Décision Administrative",
        "template":      "decision.docx",
        "output_folder": "decisions",
        "icon":          "fa5s.gavel",
    },
}

# ============================================================
# MOTIFS D'ABSENCE COURANTS
# ============================================================
MOTIFS_ABSENCE = [
    "Maladie",
    "Convalescence",
    "Maternité",
    "Décès dans la famille",
    "Mariage",
    "Convocation administrative",
    "Stage de formation",
    "Mission",
    "Examen / Concours",
    "Permission exceptionnelle",
    "Courses administratives",
    "Autre",
]

# ============================================================
# MOYENS DE DÉPLACEMENT (pour ordre de mission)
# ============================================================
MOYENS_DEPLACEMENT = [
    "Véhicule de service",
    "Véhicule personnel",
    "Transport en commun",
    "Avion",
    "Autre",
]

# ============================================================
# RÔLES UTILISATEURS
# ============================================================
ROLES = ["admin", "operateur"]

ROLE_LABELS = {
    "admin":     "Administrateur",
    "operateur": "Opérateur",
}

ROLE_PERMISSIONS = {
    "admin": [
        "personnel_create", "personnel_edit", "personnel_delete",
        "document_generate", "document_view", "document_delete",
        "user_manage", "backup_restore", "settings_edit",
    ],
    "operateur": [
        "personnel_view", "personnel_edit",
        "document_generate", "document_view",
    ],
}

# ============================================================
# ANNÉE SCOLAIRE (calculée auto si non précisée)
# ============================================================
ANNEES_SCOLAIRES = [
    "2024-2025",
    "2025-2026",
    "2026-2027",
    "2027-2028",
]

# ============================================================
# MOIS DE L'ANNÉE SCOLAIRE (septembre à août)
# ============================================================
MOIS = [
    "Septembre", "Octobre", "Novembre", "Décembre",
    "Janvier", "Février", "Mars", "Avril",
    "Mai", "Juin", "Juillet", "Août",
]


def get_annee_scolaire_courante() -> str:
    """
    Renvoie l'année scolaire en cours selon la date du jour.
    L'année scolaire commence en septembre.
    Exemple : en juin 2026 → "2025-2026" ; en octobre 2026 → "2026-2027".
    """
    from datetime import date
    today = date.today()
    if today.month >= 9:
        return f"{today.year}-{today.year + 1}"
    return f"{today.year - 1}-{today.year}"


# ============================================================
# STRUCTURES DE LA RÉGION HAMBOL (préchargées au seed)
# ============================================================
STRUCTURES_INITIALES = [
    # Direction Régionale
    {"nom": "DRENAET de Katiola", "type": "DRENAET", "localite": "Katiola"},

    # CAFOP
    {"nom": "CAFOP Katiola", "type": "CAFOP", "localite": "Katiola"},

    # Lycées de la région Hambol
    {"nom": "Lycée Moderne de Katiola", "type": "Lycée", "localite": "Katiola"},
    {"nom": "Lycée Moderne de Dabakala", "type": "Lycée", "localite": "Dabakala"},
    {"nom": "Lycée Moderne de Niakara", "type": "Lycée", "localite": "Niakara"},
    {"nom": "Lycée Moderne de Boniérédougou", "type": "Lycée", "localite": "Boniérédougou"},
    {"nom": "Lycée Moderne de Tafiré", "type": "Lycée", "localite": "Tafiré"},

    # Collèges
    {"nom": "Collège Moderne de Fronan", "type": "Collège", "localite": "Fronan"},
    {"nom": "Collège Moderne de Tortiya", "type": "Collège", "localite": "Tortiya"},
    {"nom": "Collège Moderne de Satama-Sokoura", "type": "Collège", "localite": "Satama-Sokoura"},

    # IEPP (9 inspections)
    {"nom": "IEPP Boniérédougou", "type": "IEPP", "localite": "Boniérédougou"},
    {"nom": "IEPP Dabakala 1", "type": "IEPP", "localite": "Dabakala"},
    {"nom": "IEPP Dabakala 2", "type": "IEPP", "localite": "Dabakala"},
    {"nom": "IEPP Fronan", "type": "IEPP", "localite": "Fronan"},
    {"nom": "IEPP Katiola", "type": "IEPP", "localite": "Katiola"},
    {"nom": "IEPP Niakara", "type": "IEPP", "localite": "Niakara"},
    {"nom": "IEPP Satama-Sokoura", "type": "IEPP", "localite": "Satama-Sokoura"},
    {"nom": "IEPP Tafiré", "type": "IEPP", "localite": "Tafiré"},
    {"nom": "IEPP Tortiya", "type": "IEPP", "localite": "Tortiya"},
]

# ============================================================
# STATUTS DU PERSONNEL
# ============================================================
STATUTS_PERSONNEL = [
    "Actif", "En congé", "En mission", "En détachement",
    "En mutation", "Retraité", "Décédé"
]

# ============================================================
# NOMS IVOIRIENS (pour génération de données fictives)
# ============================================================
NOMS_IVOIRIENS = [
    "ABOA", "ACHI", "ADJI", "AKA", "AKE", "AKO", "AKPA", "ALLA",
    "ASSI", "ATSE", "BAMBA", "BLE", "BROU", "COULIBALY", "DIABATE",
    "DIALLO", "DIARRA", "DIOMANDE", "DOSSO", "EHOUMAN", "ESSO",
    "FOFANA", "GBAGBO", "GBANGBO", "GNAGNE", "GOORE", "GOUANE", "GUEHI",
    "HABA", "HIE", "KABA", "KAMAGATE", "KAMARA", "KEITA", "KOFFI",
    "KOKO", "KONE", "KONAN", "KOUADIO", "KOUAKOU", "KOUAME", "KOUASSI",
    "LIDA", "LOUA", "MEITE", "MOUSSA", "NDA", "NDRI", "N'GUESSAN",
    "OUATTARA", "SACKO", "SANGARE", "SANOGO", "SAVANE", "SEKA",
    "SEKONGO", "SIDIBE", "SILUE", "SISSOKO", "SORO", "TANO", "TIA",
    "TOURE", "TRAORE", "VEH", "WODIE", "YAO", "YEO", "YOBOUE",
    "ZADI", "ZAH", "ZAMBLE", "ZOH"
]

PRENOMS_MASCULINS = [
    "Abdoulaye", "Abou", "Adama", "Ali", "Amadou", "Aboubacar", "Bakary",
    "Bourahima", "Brahima", "Cheick", "Daouda", "David", "Dramane",
    "Eric", "Fabrice", "Gérard", "Guillaume", "Habib", "Hamed",
    "Ibrahim", "Idriss", "Issa", "Issouf", "Jacques", "Jean",
    "Karim", "Kassoum", "Konan", "Lacina", "Lamine", "Mamadou",
    "Marcellin", "Marius", "Martin", "Mathurin", "Maurice", "Mohamed",
    "Moussa", "Olivier", "Pascal", "Patrice", "Patrick", "Paul",
    "Pierre", "Prosper", "Raymond", "Roger", "Sékou", "Serge",
    "Souleymane", "Sylvain", "Théodore", "Tiémoko", "Vincent", "Yacouba", "Yves"
]

PRENOMS_FEMININS = [
    "Adèle", "Adjoua", "Affoussiata", "Aïcha", "Akissi", "Aminata",
    "Anne", "Antoinette", "Aya", "Beatrice", "Brigitte", "Carine",
    "Cécile", "Christelle", "Claire", "Clarisse", "Constance",
    "Delphine", "Esther", "Eugénie", "Fanta", "Fatim", "Fatou",
    "Fatoumata", "Florence", "Gisèle", "Henriette", "Irène", "Jeanne",
    "Joëlle", "Joséphine", "Justine", "Kadidja", "Khadija", "Léa",
    "Léontine", "Lucienne", "Mai", "Mama", "Mariam", "Marie",
    "Mariétou", "Marguerite", "Mireille", "Monique", "Nadège", "Odile",
    "Olga", "Pascaline", "Rachelle", "Raïssa", "Régine", "Rita",
    "Rokia", "Rose", "Salimata", "Sanata", "Sandrine", "Sarah",
    "Sidonie", "Solange", "Sylvie", "Thérèse", "Véronique", "Yvonne"
]
