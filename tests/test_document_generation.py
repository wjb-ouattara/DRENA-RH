"""Test de génération de l'Autorisation d'Absence en PDF."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date
from src.models import init_db, get_session, Personnel, Structure
from src.services.document_generator import DocumentGenerator
from src.services.document_templates.autorisation_absence import AutorisationAbsenceTemplate


def test_generation():
    print("=" * 70)
    print("  TEST GÉNÉRATION — Demande d'Autorisation d'Absence")
    print("=" * 70)

    # 1. S'assurer que la BD est en place
    init_db()

    # 2. Vérifier si BABO et KAMENAN existent (les créer sinon)
    with get_session() as db:
        babo = db.query(Personnel).filter_by(matricule="233329C").first()
        kamenan = db.query(Personnel).filter_by(matricule="249929N").first()

        # Si BABO n'existe pas, on le crée (ainsi que la structure CAFOP)
        if not babo:
            print("\n[Setup] BABO non trouvé → création des données de test...")

            # Trouver ou créer la structure CAFOP Katiola
            cafop = db.query(Structure).filter_by(nom="CAFOP Katiola").first()
            if not cafop:
                cafop = Structure(
                    nom="CAFOP Katiola",
                    type="CAFOP",
                    localite="Katiola"
                )
                db.add(cafop)
                db.flush()
                print(f"    ✓ Structure créée : {cafop.nom}")

            # Créer BABO
            babo = Personnel(
                matricule="233329C",
                nom="BABO",
                prenoms="Assomane David",
                sexe="M",
                date_naissance=date(1975, 3, 15),
                lieu_naissance="Katiola",
                situation_matrimoniale="Marié(e)",
                emploi="Inspecteur Principal",
                grade="A4",
                fonction="Directeur du CAFOP Katiola",
                structure_id=cafop.id,
                telephone="07 07 07 07 07",
                email="babo.assomane@drenaet-kla.ci",
                residence="Katiola",
                statut="Actif",
                date_prise_service=date(2018, 9, 1),
            )
            db.add(babo)
            db.flush()
            print(f"    ✓ Agent BABO créé (id={babo.id})")

        # Si KAMENAN n'existe pas, on le crée
        if not kamenan:
            print("[Setup] KAMENAN non trouvé → création...")

            cafop = db.query(Structure).filter_by(nom="CAFOP Katiola").first()
            if not cafop:
                cafop = db.query(Structure).first()

            kamenan = Personnel(
                matricule="249929N",
                nom="KAMENAN",
                prenoms="N'Guessan Marius",
                sexe="M",
                emploi="PROFESSEUR DE CAFOP",
                grade="A5",
                fonction="Adjoint au Directeur de CAFOP",
                structure_id=cafop.id,
                statut="Actif",
            )
            db.add(kamenan)
            db.flush()
            print(f"    ✓ Agent KAMENAN créé (id={kamenan.id})")

        # Récupérer les valeurs nécessaires dans cette session
        babo_id = babo.id
        kamenan_id = kamenan.id
        kamenan_dict = {
            "matricule": kamenan.matricule,
            "nom_complet": kamenan.nom_complet,
            "emploi": kamenan.emploi,
            "fonction": kamenan.fonction or "",
            "structure": kamenan.structure.nom if kamenan.structure else "",
        }

    print(f"\n[Test] BABO id={babo_id}, KAMENAN id={kamenan_id}")

    # 3. Préparer les paramètres de l'autorisation
    parameters = {
        "date_debut": date(2026, 6, 16),
        "date_fin": date(2026, 6, 18),
        "date_reprise": date(2026, 6, 19),
        "heure_reprise": "07h30",
        "destination": "L'Ambassade de France - Abidjan",
        "motif": "Courses administratives",
        "interim_personnel_id": kamenan_id,
        "interim": kamenan_dict,
    }

    # 4. Générer le PDF
    print("\n[Génération] Création du PDF...")
    generator = DocumentGenerator()
    template = AutorisationAbsenceTemplate()

    pdf_path, numero = generator.generate(
        template=template,
        personnel_id=babo_id,
        parameters=parameters,
        user_login="admin",
    )

    print(f"\n    ✓ PDF généré : {pdf_path}")
    print(f"    ✓ Numéro     : {numero}")

    pdf_file = Path(pdf_path)
    if pdf_file.exists():
        size_kb = pdf_file.stat().st_size / 1024
        print(f"    ✓ Taille     : {size_kb:.1f} Ko")

    print("\n" + "=" * 70)
    print("  ✅ Document généré avec succès !")
    print("=" * 70)
    return pdf_path


if __name__ == "__main__":
    test_generation()