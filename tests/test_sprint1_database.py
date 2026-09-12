"""
Test du Sprint 1 — Base de données + modèles SQLAlchemy.
Vérifie que tous les modèles fonctionnent et que les contraintes sont OK.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date
from src.models import (
    init_db, get_session, drop_db,
    Structure, Personnel, DocumentGenere, Absence, Utilisateur, CompteurDocument
)


def test_full_workflow():
    print("=" * 72)
    print("  TEST SPRINT 1 — Base de données & modèles SQLAlchemy")
    print("=" * 72)

    # 0. Reset
    print("\n[0] Reset de la base...")
    drop_db()
    init_db()
    print("    ✓ Base réinitialisée")

    # 1. Structure
    print("\n[1] Création d'une structure...")
    with get_session() as db:
        cafop = Structure(
            nom="CAFOP Katiola", type="CAFOP", localite="Katiola",
            telephone="27 23 59 70 29",
        )
        db.add(cafop)
        db.flush()
        cafop_id = cafop.id
        print(f"    ✓ {cafop} (id={cafop_id})")

    # 2. Personnel BABO
    print("\n[2] Création d'un agent (BABO Assomane David du PDF)...")
    with get_session() as db:
        babo = Personnel(
            matricule="233329C", nom="BABO", prenoms="Assomane David", sexe="M",
            emploi="Inspecteur Principal", fonction="Directeur du CAFOP Katiola",
            structure_id=cafop_id, telephone="07 07 07 07 07",
            residence="Katiola", statut="Actif",
        )
        db.add(babo)
        db.flush()
        babo_id = babo.id
        print(f"    ✓ {babo}")
        print(f"      Civilité  : {babo.civilite}")
        print(f"      Context Word : {babo.to_doc_context()}")

    # 3. Contrainte UNIQUE
    print("\n[3] Test contrainte UNIQUE matricule...")
    try:
        with get_session() as db:
            doublon = Personnel(matricule="233329C", nom="X", prenoms="X",
                                sexe="M", emploi="X", structure_id=cafop_id)
            db.add(doublon)
        print("    ✗ ÉCHEC : doublon accepté")
        return False
    except Exception as e:
        print(f"    ✓ Bien rejeté : {type(e).__name__}")

    # 4. 2e Personnel KAMENAN
    print("\n[4] Création KAMENAN N'Guessan Marius (intérimaire)...")
    with get_session() as db:
        kamenan = Personnel(
            matricule="249929N", nom="KAMENAN", prenoms="N'Guessan Marius", sexe="M",
            emploi="Professeur de CAFOP", fonction="Adjoint au Directeur de CAFOP",
            structure_id=cafop_id, statut="Actif",
        )
        db.add(kamenan)
        db.flush()
        kamenan_id = kamenan.id
        print(f"    ✓ {kamenan}")

    # 5. Relation Structure → Personnel
    print("\n[5] Test relation Structure→Personnel...")
    with get_session() as db:
        struct = db.query(Structure).filter_by(nom="CAFOP Katiola").first()
        nb = struct.agents.count()
        print(f"    ✓ {struct.nom} → {nb} agents")
        for a in struct.agents:
            print(f"        • {a.matricule}  {a.nom_complet}  ({a.fonction})")

    # 6. Compteur de documents
    print("\n[6] Test du compteur de documents...")
    with get_session() as db:
        cpt = CompteurDocument(
            type_document="autorisation_absence",
            annee_scolaire="2025-2026", dernier_numero=168,
        )
        db.add(cpt)
        db.flush()
        nouveau = cpt.incrementer()
        print(f"    ✓ Nouveau N° = {nouveau}")
        # Verif persistence
        cpt2 = db.query(CompteurDocument).filter_by(
            type_document="autorisation_absence",
            annee_scolaire="2025-2026").first()
        print(f"    ✓ Persisté : dernier_numero = {cpt2.dernier_numero}")

    # 7. Document généré
    print("\n[7] Test création d'un document...")
    with get_session() as db:
        doc = DocumentGenere(
            numero="169/MENAET/DRENAET-KLA/SRH",
            type_document="autorisation_absence",
            annee_scolaire="2025-2026",
            personnel_id=babo_id,
            interim_personnel_id=kamenan_id,
            parametres_json='{"date_debut":"2026-06-16","date_fin":"2026-06-18","destination":"Ambassade de France Abidjan","motif":"Courses administratives"}',
            chemin_docx="output/2025-2026/autorisations/169.docx",
            chemin_pdf="output/2025-2026/autorisations/169.pdf",
            genere_par="admin",
        )
        db.add(doc)
        db.flush()
        doc_id = doc.id
        print(f"    ✓ {doc}")
        print(f"      Bénéficiaire : {doc.personnel.nom_complet}")
        print(f"      Intérim      : {doc.interim.nom_complet}")

    # 8. Absence
    print("\n[8] Test création d'une absence...")
    with get_session() as db:
        absence = Absence(
            personnel_id=babo_id,
            date_debut=date(2026, 6, 16), date_fin=date(2026, 6, 18),
            motif="Mission administrative",
            description="Ambassade de France - Abidjan",
            justifiee=True, document_id=doc_id,
            annee_scolaire="2025-2026", mois="Juin",
        )
        absence.nb_jours = absence.calcul_jours()
        db.add(absence)
        db.flush()
        print(f"    ✓ {absence}")
        print(f"      Durée : {absence.nb_jours} jours")
        print(f"      Document lié : {absence.document.numero}")

    # 9. Utilisateur (bcrypt)
    print("\n[9] Test utilisateur avec bcrypt...")
    import bcrypt
    with get_session() as db:
        pwd = "admin123"
        h = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt(rounds=12)).decode()
        user = Utilisateur(
            login="admin", mot_de_passe_hash=h,
            nom_complet="Administrateur DRENAET",
            email="admin@drenaet-katiola.ci", role="admin",
        )
        db.add(user)
        db.flush()
        print(f"    ✓ {user}")
        print(f"      Hash : {user.mot_de_passe_hash[:30]}...")
        print(f"      Est admin : {user.est_admin}")
        # Vérif
        ok = bcrypt.checkpw(pwd.encode(), user.mot_de_passe_hash.encode())
        print(f"    ✓ Vérification password : {ok}")

    # 10. Validation rôle
    print("\n[10] Validation rôle invalide...")
    try:
        u = Utilisateur(login="x", mot_de_passe_hash="x", nom_complet="x", role="root")
        print("    ✗ ÉCHEC : 'root' accepté")
        return False
    except ValueError as e:
        print(f"    ✓ Bien rejeté : {e}")

    # 11. Stats
    print("\n[11] Statistiques finales...")
    with get_session() as db:
        stats = {
            "Structures": db.query(Structure).count(),
            "Personnel": db.query(Personnel).count(),
            "Documents générés": db.query(DocumentGenere).count(),
            "Absences": db.query(Absence).count(),
            "Utilisateurs": db.query(Utilisateur).count(),
            "Compteurs": db.query(CompteurDocument).count(),
        }
        for k, v in stats.items():
            print(f"    • {k:25s} : {v}")

    print("\n" + "=" * 72)
    print("  ✅ TOUS LES TESTS PASSENT — Sprint 1 fonctionnel !")
    print("=" * 72)
    return True


if __name__ == "__main__":
    success = test_full_workflow()
    sys.exit(0 if success else 1)
