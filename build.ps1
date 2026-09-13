# ========================================================================
# DRENAET-RH - Script de build de l'executable Windows (mode ONEFILE)
# ========================================================================
# Produit UN SEUL fichier autonome : dist\DRENAET-RH.exe
#
# Contrairement a l'ancien mode "onedir", ce fichier peut etre copie
# n'importe ou (Bureau, cle USB, autre poste) et lance seul.
#
# Les donnees (base, documents generes, logs) ne sont PLUS a cote de
# l'executable : elles vont dans %LOCALAPPDATA%\DRENAET-RH.
# Ce script ne manipule donc plus dist\DRENAET-RH\data.
#
# Utilisation :  .\build.ps1
# ========================================================================

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Yellow
Write-Host "  DRENAET-RH - Build de l'executable" -ForegroundColor Yellow
Write-Host "  Mode : ONEFILE (un seul fichier)" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow

# --- Se placer dans le dossier du script ---
Set-Location -Path $PSScriptRoot

# --- Choisir l'interpreteur : venv en priorite ---
if (Test-Path "venv\Scripts\python.exe") {
    $python = ".\venv\Scripts\python.exe"
    Write-Host "`nEnvironnement virtuel detecte : venv" -ForegroundColor Cyan
}
else {
    $python = "python"
    Write-Host "`nATTENTION : aucun venv trouve, utilisation du Python global." -ForegroundColor Yellow
}

# --- Verifier que PyInstaller est disponible ---
# Note : les executables natifs (python.exe, pyinstaller) ecrivent leur
# progression sur la sortie d'erreur. Avec ErrorActionPreference a "Stop",
# PowerShell prendrait ces messages pour un echec : on repasse donc en
# "Continue" autour des appels natifs et on teste $LASTEXITCODE nous-memes.
$ErrorActionPreference = "Continue"

& $python -m PyInstaller --version *> $null

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nPyInstaller n'est pas installe. Installation..." -ForegroundColor Cyan
    & $python -m pip install pyinstaller
}

# --- Verifier la presence du fichier de configuration ---
if (-not (Test-Path "main.spec")) {
    Write-Host "`nERREUR : main.spec est introuvable." -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------------------
Write-Host "`n[1/4] Nettoyage des anciens builds..." -ForegroundColor Cyan

if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}

# Ancien mode onedir : le dossier n'a plus de raison d'exister
if (Test-Path "dist\DRENAET-RH") {
    Write-Host "  Suppression de l'ancien dossier onedir dist\DRENAET-RH..." -ForegroundColor Cyan
    Remove-Item -Recurse -Force "dist\DRENAET-RH"
}

if (Test-Path "dist\DRENAET-RH.exe") {
    Remove-Item -Force "dist\DRENAET-RH.exe"
}

# ------------------------------------------------------------------------
Write-Host "`n[2/4] Consolidation de la base modele..." -ForegroundColor Cyan

# La base tourne en mode WAL (journal_mode=WAL) : les ecritures recentes
# vivent dans drenaet.db-wal et le fichier .db principal peut rester quasi
# vide. Embarquer le .db seul produirait une base modele SANS donnees.
# Un checkpoint TRUNCATE replie le WAL dans le fichier principal.
if (Test-Path "data\drenaet.db") {

    & $python -c "import sqlite3; c = sqlite3.connect(r'data\drenaet.db'); c.execute('PRAGMA wal_checkpoint(TRUNCATE)'); c.close()" 2>&1 | ForEach-Object { "$_" }

    $tailleBase = [math]::Round((Get-Item "data\drenaet.db").Length / 1KB, 0)
    Write-Host "  Base consolidee : $tailleBase Ko" -ForegroundColor Green

    if ($tailleBase -lt 20) {
        Write-Host "  ATTENTION : la base modele semble vide." -ForegroundColor Yellow
        Write-Host "  L'application generera des donnees de demonstration" -ForegroundColor Yellow
        Write-Host "  (80 agents fictifs) au premier lancement." -ForegroundColor Yellow
    }
}
else {
    Write-Host "  Aucune base dans data\ : elle sera creee au premier lancement." -ForegroundColor Yellow
}

# ------------------------------------------------------------------------
Write-Host "`n[3/4] Compilation avec PyInstaller (2 a 5 minutes)..." -ForegroundColor Cyan

& $python -m PyInstaller main.spec --noconfirm 2>&1 | ForEach-Object { "$_" }

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nERREUR : PyInstaller s'est termine avec le code $LASTEXITCODE." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "dist\DRENAET-RH.exe")) {
    Write-Host "`nERREUR : la compilation a echoue. Voir les messages ci-dessus." -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------------------
Write-Host "`n[4/4] Termine !" -ForegroundColor Green

$exe = Get-Item "dist\DRENAET-RH.exe"
$tailleMo = [math]::Round($exe.Length / 1MB, 1)

Write-Host "========================================" -ForegroundColor Green
Write-Host "  Executable pret :" -ForegroundColor Green
Write-Host "  $($exe.FullName)" -ForegroundColor White
Write-Host "  Taille : $tailleMo Mo" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green

Write-Host "`nPour distribuer l'application :" -ForegroundColor Cyan
Write-Host "  Transmettre UNIQUEMENT le fichier DRENAET-RH.exe" -ForegroundColor White
Write-Host "  Il fonctionne depuis n'importe quel emplacement." -ForegroundColor White

Write-Host "`nDonnees de l'utilisateur (base, documents, logs) :" -ForegroundColor Cyan
Write-Host "  $env:LOCALAPPDATA\DRENAET-RH" -ForegroundColor White
Write-Host "  Elles sont conservees si l'executable est remplace" -ForegroundColor White
Write-Host "  (une mise a jour consiste a ecraser le .exe)." -ForegroundColor White
