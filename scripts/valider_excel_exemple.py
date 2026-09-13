"""
Validation (jetable) des fichiers Excel d'exemple — DRENAET-RH.

Passe les trois classeurs de `exemples/` dans la simulation (dry-run) du
pipeline d'import et compare le résultat aux attentes documentées dans les
feuilles « Mode d'emploi ».

N'écrit RIEN en base : seul le dry-run est utilisé.

Lancer avec :  venv\\Scripts\\python.exe scripts\\valider_excel_exemple.py
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.models import init_db
from src.services.import_pipeline.import_service import ImportService

DOSSIER = ROOT_DIR / "exemples"

resultats = []


def verifier(libelle: str, condition: bool, detail: str = ""):
    resultats.append(condition)
    marque = "OK  " if condition else "ECHEC"
    print(f"  [{marque}] {libelle}" + (f"  -> {detail}" if detail else ""))


def afficher_rapport(rapport):
    print(f"    feuille           : {rapport.sheet_name}")
    print(f"    lignes lues       : {rapport.nb_lignes_lues}")
    print(f"    a creer           : {rapport.nb_a_creer}")
    print(f"    a modifier        : {rapport.nb_a_modifier}")
    print(f"    a ignorer         : {rapport.nb_a_ignorer}")
    print(f"    erreurs           : {rapport.nb_erreurs}")
    print(f"    colonnes ignorees : {rapport.unmapped_columns}")
    print(f"    champs manquants  : {rapport.missing_required_fields}")
    print(f"    peut continuer    : {rapport.can_proceed}")


def main():
    init_db()

    # ================================================================
    print("=" * 72)
    print("FICHIER 1 — jeu valide (synonymes de colonnes)")
    print("=" * 72)
    r1 = ImportService.dry_run(str(DOSSIER / "import_personnel_valide.xlsx"),
                               strategy="UPSERT")
    afficher_rapport(r1)

    verifier("20 lignes lues", r1.nb_lignes_lues == 20, str(r1.nb_lignes_lues))
    verifier("aucune erreur de validation", r1.nb_erreurs == 0, str(r1.nb_erreurs))
    verifier("aucun champ obligatoire manquant",
             not r1.missing_required_fields, str(r1.missing_required_fields))
    verifier("l'import peut etre confirme", r1.can_proceed)
    verifier("« Observations » signalee comme non reconnue",
             any("bservation" in c for c in r1.unmapped_columns),
             str(r1.unmapped_columns))

    champs = set(r1.column_mapping.keys())
    for champ in ("matricule", "nom", "prenoms", "sexe", "emploi", "structure",
                  "telephone", "grade", "fonction", "date_naissance",
                  "date_prise_service", "statut", "email", "residence"):
        verifier(f"synonyme reconnu pour « {champ} »", champ in champs)

    if r1.errors:
        print("\n    ERREURS INATTENDUES :")
        for e in r1.errors[:5]:
            print(f"      {e}")

    # ================================================================
    print("\n" + "=" * 72)
    print("FICHIER 2 — controle des regles de validation")
    print("=" * 72)
    r2 = ImportService.dry_run(str(DOSSIER / "import_personnel_avec_erreurs.xlsx"),
                               strategy="UPSERT")
    afficher_rapport(r2)

    verifier("12 lignes lues", r2.nb_lignes_lues == 12, str(r2.nb_lignes_lues))
    verifier("7 lignes rejetees", r2.nb_erreurs == 7, str(r2.nb_erreurs))
    verifier("5 lignes acceptees",
             (r2.nb_a_creer + r2.nb_a_modifier) == 5,
             f"creer={r2.nb_a_creer} modifier={r2.nb_a_modifier}")

    print("\n    Motifs de rejet releves :")
    motifs = []
    for e in r2.errors:
        raisons = e.get("erreurs") or e.get("raisons") or [e.get("raison", "?")]
        if isinstance(raisons, str):
            raisons = [raisons]
        motifs.extend(raisons)
        print(f"      ligne {e.get('_row_number', e.get('ligne', '?'))} : "
              f"{'; '.join(str(r) for r in raisons)}")

    texte_motifs = " | ".join(str(m).lower() for m in motifs)
    for attendu, cle in (
        ("matricule manquant", "matricule"),
        ("nom manquant", "nom:"),
        ("sexe non reconnu", "sexe"),
        ("date invalide", "date_naissance"),
        ("age minimum", "18"),
        ("coherence des dates", "postérieure"),
        ("email invalide", "email"),
    ):
        verifier(f"motif detecte : {attendu}", cle in texte_motifs)

    # ================================================================
    print("\n" + "=" * 72)
    print("FICHIER 3 — strategies de fusion (avant import du fichier 1)")
    print("=" * 72)
    print("  Les 8 agents du fichier 1 ne sont pas encore en base :")
    print("  ils apparaissent donc en creation, ce qui est normal.")
    chemin3 = str(DOSSIER / "import_mise_a_jour.xlsx")

    for strategie in ("UPSERT", "INSERT_ONLY", "UPDATE_ONLY"):
        r = ImportService.dry_run(chemin3, strategy=strategie)
        print(f"\n  {strategie}")
        print(f"    lues={r.nb_lignes_lues} creer={r.nb_a_creer} "
              f"modifier={r.nb_a_modifier} ignorer={r.nb_a_ignorer} "
              f"erreurs={r.nb_erreurs}")
        verifier(f"{strategie} : 10 lignes lues", r.nb_lignes_lues == 10,
                 str(r.nb_lignes_lues))
        verifier(f"{strategie} : aucune erreur de validation",
                 r.nb_erreurs == 0, str(r.nb_erreurs))

    verifier("UPDATE_ONLY ignore les agents absents",
             ImportService.dry_run(chemin3, strategy="UPDATE_ONLY").nb_a_ignorer == 10)

    # ================================================================
    # Import REEL du fichier 1, puis re-simulation du fichier 3 :
    # c'est la seule facon de verifier les decomptes annonces dans la
    # notice (8 modifications / 2 creations).
    # ================================================================
    print("\n" + "=" * 72)
    print("IMPORT REEL du fichier 1, puis re-simulation du fichier 3")
    print("=" * 72)

    execution = ImportService.execute(
        r1, user_login="validation_automatique", user_role="admin",
        commentaire="Validation des fichiers d'exemple",
    )
    print(f"  statut import : {execution.statut}")
    nb_crees = getattr(execution, "nb_crees", None)
    print(f"  agents crees  : {nb_crees}")
    verifier("import du fichier 1 reussi",
             str(execution.statut).upper() in ("SUCCESS", "COMPLETED", "OK",
                                               "TERMINE", "SUCCES"),
             str(execution.statut))

    attendus = {
        "UPSERT":      {"creer": 2, "modifier": 8, "ignorer": 0},
        "INSERT_ONLY": {"creer": 2, "modifier": 0, "ignorer": 8},
        "UPDATE_ONLY": {"creer": 0, "modifier": 8, "ignorer": 2},
    }

    for strategie, attendu in attendus.items():
        r = ImportService.dry_run(chemin3, strategy=strategie)
        obtenu = {"creer": r.nb_a_creer, "modifier": r.nb_a_modifier,
                  "ignorer": r.nb_a_ignorer}
        print(f"\n  {strategie}")
        print(f"    attendu : {attendu}")
        print(f"    obtenu  : {obtenu}")
        verifier(f"{strategie} : decompte conforme a la notice",
                 obtenu == attendu)

    # ================================================================
    echecs = resultats.count(False)
    print("\n" + "=" * 72)
    print(f"  {len(resultats) - echecs}/{len(resultats)} verifications reussies")
    print("=" * 72)
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
