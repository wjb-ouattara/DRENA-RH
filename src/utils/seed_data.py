"""
========================================================================
DRENAET-RH — Génération de données fictives (seed)
========================================================================
Au premier lancement, l'app génère :
- Les 19 structures de référence (DRENAET, CAFOP, lycées, IEPP, collèges)
- 3 utilisateurs (admin + 2 opérateurs)
- 50-100 agents fictifs réalistes (noms ivoiriens, matricules officiels)

⚠️ IMPORTANT : ces données sont FICTIVES. Le Service RH remplacera
par ses vraies données lors de la mise en production.
"""

import random
import bcrypt
from datetime import date, timedelta
from typing import List

from config import settings
from config.constants import (
    STRUCTURES_INITIALES, EMPLOIS, FONCTIONS, STATUTS_PERSONNEL,
    NOMS_IVOIRIENS, PRENOMS_MASCULINS, PRENOMS_FEMININS,
)
from src.models import (
    get_session, init_db,
    Structure, Personnel, Utilisateur,
)


# ========================================================================
# 1. SEED DES UTILISATEURS PAR DÉFAUT
# ========================================================================
def seed_users() -> int:
    """
    Crée les 3 comptes utilisateurs par défaut (idempotent).
    Retourne le nombre d'utilisateurs créés.
    """
    nb_crees = 0
    with get_session() as db:
        for user_data in settings.DEFAULT_USERS:
            # Vérifier si l'utilisateur existe déjà
            existing = db.query(Utilisateur).filter_by(login=user_data["login"]).first()
            if existing:
                continue

            # Hasher le mot de passe
            password_hash = bcrypt.hashpw(
                user_data["password"].encode(),
                bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
            ).decode()

            user = Utilisateur(
                login=user_data["login"],
                mot_de_passe_hash=password_hash,
                nom_complet=user_data["nom_complet"],
                role=user_data["role"],
                doit_changer_mdp=True,  # Force le changement au 1er login
            )
            db.add(user)
            nb_crees += 1

    return nb_crees


# ========================================================================
# 2. SEED DES STRUCTURES DE RÉFÉRENCE
# ========================================================================
def seed_structures() -> int:
    """
    Crée les 19 structures de la DRENAET de Katiola (idempotent).
    Retourne le nombre de structures créées.
    """
    nb_crees = 0
    with get_session() as db:
        for s_data in STRUCTURES_INITIALES:
            # Vérifier si elle existe déjà
            existing = db.query(Structure).filter_by(nom=s_data["nom"]).first()
            if existing:
                continue

            structure = Structure(
                nom=s_data["nom"],
                type=s_data["type"],
                localite=s_data["localite"],
            )
            db.add(structure)
            nb_crees += 1

    return nb_crees


# ========================================================================
# 3. GÉNÉRATION DE MATRICULES IVOIRIENS RÉALISTES
# ========================================================================
def generer_matricule(rng: random.Random, deja_pris: set) -> str:
    """
    Génère un matricule au format ivoirien : 6 chiffres + 1 lettre.
    Exemples : 233329C, 249929N
    """
    while True:
        nombres = rng.randint(100000, 999999)
        lettre = rng.choice("ABCDEFGHIJKLMNPQRSTUVWXYZ")  # pas de O pour pas confondre avec 0
        matricule = f"{nombres}{lettre}"
        if matricule not in deja_pris:
            deja_pris.add(matricule)
            return matricule


# ========================================================================
# 4. SEED DES AGENTS FICTIFS
# ========================================================================
def seed_personnel(nb_agents: int = 80, seed: int = 42) -> int:
    """
    Génère N agents fictifs avec noms ivoiriens et profils variés.

    Distribution réaliste :
    - 60% des agents dans les écoles primaires / IEPP (instituteurs)
    - 25% dans les lycées/collèges (professeurs)
    - 10% au CAFOP (encadrement pédagogique)
    - 5% à la DRENAET (administration)

    Args:
        nb_agents: Nombre d'agents à créer
        seed: Graine de génération (pour reproductibilité)

    Retourne le nombre d'agents créés.
    """
    rng = random.Random(seed)
    nb_crees = 0
    matricules_pris = set()

    with get_session() as db:
        # Récupérer les structures existantes par type
        structures_par_type = {}
        for s in db.query(Structure).all():
            structures_par_type.setdefault(s.type, []).append(s)
            matricules_pris.update(
                {p.matricule for p in db.query(Personnel.matricule).all()}
            )

        if not structures_par_type:
            print("⚠ Aucune structure trouvée. Lancez seed_structures() d'abord.")
            return 0

        # Distribution des affectations
        repartition = [
            ("IEPP", 0.50),                # 50% dans les IEPP (instituteurs primaire)
            ("Lycée", 0.20),       # 20% dans les lycées
            ("Collège", 0.10),             # 10% dans les collèges
            ("CAFOP", 0.10),               # 10% au CAFOP
            ("DRENAET", 0.05), # 5% à la DRENAET
            ("EPP", 0.05),  # 5% en école primaire (rare car données via IEPP)
        ]

        for i in range(nb_agents):
            # --- Choix du type de structure selon la répartition ---
            r = rng.random()
            cumul = 0
            type_choisi = "IEPP"
            for type_struct, prop in repartition:
                cumul += prop
                if r <= cumul:
                    type_choisi = type_struct
                    break

            # Si pas de structure de ce type, fallback sur IEPP
            structures_dispo = structures_par_type.get(type_choisi, [])
            if not structures_dispo:
                structures_dispo = structures_par_type.get("IEPP", [])
                type_choisi = "IEPP"
            structure = rng.choice(structures_dispo)

            # --- Choix de l'emploi selon la structure ---
            if type_choisi == "IEPP" or type_choisi == "EPP":
                emploi = rng.choices(
                    ["Instituteur", "Instituteur Adjoint", "Éducateur Préscolaire"],
                    weights=[60, 30, 10]
                )[0]
            elif type_choisi == "Lycée":
                emploi = "Professeur de Lycée"
            elif type_choisi == "Collège":
                emploi = rng.choice(["Professeur de Collège", "Professeur de Lycée"])
            elif type_choisi == "CAFOP":
                emploi = rng.choices(
                    ["PROFESSEUR DE CAFOP", "Inspecteur de l'Éducation", "Conseiller Pédagogique",
                     "Inspecteur Principal"],
                    weights=[60, 20, 15, 5]
                )[0]
            elif type_choisi == "DRENAET":
                emploi = rng.choice([
                    "Inspecteur Principal", "Inspecteur de l'Éducation",
                    "Attaché des Services Financiers",
                    "Secrétaire Administratif", "Agent Administratif"
                ])
            else:
                emploi = "Instituteur"

            # --- Fonction (seul ~20% des agents ont une fonction d'encadrement) ---
            fonction = None
            if rng.random() < 0.20:
                if "IEPP" in type_choisi or "École" in type_choisi:
                    fonction = rng.choice([
                        "Directeur d'école", "Adjoint au Directeur d'école",
                        "Enseignant de classe", "Conseiller Pédagogique de Secteur"
                    ])
                elif type_choisi in ("Lycée", "Collège"):
                    fonction = rng.choice(["Proviseur", "Censeur du Lycée",
                                            "Principal du Collège", "Surveillant Général"])
                elif type_choisi == "CAFOP":
                    fonction = rng.choice(["Directeur du CAFOP",
                                            "Adjoint au Directeur de CAFOP", "Censeur"])
                elif type_choisi == "DRENAET":
                    fonction = rng.choice(["Directeur Régional",
                                            "Chef de Service Ressources Humaines",
                                            "Chef de Service Pédagogie"])

            # --- Identité ---
            sexe = rng.choices(["M", "F"], weights=[55, 45])[0]
            nom = rng.choice(NOMS_IVOIRIENS)
            if sexe == "M":
                # 1 ou 2 prénoms
                if rng.random() < 0.3:
                    prenoms = f"{rng.choice(PRENOMS_MASCULINS)} {rng.choice(PRENOMS_MASCULINS)}"
                else:
                    prenoms = rng.choice(PRENOMS_MASCULINS)
            else:
                if rng.random() < 0.3:
                    prenoms = f"{rng.choice(PRENOMS_FEMININS)} {rng.choice(PRENOMS_FEMININS)}"
                else:
                    prenoms = rng.choice(PRENOMS_FEMININS)

            # --- Âge entre 25 et 60 ans ---
            age = rng.randint(25, 60)
            annee_naissance = date.today().year - age
            mois_naissance = rng.randint(1, 12)
            jour_naissance = rng.randint(1, 28)
            date_naissance = date(annee_naissance, mois_naissance, jour_naissance)

            # --- Date de prise de service ---
            annees_anciennete = rng.randint(1, min(age - 22, 35))
            date_prise_service = date.today() - timedelta(days=annees_anciennete * 365)

            # --- Téléphone ivoirien (format 07, 05, 01) ---
            prefixe = rng.choice(["07", "05", "01"])
            telephone = f"{prefixe} {rng.randint(10,99)} {rng.randint(10,99)} {rng.randint(10,99)} {rng.randint(10,99)}"

            # --- Statut ---
            statut = rng.choices(
                ["Actif", "En congé", "En mission", "En détachement"],
                weights=[88, 7, 4, 1]
            )[0]

            # --- Création de l'agent ---
            agent = Personnel(
                matricule=generer_matricule(rng, matricules_pris),
                nom=nom,
                prenoms=prenoms,
                sexe=sexe,
                date_naissance=date_naissance,
                lieu_naissance=structure.localite,
                emploi=emploi,
                fonction=fonction,
                structure_id=structure.id,
                date_prise_service=date_prise_service,
                telephone=telephone,
                residence=structure.localite,
                statut=statut,
                nationalite="Ivoirienne",
            )
            db.add(agent)
            nb_crees += 1

    return nb_crees


# ========================================================================
# 5. MAIN — Seed complet
# ========================================================================
def seed_all(nb_agents: int = 80, force: bool = False) -> dict:
    """
    Initialise complètement la base avec les données fictives.

    Args:
        nb_agents: Nombre d'agents fictifs à créer
        force: Si True, recrée la BD depuis zéro (DANGER)

    Retourne un dict avec les compteurs.
    """
    if force:
        from src.models import drop_db
        drop_db()
        print("  ⚠ Base supprimée (force=True)")

    init_db()
    print("  ✓ Schéma BD créé")

    nb_users = seed_users()
    print(f"  ✓ {nb_users} utilisateur(s) créé(s)")

    nb_structs = seed_structures()
    print(f"  ✓ {nb_structs} structure(s) créée(s)")

    nb_pers = seed_personnel(nb_agents=nb_agents)
    print(f"  ✓ {nb_pers} agent(s) fictif(s) généré(s)")

    return {
        "utilisateurs": nb_users,
        "structures": nb_structs,
        "personnel": nb_pers,
    }


if __name__ == "__main__":
    print("=" * 72)
    print("  SEED DRENAET-RH — Génération des données fictives")
    print("=" * 72)
    print()
    result = seed_all(nb_agents=80, force=True)
    print()
    print("=" * 72)
    print(f"  ✅ Seed terminé : {result}")
    print("=" * 72)
