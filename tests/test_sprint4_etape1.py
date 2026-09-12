"""
========================================================================
DRENAET-RH — Tests des services Sprint 4 Étape 1
========================================================================
Tests unitaires pour :
- PersonnelService (CRUD + recherche + statistiques)
- StructureService (CRUD structures)
- AuditService (audit trail)

Usage :
    python tests/test_sprint4_etape1.py

Note : ce test utilise une BD temporaire (SQLite en mémoire ou fichier .db.test)
pour ne pas polluer la vraie BD.
"""

import sys
import os
from pathlib import Path
from datetime import date

# Ajouter le dossier racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models import init_db, get_session, Personnel, Structure
from src.services.personnel_service import (
    PersonnelService,
    MatriculeExistantError,
    ChampObligatoireError,
    AgentIntrouvableError,
    StructureInvalideError,
)
from src.services.structure_service import (
    StructureService,
    NomStructureExistantError,
    StructureAvecAgentsError,
)
from src.services.audit_service import AuditService


# ========================================================================
# HELPERS
# ========================================================================
def print_test(name):
    print(f"\n─── TEST: {name} ─────────────────────────────────────")


def assert_eq(actual, expected, label=""):
    if actual != expected:
        print(f"  ❌ ÉCHEC {label}")
        print(f"     attendu : {expected}")
        print(f"     obtenu  : {actual}")
        return False
    print(f"  ✓ {label}")
    return True


def assert_raises(func, exception_cls, label=""):
    try:
        func()
        print(f"  ❌ ÉCHEC {label} : aucune exception levée")
        return False
    except exception_cls as e:
        print(f"  ✓ {label} → {type(e).__name__}: {e}")
        return True
    except Exception as e:
        print(f"  ❌ ÉCHEC {label} : mauvaise exception ({type(e).__name__}: {e})")
        return False


# ========================================================================
# TESTS STRUCTURE SERVICE
# ========================================================================
def test_structure_service():
    print_test("StructureService - CRUD basique")

    # CREATE
    cafop = StructureService.create({
        "nom": "CAFOP Katiola TEST",
        "type": "CAFOP",
        "localite": "Katiola",
    })
    assert_eq(cafop["nom"], "CAFOP Katiola TEST", "création CAFOP")
    assert cafop["id"] is not None, "ID assigné"

    # GET_OR_CREATE (existant)
    same = StructureService.get_or_create("CAFOP Katiola TEST")
    assert_eq(same["id"], cafop["id"], "get_or_create existant")

    # GET_OR_CREATE (nouveau)
    iepp = StructureService.get_or_create("IEPP Test", type="IEPP")
    assert iepp["id"] != cafop["id"], "get_or_create nouveau"
    print(f"  ✓ get_or_create crée nouvelle structure ID={iepp['id']}")

    # Duplicate name
    assert_raises(
        lambda: StructureService.create({"nom": "CAFOP Katiola TEST", "type": "CAFOP"}),
        NomStructureExistantError,
        "création doublon rejetée",
    )

    return cafop, iepp


# ========================================================================
# TESTS PERSONNEL SERVICE
# ========================================================================
def test_personnel_service_create(structure):
    print_test("PersonnelService - CREATE")

    # Création OK
    agent = PersonnelService.create(
        {
            "matricule": "TST001A",
            "nom": "TESTAGENT",
            "prenoms": "Jean-Paul",
            "sexe": "M",
            "emploi": "Inspecteur",
            "grade": "A4",
            "structure_id": structure["id"],
            "telephone": "07 07 07 07 07",
            "date_prise_service": date(2020, 9, 1),
        },
        user_login="testuser",
        user_role="admin",
    )
    assert_eq(agent["matricule"], "TST001A", "création agent")
    assert_eq(agent["structure_id"], structure["id"], "structure liée")
    print(f"  ✓ Agent créé avec ID={agent['id']}")

    # Duplicate matricule
    assert_raises(
        lambda: PersonnelService.create(
            {
                "matricule": "TST001A",
                "nom": "AUTRE",
                "prenoms": "Autre",
                "sexe": "F",
                "emploi": "Prof",
                "structure_id": structure["id"],
            },
            user_login="testuser",
        ),
        MatriculeExistantError,
        "matricule doublon rejeté",
    )

    # Champ obligatoire manquant
    assert_raises(
        lambda: PersonnelService.create(
            {
                "matricule": "TST002B",
                "nom": "NOMSANSEMPLOI",
                "prenoms": "Test",
                "sexe": "M",
                "structure_id": structure["id"],
                # emploi manquant !
            },
            user_login="testuser",
        ),
        ChampObligatoireError,
        "emploi manquant rejeté",
    )

    # Sexe invalide
    assert_raises(
        lambda: PersonnelService.create(
            {
                "matricule": "TST003C",
                "nom": "TEST",
                "prenoms": "Test",
                "sexe": "X",
                "emploi": "Prof",
                "structure_id": structure["id"],
            },
            user_login="testuser",
        ),
        ChampObligatoireError,
        "sexe invalide rejeté",
    )

    # Structure invalide
    assert_raises(
        lambda: PersonnelService.create(
            {
                "matricule": "TST004D",
                "nom": "TEST",
                "prenoms": "Test",
                "sexe": "M",
                "emploi": "Prof",
                "structure_id": 99999,
            },
            user_login="testuser",
        ),
        StructureInvalideError,
        "structure inexistante rejetée",
    )

    return agent


def test_personnel_service_read(agent):
    print_test("PersonnelService - READ")

    # GET_BY_ID
    got = PersonnelService.get_by_id(agent["id"])
    assert_eq(got["matricule"], agent["matricule"], "get_by_id")

    # GET_BY_MATRICULE
    got2 = PersonnelService.get_by_matricule(agent["matricule"])
    assert_eq(got2["id"], agent["id"], "get_by_matricule")

    # EXISTS_MATRICULE
    assert_eq(PersonnelService.exists_matricule(agent["matricule"]), True, "exists=True")
    assert_eq(PersonnelService.exists_matricule("INEXISTANT"), False, "exists=False")

    # SEARCH par nom
    results, total = PersonnelService.search(query="TESTAGENT")
    assert total >= 1, f"search par nom trouve au moins 1 résultat (obtenu: {total})"
    print(f"  ✓ search 'TESTAGENT' → {total} résultat(s)")


def test_personnel_service_update(agent):
    print_test("PersonnelService - UPDATE")

    # Modifier téléphone et fonction
    updated = PersonnelService.update(
        agent["id"],
        {
            "telephone": "08 08 08 08 08",  # nouveau
            "fonction": "Directeur",         # nouveau
        },
        user_login="testuser",
        commentaire="Test modification téléphone + fonction",
    )
    assert_eq(updated["telephone"], "08 08 08 08 08", "téléphone modifié")
    assert_eq(updated["fonction"], "Directeur", "fonction ajoutée")

    # Vérifier audit trail
    history = AuditService.get_history_for_agent(agent["matricule"])
    assert len(history) >= 2, f"historique contient au moins 2 entrées (obtenu: {len(history)})"

    latest = history[0]  # tri desc
    assert_eq(latest["action"], "UPDATE", "dernière action = UPDATE")
    assert "changements" in latest["changements"], "changements présents dans audit"

    changements = latest["changements"]["changements"]
    print(f"  ✓ Champs modifiés : {list(changements.keys())}")

    # Update inexistant
    assert_raises(
        lambda: PersonnelService.update(99999, {"telephone": "..."}),
        AgentIntrouvableError,
        "update agent inexistant rejeté",
    )


def test_personnel_service_delete(agent):
    print_test("PersonnelService - DELETE (hard-delete)")

    matricule = agent["matricule"]

    # Snapshot avant suppression
    snapshot = PersonnelService.delete(
        agent["id"],
        user_login="testuser",
        commentaire="Test suppression",
    )
    assert_eq(snapshot["matricule"], matricule, "snapshot renvoyé")

    # Vérifier qu'il n'existe plus
    got = PersonnelService.get_by_id(agent["id"])
    assert_eq(got, None, "agent inaccessible après delete")

    # Mais l'historique existe toujours !
    history = AuditService.get_history_for_agent(matricule)
    assert len(history) >= 1, "historique persiste après hard-delete"

    latest = history[0]
    assert_eq(latest["action"], "DELETE", "dernière action = DELETE")
    assert "snapshot" in latest["changements"], "snapshot présent dans audit"
    print(f"  ✓ Historique conserve {len(history)} entrée(s) après suppression")


# ========================================================================
# TESTS AUDIT SERVICE
# ========================================================================
def test_audit_service():
    print_test("AuditService - Recherche et statistiques")

    # Compteurs
    counts = AuditService.count_by_action()
    print(f"  ✓ Actions loggées : {counts}")
    assert "CREATE" in counts, "CREATE compté"
    assert "UPDATE" in counts, "UPDATE compté"
    assert "DELETE" in counts, "DELETE compté"

    # Activité récente
    recent = AuditService.get_recent_activity(limit=10)
    assert len(recent) >= 3, f"au moins 3 actions récentes (obtenu: {len(recent)})"
    print(f"  ✓ Activité récente : {len(recent)} entrée(s)")

    # Filtrer par action
    creates_only = AuditService.get_recent_activity(action="CREATE")
    assert all(e["action"] == "CREATE" for e in creates_only), "filtre CREATE ok"

    # Filtrer par utilisateur
    testuser_actions = AuditService.get_recent_activity(user_login="testuser")
    assert all(e["utilisateur_login"] == "testuser" for e in testuser_actions), "filtre user ok"


# ========================================================================
# TEST STATISTIQUES
# ========================================================================
def test_statistics(structure):
    print_test("PersonnelService - Statistiques")

    # Créer 3 agents pour avoir des stats
    for i, sexe in enumerate(["M", "F", "M"]):
        PersonnelService.create(
            {
                "matricule": f"STA00{i}A",
                "nom": f"STAT{i}",
                "prenoms": "Test",
                "sexe": sexe,
                "emploi": "Prof",
                "structure_id": structure["id"],
            },
            user_login="testuser",
        )

    stats = PersonnelService.get_statistics()
    print(f"  ✓ Total agents : {stats['total_agents']}")
    print(f"  ✓ Hommes : {stats['hommes']} ({stats['ratio_hommes_pct']}%)")
    print(f"  ✓ Femmes : {stats['femmes']} ({stats['ratio_femmes_pct']}%)")
    print(f"  ✓ Top structures : {stats['top_structures']}")

    assert stats['total_agents'] >= 3, "au moins 3 agents comptés"


# ========================================================================
# MAIN
# ========================================================================
def main():
    print("=" * 72)
    print("  TESTS SPRINT 4 - ÉTAPE 1 : FONDATIONS")
    print("=" * 72)

    # Initialiser la BD (crée les tables si absentes)
    print("\n[Setup] Initialisation de la BD...")
    init_db()
    print("  ✓ Schéma BD prêt")

    # Lancer les tests
    try:
        cafop, iepp = test_structure_service()
        agent = test_personnel_service_create(cafop)
        test_personnel_service_read(agent)
        test_personnel_service_update(agent)
        test_audit_service()  # avant delete pour compter CREATE + UPDATE
        test_statistics(cafop)
        test_personnel_service_delete(agent)  # delete en dernier

        print("\n" + "=" * 72)
        print("  ✅ TOUS LES TESTS PASSENT")
        print("=" * 72)
        return 0

    except AssertionError as e:
        print(f"\n❌ Test échoué : {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Erreur inattendue : {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())