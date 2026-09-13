# Jeux d'essai — DRENAET-RH

Ce dossier rassemble de quoi éprouver les deux fonctions centrales du
logiciel sans ressaisir des données à la main : la **génération des
documents officiels** et l'**import du personnel depuis Excel**.

Tous ces fichiers sont reproductibles à volonté par les scripts indiqués
plus bas.

---

## 1. Les 8 documents officiels — `documents/`

Un exemplaire de chaque document, renseigné avec des données plausibles de
la région du Hambol (agents, structures et références d'arrêtés cohérents).

| Fichier | Cas représenté |
|---|---|
| `1_autorisation_dabsence.pdf` | Absence de 3 jours à Bouaké, **avec intérim assuré** |
| `2_ordre_de_mission.pdf` | Tournée d'inspection de 5 jours, hébergement assuré, repas non fournis |
| `3_attestation_de_travail.pdf` | Pièce pour un dossier de prêt bancaire |
| `4_attestation_de_presence.pdf` | Pièce destinée à la Direction de la Solde |
| `5_titre_de_conges.pdf` | Congé annuel de fin d'année, destination Abidjan |
| `6_certificat_de_prise_de_service.pdf` | Prise de fonction après arrêté d'affectation |
| `7_certificat_de_cessation_de_service.pdf` | Départ pour mutation |
| `8_fiche_de_mutation.pdf` | Candidature Chef de Circonscription, **3 vœux** |

### Ce qu'il faut regarder sur chaque document

- **L'en-tête officiel** : bandeau à dégradé tricolore (orange pâle, blanc,
  vert pâle), Ministère et Direction des Ressources Humaines à gauche,
  armoirie au centre, République, devise et année scolaire à droite. Les
  tirets séparateurs sont noirs et le bandeau ne porte **aucun filet ni
  bordure**, conformément aux documents de référence.
- **Le bandeau de titre** : dessiné sous l'en-tête, sur fond crème, **détaché
  de celui-ci** et **exactement à la même largeur**. Les deux bandeaux
  s'alignent sur les marges du texte et ne couvrent donc pas toute la largeur
  de la feuille. Le titre et l'année scolaire tiennent sur une seule ligne,
  en noir :
  `FICHE D'INSCRIPTION | MUTATION - CHEF DE CIRCONSCRIPTION | 2026-2027`.
  Il est tracé sur le canevas et non dans le flux, car un flowable ReportLab
  ne peut pas dépasser la largeur du cadre de texte.
- **Les bandeaux de section** (fiche de mutation) : **gris**, texte blanc, à
  la même largeur que les bandeaux du haut. Le rouge et l'orange ont été
  écartés : ils ne correspondent pas au format de référence.
- **Les champs non renseignés restent vides** : aucun tiret de remplissage.
  La section « Informations sur la demande de l'agent » n'est ainsi qu'un
  bandeau sans contenu, comme sur la fiche de référence.
- **Le pied de page** : filet noir, nom complet de la Direction Régionale,
  BP, téléphone
  et adresse électronique, avec l'identifiant du document à gauche et la date
  d'édition à droite. Il ne comporte ni QR code, ni code-barres, ni
  pagination.
- **Le civilité** : « M. » ou « Mme » selon le sexe de l'agent — vérifier
  sur l'attestation de présence, établie pour une femme.
- **Les dates en toutes lettres** : « jeudi 15 octobre 2026 », et l'heure
  « 07 heures 30 minutes ».
- **Le bloc de clôture** : ampliations à gauche, lieu, date et titre du
  signataire à droite, côte à côte comme sur le document officiel signé. Le
  nom et le titre proviennent de l'écran **Paramètres**. Modifier le nom du
  Directeur Régional dans les Paramètres puis régénérer un document est le
  meilleur moyen de vérifier que le réglage est bien pris en compte.

### Formule de clôture des attestations

Le champ « But » a été retiré des deux formulaires d'attestation : le modèle
officiel de la DRENAET impose une formule fermée, toujours identique.

> En foi de quoi, la présente attestation lui est délivrée pour servir et
> valoir ce que de droit.

Cela supprime la répétition « pour servir et valoir servir et valoir… » que
l'ancien champ pouvait produire.

### Mise en page sur une seule page

Les huit documents tiennent désormais chacun sur **une seule page**, y
compris l'autorisation d'absence avec intérim et la fiche de mutation à
3 vœux. Le gain vient de trois ajustements : les ampliations et la signature
sont placées côte à côte (comme sur le document officiel signé), le tableau
de signatures a été resserré, et la recopie du pied de page qui figurait
dans le corps de cinq modèles a été supprimée puisque le vrai pied de page
la porte désormais sur chaque page.

### Régénérer les documents

```
venv\Scripts\python.exe scripts\generer_exemples_documents.py
```

Le script utilise l'agent `233329C` comme demandeur et `240187G` comme
intérimaire. Chaque document consomme un numéro officiel et s'inscrit dans
l'historique, exactement comme s'il avait été produit depuis l'interface :
la numérotation et la traçabilité sont donc éprouvées aussi.

---

## 2. Import Excel du personnel — 3 classeurs

Chaque classeur contient une feuille **« Mode d'emploi »** détaillant ce
qui doit se passer. Les trois ont été validés en simulation réelle
(40 contrôles automatiques, tous conformes).

### `import_personnel_valide.xlsx` — 20 agents corrects

Sert de point de départ. Sa particularité : **aucun en-tête ne porte le nom
interne du champ**, comme dans les fichiers réellement reçus des
établissements.

| En-tête du fichier | Champ reconnu |
|---|---|
| `N° Matricule` | matricule |
| `Nom et Prénoms` | nom **+** prénoms, séparés automatiquement |
| `Tél` | téléphone |
| `Catégorie` | grade |
| `Affectation` | structure |
| `Fonction actuelle` | fonction |

Éprouve aussi :

- la **détection de la ligne d'en-tête**, placée en ligne 4 sous un titre ;
- la **séparation nom/prénoms** : « OUATTARA Wahon Jean Baptiste » donne
  nom = `OUATTARA`, prénoms = `Wahon Jean Baptiste` (le mot en majuscules
  est le nom) ;
- une **colonne inconnue** (`Observations`) qui doit être signalée sans
  bloquer l'import.

Résultat attendu : **20 lignes valides, 0 rejet**.

### `import_personnel_avec_erreurs.xlsx` — 12 lignes, 7 fautives

Une colonne `ERREUR ATTENDUE` indique, ligne par ligne, ce que la
simulation doit reprocher. Les lignes à rejeter sont sur fond rouge.

Les 7 règles éprouvées : matricule manquant, nom manquant, sexe non
reconnu, date de naissance impossible (`32/13/1985`), agent de moins de
18 ans, prise de service antérieure à la naissance, e-mail mal formé.

Les 5 lignes valides éprouvent la normalisation : `koulibaly` devient
`KOULIBALY`, `féminin` devient `F`, `en service` devient `Actif`, et les
dates au format texte `17/06/1979` sont bien interprétées.

> **Lancez la simulation, mais ne validez pas l'import** : les 5 lignes
> valides seraient réellement créées en base.

Point à surveiller : la ligne `250005E` cite « Direction Régionale de
Bouaké », structure inexistante. L'application **crée automatiquement** les
structures inconnues. C'est pratique, mais une faute de frappe dans un nom
d'établissement crée donc un doublon silencieux.

### `import_mise_a_jour.xlsx` — 8 mises à jour + 2 nouveaux

À utiliser **après** avoir importé le premier fichier. Permet de comparer
les quatre stratégies de fusion. Décomptes vérifiés :

| Stratégie | Créations | Modifications | Ignorés |
|---|---|---|---|
| `UPSERT` | 2 | 8 | 0 |
| `INSERT_ONLY` | 2 | 0 | 8 |
| `UPDATE_ONLY` | 0 | 8 | 2 |
| `REPLACE` | vide la structure avant de réimporter — à tester après sauvegarde |

La colonne `CHANGEMENT PAR RAPPORT AU FICHIER 1` précise ce qui doit
bouger : promotions, mutations, avancements de grade, changements de statut
(`En congé`, `Muté`, `Retraité`). Contrôle le plus parlant : après un
`UPSERT`, le matricule `233329C` doit afficher « Directeur Régional » au
lieu de « Chef de Service RH ».

### Régénérer les classeurs

```
venv\Scripts\python.exe scripts\generer_excel_exemple.py
venv\Scripts\python.exe scripts\valider_excel_exemple.py
```

Le second script rejoue les trois classeurs dans la simulation et compare
les résultats aux attentes ci-dessus.

> Attention : `valider_excel_exemple.py` **importe réellement** le premier
> fichier, afin de pouvoir vérifier les décomptes du troisième.

---

## 3. Parcours de test conseillé

1. **Documents seuls** — ouvrez les 8 PDF de `documents/`. C'est le plus
   rapide pour juger la mise en page et repérer les deux débordements.
2. **Import propre** — Personnel ▸ Importer depuis Excel ▸
   `import_personnel_valide.xlsx`. Simulez, contrôlez la correspondance des
   colonnes, validez. 20 agents doivent apparaître dans la liste.
3. **Contrôle des rejets** — même écran avec
   `import_personnel_avec_erreurs.xlsx`. Simulez, comparez à la colonne
   `ERREUR ATTENDUE`, **puis annulez**.
4. **Mise à jour** — `import_mise_a_jour.xlsx` en `UPSERT`, puis vérifiez
   que `233329C` est devenu Directeur Régional.
5. **Documents sur données importées** — générez une autorisation d'absence
   pour un agent importé, avec un autre agent importé comme intérimaire.
   Vérifiez au passage que l'absence est bien créée dans le module
   Absences.
6. **Paramètres** — changez le nom du Directeur Régional, régénérez un
   document, vérifiez que la signature a suivi.
7. **Historique** — Personnel ▸ Historique des imports doit lister les
   opérations, et le journal d'audit (Administration) tracer les créations.
