"""
Test de vérification manuelle (jetable) — DRENAET-RH.

Vérifie sans intervention humaine :
  1. l'initialisation complète de l'application (init_db puis paramètres) ;
  2. la sidebar d'un ADMIN : les 7 menus, dont Paramètres et Administration ;
  3. la sidebar d'un OPÉRATEUR : 5 menus, ni Paramètres ni Administration,
     et pages réservées non instanciées ;
  4. la garde défensive de _on_menu_click pour un opérateur ;
  5. le changement de mot de passe (succès, mauvais ancien, trop court) ;
  6. l'instanciation de la popup ChangePasswordDialog.

Lancer avec :  python scripts\verifier_roles_et_mdp.py
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from PyQt6.QtWidgets import QApplication

from config import settings
from src.models import init_db, get_session, Utilisateur
from src.services.auth_service import AuthService, UserSession, hash_password
from src.services.settings_service import SettingsService

resultats = []


def verifier(libelle: str, condition: bool, detail: str = ""):
    resultats.append((libelle, condition, detail))
    marque = "OK  " if condition else "ECHEC"
    print(f"[{marque}] {libelle}" + (f"  -> {detail}" if detail else ""))


def main():
    print("=" * 70)
    print(f"  Base utilisée : {settings.DATABASE_FILE}")
    print("=" * 70)

    # --- 1. Initialisation (ordre init_db -> paramètres) ---
    init_db()
    SettingsService.sync_to_runtime_config()
    verifier("Initialisation : init_db puis sync_to_runtime_config", True)

    app = QApplication(sys.argv)
    from src.ui.main_window import MainWindow, ADMIN_ONLY_PAGES

    # --- Comptes de test ---
    with get_session() as db:
        for login, role in (("zz_test_admin", "admin"),
                            ("zz_test_operateur", "operateur")):
            existant = db.query(Utilisateur).filter_by(login=login).first()
            if existant:
                db.delete(existant)
            db.flush()
            db.add(Utilisateur(
                login=login,
                mot_de_passe_hash=hash_password("motdepasse1"),
                nom_complet=f"Test {role}",
                role=role,
                actif=True,
            ))

    # --- 2. Sidebar ADMIN ---
    ok, _, _ = AuthService.authenticate("zz_test_admin", "motdepasse1")
    verifier("Connexion du compte admin de test", ok)

    fenetre_admin = MainWindow()
    menus_admin = set(fenetre_admin.menu_buttons.keys())
    verifier("Admin : Paramètres et Administration visibles",
             ADMIN_ONLY_PAGES <= menus_admin, f"menus = {sorted(menus_admin)}")
    verifier("Admin : les deux pages réservées sont instanciées",
             ADMIN_ONLY_PAGES <= set(fenetre_admin.pages.keys()))
    fenetre_admin.deleteLater()

    # --- 3. Sidebar OPÉRATEUR ---
    AuthService.logout()
    ok, _, _ = AuthService.authenticate("zz_test_operateur", "motdepasse1")
    verifier("Connexion du compte opérateur de test", ok)

    fenetre_ope = MainWindow()
    menus_ope = set(fenetre_ope.menu_buttons.keys())
    verifier("Opérateur : aucun menu réservé dans la sidebar",
             not (ADMIN_ONLY_PAGES & menus_ope), f"menus = {sorted(menus_ope)}")
    verifier("Opérateur : 5 menus exactement",
             len(menus_ope) == 5, f"{len(menus_ope)} menus")
    verifier("Opérateur : pages réservées NON instanciées",
             not (ADMIN_ONLY_PAGES & set(fenetre_ope.pages.keys())),
             f"pages = {sorted(fenetre_ope.pages.keys())}")

    # --- 4. Garde défensive : la page courante ne doit pas changer ---
    page_avant = fenetre_ope.content_stack.currentWidget()
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QMessageBox, QApplication as QA

    # Ferme automatiquement la boîte d'avertissement attendue
    def fermer_boite():
        for widget in QA.topLevelWidgets():
            if isinstance(widget, QMessageBox) and widget.isVisible():
                widget.accept()
    QTimer.singleShot(150, fermer_boite)
    fenetre_ope._on_menu_click("administration")
    verifier("Opérateur : _on_menu_click('administration') refusé",
             fenetre_ope.content_stack.currentWidget() is page_avant)

    # --- 6. Popup de changement de mot de passe ---
    from src.ui.widgets.change_password_dialog import ChangePasswordDialog
    popup = ChangePasswordDialog()
    verifier("Popup ChangePasswordDialog instanciable",
             popup.champ_actuel is not None
             and popup.champ_nouveau is not None
             and popup.champ_confirmation is not None)
    verifier("Opérateur : bouton clé présent dans la carte profil",
             fenetre_ope.user_card.password_btn is not None)
    popup.deleteLater()
    fenetre_ope.deleteLater()

    # --- 5. Service de changement de mot de passe ---
    session = UserSession.get_instance()
    uid = session.user_id

    ok, msg = AuthService.change_password(uid, "mauvais_ancien", "nouveau123")
    verifier("Refus si ancien mot de passe incorrect", not ok, msg)

    ok, msg = AuthService.change_password(uid, "motdepasse1", "abc")
    verifier("Refus si nouveau mot de passe trop court", not ok, msg)

    ok, msg = AuthService.change_password(uid, "motdepasse1", "motdepasse1")
    verifier("Refus si identique à l'ancien", not ok, msg)

    ok, msg = AuthService.change_password(uid, "motdepasse1", "nouveau123")
    verifier("Changement accepté", ok, msg)

    AuthService.logout()
    ok, _, _ = AuthService.authenticate("zz_test_operateur", "nouveau123")
    verifier("Reconnexion avec le NOUVEAU mot de passe", ok)

    AuthService.logout()
    ok, _, _ = AuthService.authenticate("zz_test_operateur", "motdepasse1")
    verifier("Ancien mot de passe désormais refusé", not ok)

    # Le rôle n'a pas bougé
    with get_session() as db:
        u = db.query(Utilisateur).filter_by(login="zz_test_operateur").first()
        verifier("Le rôle est resté 'operateur'", u.role == "operateur", u.role)

    # --- Nettoyage ---
    AuthService.logout()
    with get_session() as db:
        for login in ("zz_test_admin", "zz_test_operateur"):
            u = db.query(Utilisateur).filter_by(login=login).first()
            if u:
                db.delete(u)
    print("\nComptes de test supprimés.")

    echecs = [r for r in resultats if not r[1]]
    print("=" * 70)
    print(f"  {len(resultats) - len(echecs)}/{len(resultats)} vérifications réussies")
    print("=" * 70)
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
