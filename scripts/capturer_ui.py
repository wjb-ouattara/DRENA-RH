"""
Capture d'écran (jetable) — DRENAET-RH.

Produit deux images dans output/captures/ :
  - popup_mot_de_passe.png : la popup de changement de mot de passe
  - sidebar_operateur.png  : la sidebar d'un opérateur (sans Paramètres
                             ni Administration)

Lancer avec :  venv\\Scripts\\python.exe scripts\\capturer_ui.py
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from PyQt6.QtWidgets import QApplication

from config import settings
from src.models import init_db, get_session, Utilisateur
from src.services.auth_service import AuthService, hash_password

DOSSIER = settings.OUTPUT_DIR / "captures"


def main():
    init_db()
    DOSSIER.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)

    # Comptes temporaires (un par rôle)
    with get_session() as db:
        for login, role, nom in (("zz_capture", "operateur", "Kone Mamadou"),
                                 ("zz_capture_admin", "admin", "Traore Awa")):
            existant = db.query(Utilisateur).filter_by(login=login).first()
            if existant:
                db.delete(existant)
            db.flush()
            db.add(Utilisateur(
                login=login,
                mot_de_passe_hash=hash_password("motdepasse1"),
                nom_complet=nom,
                role=role,
                actif=True,
            ))

    AuthService.authenticate("zz_capture", "motdepasse1")

    from src.ui.main_window import MainWindow
    from src.ui.widgets.change_password_dialog import ChangePasswordDialog

    fenetre = MainWindow()
    fenetre.show()
    app.processEvents()

    popup = ChangePasswordDialog(fenetre)
    popup.show()
    app.processEvents()
    popup.grab().save(str(DOSSIER / "popup_mot_de_passe.png"))
    popup.close()

    fenetre.sidebar.grab().save(str(DOSSIER / "sidebar_operateur.png"))
    fenetre.close()

    # --- Sidebar administrateur ---
    AuthService.logout()
    AuthService.authenticate("zz_capture_admin", "motdepasse1")
    fenetre_admin = MainWindow()
    fenetre_admin.show()
    app.processEvents()
    fenetre_admin.sidebar.grab().save(str(DOSSIER / "sidebar_admin.png"))
    fenetre_admin.close()

    # Nettoyage
    AuthService.logout()
    with get_session() as db:
        for login in ("zz_capture", "zz_capture_admin"):
            u = db.query(Utilisateur).filter_by(login=login).first()
            if u:
                db.delete(u)

    print(f"Captures enregistrees dans {DOSSIER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
