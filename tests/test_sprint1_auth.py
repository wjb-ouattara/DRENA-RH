"""Test du service d'authentification."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.services.auth_service import AuthService, UserSession, hash_password, verify_password


def test_auth():
    print("=" * 72)
    print("  TEST AUTHENTIFICATION — Sprint 1")
    print("=" * 72)

    # 1. hash / verify
    print("\n[1] Test hash / verify password...")
    pwd = "MonMotDePasse123"
    h = hash_password(pwd)
    print(f"    Password : {pwd}")
    print(f"    Hash     : {h[:30]}...")
    assert verify_password(pwd, h), "verify_password devrait retourner True"
    assert not verify_password("MauvaisMdp", h), "verify_password devrait retourner False"
    print("    ✓ hash/verify fonctionnent")

    # 2. Login valide (admin)
    print("\n[2] Test login valide (admin/admin2026)...")
    success, msg, user = AuthService.authenticate("admin", "admin2026")
    print(f"    success={success}, msg='{msg}', user={user}")
    assert success, f"Login admin devrait réussir : {msg}"
    assert user.role == "admin"
    print("    ✓ Login admin OK")

    # 3. Session active
    print("\n[3] Test session utilisateur...")
    session = UserSession.get_instance()
    print(f"    Authentifié : {session.is_authenticated}")
    print(f"    Login       : {session.login}")
    print(f"    Nom         : {session.nom_complet}")
    print(f"    Rôle        : {session.role}")
    print(f"    Est admin   : {session.is_admin}")
    assert session.is_authenticated
    assert session.is_admin
    print("    ✓ Session OK")

    # 4. Logout
    print("\n[4] Test logout...")
    AuthService.logout()
    assert not session.is_authenticated, "Session devrait être fermée"
    print("    ✓ Logout OK")

    # 5. Login avec mauvais mot de passe (1ère tentative)
    print("\n[5] Test login avec mauvais mot de passe...")
    success, msg, user = AuthService.authenticate("admin", "MauvaisMotDePasse")
    print(f"    success={success}, msg='{msg}'")
    assert not success
    print("    ✓ Rejet correctement")

    # 6. Login avec login inexistant
    print("\n[6] Test login inexistant...")
    success, msg, user = AuthService.authenticate("inconnu", "x")
    print(f"    success={success}, msg='{msg}'")
    assert not success
    print("    ✓ Rejet correctement")

    # 7. Login opérateur
    print("\n[7] Test login operateur1/passer123...")
    success, msg, user = AuthService.authenticate("operateur1", "passer123")
    print(f"    success={success}, role={user.role if user else None}")
    assert success
    assert user.role == "operateur"
    assert not session.is_admin
    print("    ✓ Login operateur OK")

    # 8. Changement de mot de passe
    print("\n[8] Test changement de mot de passe...")
    user_id = session.user_id
    success, msg = AuthService.change_password(user_id, "passer123", "NouveauMdp456")
    print(f"    success={success}, msg='{msg}'")
    assert success
    print("    ✓ Mot de passe changé")

    # Vérifier que l'ancien ne marche plus
    AuthService.logout()
    success, msg, user = AuthService.authenticate("operateur1", "passer123")
    assert not success
    print("    ✓ L'ancien mot de passe ne fonctionne plus")

    # Et le nouveau si
    success, msg, user = AuthService.authenticate("operateur1", "NouveauMdp456")
    assert success
    print("    ✓ Le nouveau mot de passe fonctionne")

    # Remettre le mdp d'origine pour ne pas casser les autres tests
    AuthService.change_password(user.id, "NouveauMdp456", "passer123")
    AuthService.logout()

    print("\n" + "=" * 72)
    print("  ✅ TESTS AUTHENTIFICATION OK")
    print("=" * 72)


if __name__ == "__main__":
    test_auth()
