# 🎨 SPRINT 2 — UI Shell : Mode d'emploi

Cette version ajoute l'**interface graphique PyQt6** au projet DRENAET-RH.

## 📦 Ce qui est nouveau (par rapport au Sprint 1)

### Nouveaux fichiers créés

**Feuille de style** :
- `ressources/styles/main.qss` — Styles indigo/violet (402 lignes)

**Widgets réutilisables** :
- `src/ui/widgets/kpi_card.py` — Carte d'indicateur
- `src/ui/widgets/sidebar_button.py` — Bouton de menu

**Fenêtres** :
- `src/ui/login_window.py` — Écran de connexion (carte blanche sur fond indigo, icône graduation cap)
- `src/ui/main_window.py` — Fenêtre principale (sidebar + header + zone centrale)
- `src/ui/dashboard_view.py` — Page d'accueil (4 KPI cards + carte de bienvenue avec dégradé)
- `src/ui/placeholder_view.py` — Pages "Module à venir" pour les sprints suivants
- `src/ui/app.py` — Orchestrateur (cycle login ↔ main)

**Modifié** :
- `main.py` — Lance maintenant l'interface PyQt6 au lieu d'un message console
- `config/settings.py` — Ajout de `APP_FULL_NAME` et `APP_ORGANIZATION`

## 🚀 Installation sur Windows

### Étape 1 : Mettre à jour les dépendances

Si tu n'as pas encore PyQt6 et qtawesome dans ton environnement virtuel :

```powershell
# Dans le dossier D:\drenaet-rh, avec venv activé
pip install PyQt6 qtawesome
```

### Étape 2 : Lancer l'application

```powershell
python main.py
```

**Une fenêtre graphique devrait s'ouvrir** : l'écran de login avec carte blanche sur fond indigo.

### Étape 3 : Se connecter

Utilise un des comptes par défaut :

| Login | Mot de passe | Rôle |
|---|---|---|
| `admin` | `admin2026` | Administrateur |
| `operateur1` | `passer123` | Opérateur |
| `operateur2` | `passer123` | Opérateur |

## 🎯 Ce que tu peux faire dans cette version

✅ **Te connecter** avec login/mot de passe
✅ **Voir le dashboard** avec 4 KPI (80 agents fictifs, 19 structures, 0 docs, 0 absences)
✅ **Naviguer dans la sidebar** entre les 7 menus :
   - 📊 Dashboard (fonctionnel)
   - 👥 Personnel (placeholder)
   - 📄 Documents (placeholder)
   - 📅 Absences (placeholder)
   - 📈 Statistiques (placeholder)
   - ⚙️ Paramètres (placeholder)
   - 🛡️ Administration (placeholder)
✅ **Te déconnecter** (retour à l'écran de login)
✅ **Te reconnecter** sans relancer l'app

## 🔍 Ce qui n'est PAS encore là (sprints suivants)

❌ Liste / ajout / modification des agents (Sprint 3)
❌ Import Excel en masse (Sprint 4)
❌ Génération de documents (Sprints 5-6)
❌ Statistiques avancées et graphiques (Sprint 7)
❌ Exécutable .exe Windows (Sprint 8)

## ⚠️ Si quelque chose ne marche pas

### Erreur "No module named PyQt6"
```powershell
pip install PyQt6 qtawesome
```

### L'app se lance mais sans style (look gris/blanc cassé)
Vérifier que le fichier `ressources/styles/main.qss` existe bien.

### Erreur "no such table: utilisateurs"
La base de données s'est corrompue. Supprime `data/drenaet.db` et relance `python main.py` (la BD sera recréée avec le seed).

### Erreur d'imports
Vérifier que tu lances bien depuis le **dossier racine** du projet (`D:\drenaet-rh`), pas depuis un sous-dossier.

## 📝 Note importante sur les tests

Si tu veux relancer les tests :

```powershell
# Reset propre de la BD avant les tests
del data\drenaet.db

# Lancer main.py UNE FOIS pour le seed complet
python main.py
# Fermer l'app avec la croix

# Maintenant les tests passent
python tests\test_sprint1_database.py    # ATTENTION : drop la BD
python main.py                             # Re-seed
python tests\test_sprint1_auth.py
python tests\check_seed.py
```

L'ordre est important parce que `test_sprint1_database.py` réinitialise la BD avec juste 1 admin pour ses tests internes.

---

**Prochaine étape : Sprint 3 — Module Personnel (CRUD complet)**

Une fois que tu valides que l'interface s'ouvre bien chez toi, on attaque le vrai module de gestion du personnel : liste avec recherche, formulaire d'ajout, modification, fiche détaillée.
