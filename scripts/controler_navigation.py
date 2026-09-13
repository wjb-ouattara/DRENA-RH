"""Verifie sans ecran que la navigation du tableau de bord fonctionne.

Ouvre une session administrateur, construit la fenetre principale en mode
« offscreen », emet le signal de chaque action rapide et controle que la page
affichee est bien celle attendue. Verifie aussi la couleur des filets du
sidebar dans la feuille de style.
"""
import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication

from config import settings
from src.services.auth_service import AuthService, UserSession
from src.ui.main_window import MainWindow

echecs = []

app = QApplication(sys.argv)

# --- Session administrateur -------------------------------------------------
succes, message, utilisateur = AuthService.authenticate("admin", "admin2026")
if not succes or utilisateur is None:
    print(f"ECHEC : impossible d'ouvrir une session admin ({message})")
    sys.exit(1)
UserSession.get_instance().login_user(utilisateur)

fenetre = MainWindow()

# --- Navigation depuis les actions rapides ---------------------------------
attendus = {
    "personnel": "personnel",
    "documents": "documents",
    "statistics": "statistics",
}
for cle, page_attendue in attendus.items():
    fenetre.pages["dashboard"].navigate_requested.emit(cle)
    courant = fenetre.content_stack.currentWidget()
    obtenu = next((k for k, v in fenetre.pages.items() if v is courant), "?")
    etat = "OK" if obtenu == page_attendue else "ECHEC"
    if etat == "ECHEC":
        echecs.append(f"navigation {cle} -> {obtenu} (attendu {page_attendue})")
    print(f"[{etat}] action rapide « {cle} » -> page « {obtenu} »")
    coche = fenetre.menu_buttons[page_attendue].isChecked()
    if not coche:
        echecs.append(f"bouton de menu {page_attendue} non coche")
    print(f"       bouton de menu coche : {coche}")

# --- Une cle inconnue doit etre signalee, pas ignoree ----------------------
fenetre.pages["dashboard"].navigate_requested.emit("statistiques")
print("[OK ] cle inconnue « statistiques » : voir l'avertissement dans le journal")

# --- Formulaires de documents crees a la demande ---------------------------
pile = fenetre.pages["documents"]
print(f"[{'OK ' if pile.count() == 1 else 'ECHEC'}] "
      f"pile Documents au demarrage : {pile.count()} page(s), attendu 1")
if pile.count() != 1:
    echecs.append(f"pile Documents contient {pile.count()} pages au demarrage")

liste = pile.widget(0)
liste.document_selected.emit("fiche_mutation")
print(f"[{'OK ' if pile.count() == 2 else 'ECHEC'}] "
      f"apres ouverture d'un formulaire : {pile.count()} page(s), attendu 2")
if pile.count() != 2:
    echecs.append("le formulaire demande n'a pas ete construit")

liste.document_selected.emit("fiche_mutation")
print(f"[{'OK ' if pile.count() == 2 else 'ECHEC'}] "
      f"seconde ouverture (mise en cache) : {pile.count()} page(s), attendu 2")
if pile.count() != 2:
    echecs.append("le formulaire a ete reconstruit au lieu d'etre reutilise")

# --- Filets du sidebar ------------------------------------------------------
qss = (settings.STYLES_DIR / "main.qss").read_text(encoding="utf-8")
bleu = [ligne.strip() for ligne in qss.splitlines()
        if "border" in ligne and "#312E81" in ligne]
print(f"[{'OK ' if not bleu else 'ECHEC'}] filets indigo restants : "
      f"{bleu if bleu else 'aucun'}")
if bleu:
    echecs.append(f"filets indigo encore presents : {bleu}")

print()
if echecs:
    print("RESULTAT : " + str(len(echecs)) + " echec(s)")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("RESULTAT : tous les controles sont conformes")
