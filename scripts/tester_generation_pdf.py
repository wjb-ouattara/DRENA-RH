"""
Test (jetable) de génération d'un PDF officiel — DRENAET-RH.

Vérifie qu'aucun chemin de ressource n'a été cassé par la séparation
lecture/écriture : l'armoirie est lue dans RESOURCES_DIR (bundle) et le PDF
est écrit dans OUTPUT_DIR (données utilisateur).

Lancer avec :  venv\\Scripts\\python.exe scripts\\tester_generation_pdf.py
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import settings
from src.models import init_db, get_session, Personnel


def main():
    init_db()

    print(f"RESOURCES_DIR (lecture) : {settings.RESOURCES_DIR}")
    print(f"OUTPUT_DIR    (ecriture): {settings.OUTPUT_DIR}")

    armoirie = settings.RESOURCES_DIR / "images" / "armoirie_ci.png"
    print(f"Armoirie presente       : {armoirie.exists()}")
    if not armoirie.exists():
        print("ECHEC : armoirie introuvable, l'en-tete officiel serait degrade.")
        return 1

    with get_session() as db:
        agent = db.query(Personnel).first()
        if agent is None:
            print("Aucun agent en base : seed necessaire pour ce test.")
            print("Lancer d'abord l'application une fois, puis relancer ce script.")
            return 2
        agent_id = agent.id
        matricule = agent.matricule

    from src.services.document_generator import DocumentGenerator
    from src.services.document_templates.attestation_travail import (
        AttestationTravailTemplate,
    )

    generateur = DocumentGenerator()
    chemin, numero = generateur.generate(
        template=AttestationTravailTemplate(),
        personnel_id=agent_id,
        parameters={},
        user_login="test_automatique",
    )

    pdf = Path(chemin)
    ok = pdf.is_file() and pdf.stat().st_size > 1000
    print(f"\nPDF genere   : {pdf}")
    print(f"Taille       : {pdf.stat().st_size if pdf.is_file() else 0} octets")
    print(f"Numero       : {numero}")
    print(f"Agent        : {matricule}")
    print(f"\n[{'OK' if ok else 'ECHEC'}] Generation PDF")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
