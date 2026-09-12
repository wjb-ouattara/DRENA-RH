# ========================================================================
# DRENAET-RH - Script de build de l'executable Windows
# ========================================================================

Write-Host "========================================" -ForegroundColor Yellow
Write-Host "  DRENAET-RH - Build de l'executable" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow

# --- Verifier que PyInstaller est installe ---
$pyinstallerVersion = pip show pyinstaller 2>$null

if (-not $pyinstallerVersion) {
    Write-Host "`nPyInstaller n'est pas installe. Installation..." -ForegroundColor Cyan
    pip install pyinstaller
}

# --- Nettoyer les anciens builds ---
Write-Host "`n[1/4] Nettoyage des anciens builds..." -ForegroundColor Cyan

if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}

if (Test-Path "dist\DRENAET-RH") {

    # Garder une sauvegarde de l'ancienne base de donnees
    if (Test-Path "dist\DRENAET-RH\data\drenaet.db") {
        Write-Host "  Sauvegarde de l'ancienne base de donnees..." -ForegroundColor Cyan

        Copy-Item `
            "dist\DRENAET-RH\data\drenaet.db" `
            -Destination "drenaet_backup_temp.db" `
            -Force
    }

    Remove-Item -Recurse -Force "dist\DRENAET-RH"
}

# --- Lancer PyInstaller ---
Write-Host "`n[2/4] Compilation avec PyInstaller (peut prendre 2-5 minutes)..." -ForegroundColor Cyan

pyinstaller main.spec

if (-not (Test-Path "dist\DRENAET-RH\DRENAET-RH.exe")) {
    Write-Host "`nERREUR : la compilation a echoue. Voir les messages ci-dessus." -ForegroundColor Red
    exit 1
}

# --- Copier/restaurer le dossier data ---
Write-Host "`n[3/4] Mise en place de la base de donnees..." -ForegroundColor Cyan

New-Item `
    -ItemType Directory `
    -Force `
    -Path "dist\DRENAET-RH\data" | Out-Null

if (Test-Path "drenaet_backup_temp.db") {

    Move-Item `
        "drenaet_backup_temp.db" `
        -Destination "dist\DRENAET-RH\data\drenaet.db" `
        -Force

    Write-Host "  Base de donnees existante restauree." -ForegroundColor Green

}
elseif (Test-Path "data\drenaet.db") {

    Copy-Item `
        "data\drenaet.db" `
        -Destination "dist\DRENAET-RH\data\drenaet.db" `
        -Force

    Write-Host "  Base de donnees de developpement copiee." -ForegroundColor Green

}
else {

    Write-Host "  Aucune base existante trouvee : elle sera creee au premier lancement." -ForegroundColor Yellow
}

# --- Creer logs ---
New-Item `
    -ItemType Directory `
    -Force `
    -Path "dist\DRENAET-RH\logs" | Out-Null

# --- Copier outputs ---
if (Test-Path "outputs") {

    Copy-Item `
        "outputs" `
        -Destination "dist\DRENAET-RH\outputs" `
        -Recurse `
        -Force

}
else {

    New-Item `
        -ItemType Directory `
        -Force `
        -Path "dist\DRENAET-RH\outputs" | Out-Null
}

# --- Fin ---
Write-Host "`n[4/4] Termine !" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Executable pret : dist\DRENAET-RH\DRENAET-RH.exe" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host "`nPour distribuer l'application, copie TOUT le dossier :" -ForegroundColor Cyan
Write-Host "  dist\DRENAET-RH\" -ForegroundColor White
Write-Host "(pas juste le fichier .exe seul)" -ForegroundColor Cyan