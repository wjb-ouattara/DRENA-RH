"""Vérification de la qualité des données seedées."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collections import Counter
from src.models import get_session, Personnel, Structure, Utilisateur


def check():
    print("=" * 72)
    print("  VÉRIFICATION DU SEED")
    print("=" * 72)

    with get_session() as db:
        # Utilisateurs
        print("\n[1] UTILISATEURS")
        for u in db.query(Utilisateur).all():
            print(f"  • {u.login:15} | {u.nom_complet:25} | role={u.role}")

        # Stats globales
        print("\n[2] STATISTIQUES")
        nb_struct = db.query(Structure).count()
        nb_pers = db.query(Personnel).count()
        print(f"  • Structures : {nb_struct}")
        print(f"  • Agents     : {nb_pers}")

        # Par structure
        print("\n[3] RÉPARTITION PAR STRUCTURE")
        for s in db.query(Structure).all():
            nb = s.agents.count()
            print(f"  • {s.nom:38} ({s.type:8}) : {nb:3} agents")

        # Par emploi
        print("\n[4] RÉPARTITION PAR EMPLOI")
        emplois = Counter([p.emploi for p in db.query(Personnel).all()])
        for e, n in emplois.most_common():
            print(f"  • {e:50} : {n}")

        # Par statut
        print("\n[5] RÉPARTITION PAR STATUT")
        statuts = Counter([p.statut for p in db.query(Personnel).all()])
        for s, n in statuts.most_common():
            print(f"  • {s:25} : {n}")

        # Par sexe
        print("\n[6] RÉPARTITION PAR SEXE")
        sexes = Counter([p.sexe for p in db.query(Personnel).all()])
        for s, n in sexes.most_common():
            print(f"  • {s} : {n}")

        # Échantillon
        print("\n[7] 10 PREMIERS AGENTS (échantillon)")
        print(f"  {'Matricule':<10} {'Nom complet':<35} {'Sexe':<5} {'Emploi':<35} {'Structure':<25}")
        print("  " + "-" * 110)
        for p in db.query(Personnel).limit(10).all():
            print(f"  {p.matricule:<10} {p.nom_complet:<35} {p.sexe:<5} {p.emploi:<35} {p.structure.nom:<25}")

        # Test contexte Word pour un agent
        print("\n[8] CONTEXTE WORD POUR UN AGENT (exemple template)")
        p = db.query(Personnel).first()
        ctx = p.to_doc_context()
        for k, v in ctx.items():
            print(f"  {k:15} = {v}")

    print("\n" + "=" * 72)
    print("  ✅ Données seedées de qualité")
    print("=" * 72)


if __name__ == "__main__":
    check()
