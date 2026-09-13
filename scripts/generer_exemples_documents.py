"""
========================================================================
DRENAET-RH — Génération des 8 documents PDF d'exemple
========================================================================
Produit un exemplaire de chacun des 8 documents officiels, renseigné avec
des données réalistes de la région du Hambol, afin de contrôler la mise en
page, l'en-tête officiel, le code-barres et le bloc de signature sans avoir
à ressaisir les formulaires un par un.

Les PDF sont écrits dans le dossier des documents générés
(settings.OUTPUT_DIR, soit `output/<année scolaire>/<type>/` en
développement), exactement comme s'ils avaient été produits par
l'interface. Ils sont donc aussi enregistrés dans l'historique des
documents et consomment un numéro officiel — c'est voulu : cela permet de
vérifier également la numérotation et la traçabilité.

Prérequis : au moins un agent en base. Le script choisit de préférence un
agent du fichier d'exemple `import_personnel_valide.xlsx`.

Lancer avec :
    venv\\Scripts\\python.exe scripts\\generer_exemples_documents.py
"""

import shutil
import sys
from datetime import date
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import settings
from src.models import init_db, get_session, Personnel
from src.services.document_generator import DocumentGenerator

# Les 8 templates officiels
from src.services.document_templates.autorisation_absence import (
    AutorisationAbsenceTemplate,
)
from src.services.document_templates.ordre_mission import OrdreMissionTemplate
from src.services.document_templates.attestation_travail import (
    AttestationTravailTemplate,
)
from src.services.document_templates.attestation_presence import (
    AttestationPresenceTemplate,
)
from src.services.document_templates.titre_conges import TitreCongesTemplate
from src.services.document_templates.certificat_prise_service import (
    CertificatPriseServiceTemplate,
)
from src.services.document_templates.certificat_cessation import (
    CertificatCessationTemplate,
)
from src.services.document_templates.fiche_mutation import FicheMutationTemplate


# Matricules issus de exemples/import_personnel_valide.xlsx
MATRICULE_PRINCIPAL = "233329C"   # OUATTARA Wahon Jean Baptiste
MATRICULE_INTERIM = "240187G"     # SORO Mariam Aïcha
MATRICULE_SECONDAIRE = "221934F"  # DIABATE Fatoumata

# Copie de courtoisie des PDF, sous des noms explicites, pour consultation
DOSSIER_EXEMPLES = ROOT_DIR / "exemples" / "documents"


def _trouver_agent(db, matricule: str):
    """Cherche un agent par matricule, sinon retourne le premier disponible."""
    agent = db.query(Personnel).filter_by(matricule=matricule).first()
    if agent is None:
        agent = db.query(Personnel).first()
    return agent


def main():
    init_db()

    with get_session() as db:
        principal = _trouver_agent(db, MATRICULE_PRINCIPAL)
        if principal is None:
            print("Aucun agent en base. Importez d'abord")
            print("  exemples\\import_personnel_valide.xlsx")
            print("ou lancez l'application une fois pour generer les donnees.")
            return 2

        interim = _trouver_agent(db, MATRICULE_INTERIM)
        secondaire = _trouver_agent(db, MATRICULE_SECONDAIRE)

        id_principal = principal.id
        nom_principal = f"{principal.nom} {principal.prenoms}"
        mat_principal = principal.matricule

        id_secondaire = secondaire.id if secondaire else id_principal

        # Bloc intérimaire attendu par l'autorisation d'absence
        bloc_interim = {
            "matricule": interim.matricule if interim else "",
            "nom_complet": (
                f"{interim.nom} {interim.prenoms}" if interim else ""
            ),
            "emploi": (interim.emploi or "") if interim else "",
            "fonction": (interim.fonction or "") if interim else "",
            "structure": (
                interim.structure.nom
                if interim and interim.structure else ""
            ),
        }

    print(f"Agent principal : {nom_principal} ({mat_principal})")
    print(f"Interimaire     : {bloc_interim['nom_complet'] or '(aucun)'}")
    print(f"Dossier sortie  : {settings.OUTPUT_DIR}\n")

    generateur = DocumentGenerator()

    # ================================================================
    # Les 8 documents, avec des paramètres plausibles
    # ================================================================
    documents = [

        # 1 ─ Autorisation d'absence : 3 jours pour raison familiale,
        #     avec intérim assuré pendant l'absence.
        (
            "Autorisation d'absence",
            AutorisationAbsenceTemplate(),
            id_principal,
            {
                "date_debut": date(2026, 10, 12),
                "date_fin": date(2026, 10, 14),
                "destination": "Bouaké",
                "motif": "Obligations familiales impérieuses",
                "interim": bloc_interim,
                "date_reprise": date(2026, 10, 15),
                "heure_reprise": "07h30",
            },
        ),

        # 2 ─ Ordre de mission : tournée d'inspection pédagogique,
        #     hébergement assuré mais repas non fournis.
        (
            "Ordre de mission",
            OrdreMissionTemplate(),
            id_principal,
            {
                "date_depart": date(2026, 11, 3),
                "date_retour": date(2026, 11, 7),
                "destination": "Dabakala, Satama-Sokoura et Tortiya",
                "objet": (
                    "Tournée d'inspection pédagogique et de contrôle "
                    "administratif des établissements du département"
                ),
                "moyen_deplacement": "Véhicule de service — immatriculé 4521 CI 01",
                "hebergement_assure": True,
                "repas_fourni": False,
                "imputation": "Budget DRENAET Katiola — ligne 6241",
            },
        ),

        # 3 ─ Attestation de travail : destinée à une banque, cas le plus
        #     fréquent (dossier de prêt). Le modèle officiel n'accepte aucun
        #     paramètre : la formule de clôture est figée.
        (
            "Attestation de travail",
            AttestationTravailTemplate(),
            id_principal,
            {},
        ),

        # 4 ─ Attestation de présence au poste : contrôle de présence
        #     effective, souvent demandé par la Direction de la Solde.
        (
            "Attestation de présence",
            AttestationPresenceTemplate(),
            id_secondaire,
            {},
        ),

        # 5 ─ Titre de congés : congé annuel, départ hors de la région.
        (
            "Titre de congés",
            TitreCongesTemplate(),
            id_principal,
            {
                "date_debut": date(2026, 12, 21),
                "date_fin": date(2027, 1, 4),
                "destination": "Abidjan",
            },
        ),

        # 6 ─ Certificat de prise de service : suite à un arrêté
        #     d'affectation ministériel.
        (
            "Certificat de prise de service",
            CertificatPriseServiceTemplate(),
            id_secondaire,
            {
                "num_arrete": "0247/MENAET/DRH/SDGC",
                "date_arrete": date(2026, 8, 28),
                "lieu_prise_service": "IEPP Fronan",
                "qualite": "Chef de Circonscription",
                "date_prise_service": date(2026, 9, 14),
            },
        ),

        # 7 ─ Certificat de cessation de service : départ pour mutation
        #     vers une autre direction régionale.
        (
            "Certificat de cessation de service",
            CertificatCessationTemplate(),
            id_secondaire,
            {
                "structure_precedente": "IEPP Dabakala 1",
                "qualite": "Conseiller Pédagogique",
                "date_cessation": date(2026, 9, 11),
                "motif": (
                    "Mutation prononcée par arrêté n° 0247/MENAET/DRH/SDGC "
                    "du 28 août 2026"
                ),
            },
        ),

        # 8 ─ Fiche de mutation : candidature au poste de Chef de
        #     Circonscription, avec trois vœux d'affectation.
        (
            "Fiche de mutation",
            FicheMutationTemplate(),
            id_principal,
            {
                "date_entree_fp": date(2003, 10, 1),
                "date_entree_drenaet": date(2010, 9, 13),
                "date_fonction_actuelle": date(2019, 9, 16),
                "date_retraite": date(2038, 3, 14),
                "voeux": [
                    {"drenaet": "DRENAET de Katiola", "iepp": "IEPP Katiola"},
                    {"drenaet": "DRENAET de Bouaké 1", "iepp": "IEPP Bouaké Nord"},
                    {"drenaet": "DRENAET de Korhogo", "iepp": "IEPP Korhogo 2"},
                ],
            },
        ),
    ]

    # ================================================================
    reussis = []
    echecs = []

    DOSSIER_EXEMPLES.mkdir(parents=True, exist_ok=True)

    for numero_ordre, (libelle, template, personnel_id, parametres) in enumerate(
            documents, start=1):
        try:
            chemin, numero = generateur.generate(
                template=template,
                personnel_id=personnel_id,
                parameters=parametres,
                user_login="exemples",
            )
            pdf = Path(chemin)
            taille = pdf.stat().st_size if pdf.is_file() else 0

            if taille > 1000:
                # Copie sous un nom lisible dans exemples/documents/
                nom_lisible = (
                    f"{numero_ordre}_"
                    + libelle.lower()
                        .replace("'", "")
                        .replace("é", "e")
                        .replace("è", "e")
                        .replace(" ", "_")
                    + ".pdf"
                )
                shutil.copy2(pdf, DOSSIER_EXEMPLES / nom_lisible)

                reussis.append((libelle, numero, pdf, taille))
                print(f"  [OK  ] {libelle:<34} {numero:<32} {taille:>7} octets")
            else:
                echecs.append((libelle, "PDF vide ou trop petit"))
                print(f"  [ECHEC] {libelle:<34} PDF de {taille} octets")

        except Exception as e:
            echecs.append((libelle, str(e)))
            print(f"  [ECHEC] {libelle:<34} {type(e).__name__} : {e}")

    # ================================================================
    print(f"\n{len(reussis)}/{len(documents)} documents generes.")

    if reussis:
        print(f"\nCopies lisibles : {DOSSIER_EXEMPLES}")
        dossiers = sorted({p.parent for _, _, p, _ in reussis})
        print("\nEmplacements d'origine (historique de l'application) :")
        for dossier in dossiers:
            print(f"  {dossier}")

        # Contrôle du nombre de pages : ces documents officiels sont
        # conçus pour tenir sur UNE page.
        try:
            from pypdf import PdfReader
            debordements = []
            for libelle, _, pdf, _ in reussis:
                nb_pages = len(PdfReader(str(pdf)).pages)
                if nb_pages > 1:
                    debordements.append((libelle, nb_pages))
            if debordements:
                print("\nATTENTION : documents s'etalant sur plusieurs pages")
                for libelle, nb_pages in debordements:
                    print(f"  {libelle} : {nb_pages} pages")
        except ImportError:
            pass

    if echecs:
        print("\nEchecs :")
        for libelle, raison in echecs:
            print(f"  {libelle} : {raison}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
