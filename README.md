# DRENAET-RH

> **Outil de gestion des ressources humaines** pour la Direction Régionale de l'Éducation Nationale, de l'Alphabétisation et de l'Enseignement Technique (DRENAET) de Katiola, Côte d'Ivoire.

Application desktop Python/PyQt6 permettant de gérer le personnel et de générer automatiquement les documents administratifs (autorisations d'absence, ordres de mission, attestations, décisions...) à partir d'une base de données centralisée.

---

## 🎯 Fonctionnalités

- 👥 **Gestion du personnel** : ajout, modification, recherche, photos
- 📄 **Génération automatique de documents** officiels en Word et PDF
- 🔢 **Numérotation automatique** des références (ex: 169/MENAET/DRENAET-KLA/SRH)
- 📊 **Tableau de bord** avec indicateurs et statistiques d'absences
- 🔐 **Authentification multi-utilisateurs** (3 comptes : 1 admin + 2 opérateurs)
- 💾 **Sauvegardes automatiques** quotidiennes
- ☁️ **Mode partagé optionnel** via OneDrive pour le travail en équipe

---

## 🛠️ Stack technique

| Composant | Technologie |
|---|---|
| Langage | Python 3.11+ |
| Interface graphique | PyQt6 |
| Base de données | SQLite (via SQLAlchemy ORM) |
| Documents Word | python-docx |
| Conversion PDF | docx2pdf (Windows) |
| Graphiques | matplotlib + pandas |
| Sécurité | bcrypt |
| Distribution | PyInstaller |

---

## 📦 Installation

### Prérequis
- Windows 10 / 11
- Python 3.11 ou supérieur ([télécharger ici](https://www.python.org/downloads/))
- Microsoft Word installé (pour conversion PDF)

### Étapes

```bash
# 1. Cloner ou télécharger le projet
cd drenaet-rh

# 2. Créer un environnement virtuel (recommandé)
python -m venv venv
venv\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer l'application
python main.py
```

Au premier lancement, la base de données est créée automatiquement avec 3 comptes utilisateurs par défaut et 50 agents fictifs pour tester.

### Comptes par défaut

| Login | Mot de passe | Rôle |
|---|---|---|
| `admin` | `admin2026` | Administrateur |
| `operateur1` | `passer123` | Opérateur |
| `operateur2` | `passer123` | Opérateur |

⚠️ **Changer ces mots de passe au premier lancement en production.**

---

## 📁 Structure du projet

```
drenaet-rh/
├── main.py                  # Point d'entrée
├── requirements.txt         # Dépendances
├── README.md
│
├── config/                  # Configuration globale
│   ├── settings.py
│   └── constants.py
│
├── data/                    # Données locales
│   ├── drenaet.db          # Base SQLite (créée au 1er lancement)
│   └── backups/            # Sauvegardes auto
│
├── ressources/              # Ressources statiques
│   ├── icons/
│   ├── images/
│   ├── styles/main.qss     # Style CSS de l'interface
│   └── templates/          # Modèles Word officiels
│
├── output/                  # Documents générés
│   └── 2025-2026/
│       ├── autorisations/
│       ├── ordres_mission/
│       └── attestations/
│
├── src/                     # Code source
│   ├── models/             # Couche données (SQLAlchemy)
│   ├── services/           # Couche métier
│   ├── ui/                 # Couche présentation (PyQt6)
│   └── utils/              # Utilitaires
│
└── tests/                   # Tests unitaires
```

---

## 🚀 Déploiement (création .exe)

Pour distribuer l'application au Service RH :

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=ressources/icons/app.ico --name=DRENAET-RH main.py
```

L'exécutable sera dans `dist/DRENAET-RH.exe`. Il suffit de le double-cliquer pour lancer.

---

## 📝 Roadmap

- [x] **Sprint 1** — Structure projet, base de données, authentification
- [ ] **Sprint 2** — Interface principale avec sidebar et navigation
- [ ] **Sprint 3** — Module Personnel (CRUD complet)
- [ ] **Sprint 4** — Module Documents v1 (Autorisation d'absence)
- [ ] **Sprint 5** — Module Documents v2 (Ordre mission, attestation, décision)
- [ ] **Sprint 6** — Module Absences + Statistiques
- [ ] **Sprint 7** — Polish UI + Sauvegardes
- [ ] **Sprint 8** — Distribution .exe + Documentation utilisateur

---

## 📄 Licence

Projet académique — Tous droits réservés à la DRENAET de Katiola, Côte d'Ivoire.

## 👨‍💻 Auteur

Développé dans le cadre d'un projet de génie informatique (4ème année).
