"""Verifie que l'ecran de demarrage se construit et s'affiche sans erreur.

Rend le visuel dans un PNG pour controle, puis quitte. Ne remplace pas un
essai a l'ecran, mais garantit qu'aucune exception n'est levee.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication

from src.ui.widgets.splash_screen import SplashDemarrage

app = QApplication(sys.argv)
splash = SplashDemarrage()
splash.show()
splash.etape("Verification du splash...")

sortie = ROOT / "output" / "controle_splash.png"
sortie.parent.mkdir(parents=True, exist_ok=True)
ok = splash.grab().save(str(sortie))

print(f"image construite : {splash.pixmap().width()}x{splash.pixmap().height()}")
print(f"capture ecrite   : {ok} -> {sortie}")
splash.close()
