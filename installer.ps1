# Installation automatique de WebCognitive Engine (Windows)
#
# Lancement : double-clic sur installer.bat, ou dans PowerShell :
#     powershell -ExecutionPolicy Bypass -File installer.ps1
#
# Étapes (chacune est sautée si elle est déjà faite, on peut donc relancer le script sans risque) :
#   1. vérifier Python (3.10 ou plus)
#   2. créer l'environnement virtuel .venv et installer les dépendances
#   3. installer Ollama (via winget) s'il est absent, et le démarrer
#   4. télécharger le modèle de langage (mistral par défaut)
#   5. calculer les vecteurs du corpus (5 à 10 min la première fois)
#   6. remplir la base vectorielle ChromaDB
param(
    [string]$Modele = "mistral"   # autre choix plus léger : -Modele llama3.2:3b
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Etape($numero, $texte) { Write-Host "`n[$numero/6] $texte" -ForegroundColor Cyan }
function Ok($texte) { Write-Host "      OK  $texte" -ForegroundColor Green }
function Info($texte) { Write-Host "      $texte" }
function Arret($texte) {
    Write-Host "`n  ERREUR : $texte" -ForegroundColor Red
    Read-Host "`nAppuyez sur Entrée pour fermer"
    exit 1
}
function Executer([string]$programme, [string[]]$arguments, [string]$erreur) {
    & $programme @arguments
    if ($LASTEXITCODE -ne 0) { Arret $erreur }
}

Write-Host "=== Installation de WebCognitive Engine ===" -ForegroundColor White
Info "Dossier : $PSScriptRoot"

# ------------------------------------------------------------------ 1. Python
Etape 1 "Python"
$pyExe = $null; $pyArgs = @(); $version = $null
foreach ($candidat in @("py -3.12", "py -3", "python")) {
    $morceaux = $candidat -split " "
    $exe = $morceaux[0]
    $options = @($morceaux | Select-Object -Skip 1)
    try {
        $v = & $exe @options -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $v -and [version]"$v" -ge [version]"3.10") {
            $pyExe = $exe; $pyArgs = $options; $version = $v; break
        }
    } catch { }
}
if (-not $pyExe) {
    Arret "Python 3.10 ou plus est introuvable. Installez Python 3.12 depuis https://www.python.org/downloads/ (cochez « Add python.exe to PATH »), puis relancez."
}
Ok "Python $version"

# ------------------------------------------------------------------ 2. Environnement virtuel + dépendances
Etape 2 "Environnement virtuel et dépendances (quelques minutes la première fois)"
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Executer $pyExe ($pyArgs + @("-m", "venv", ".venv")) "impossible de créer l'environnement virtuel .venv"
    Ok "environnement .venv créé"
} else {
    Ok "environnement .venv déjà présent"
}
Executer $venvPython @("-m", "pip", "install", "--upgrade", "pip", "--quiet") "mise à jour de pip impossible"
Executer $venvPython @("-m", "pip", "install", "-r", "requirements.txt", "--quiet") "installation des dépendances impossible (connexion Internet ?)"
Ok "dépendances installées (requirements.txt)"

# ------------------------------------------------------------------ 3. Ollama
Etape 3 "Ollama (LLM local)"
$ollamaDir = Join-Path $env:LOCALAPPDATA "Programs\Ollama"
if (Test-Path $ollamaDir) { $env:Path = "$ollamaDir;$env:Path" }
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Info "Ollama absent : installation avec winget…"
        & winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
        $env:Path = "$ollamaDir;$env:Path"
    }
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
        Arret "Ollama n'est pas installé. Téléchargez-le sur https://ollama.com/download, installez-le, puis relancez ce script."
    }
}
Ok "Ollama installé"

function OllamaRepond {
    try { Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 | Out-Null; return $true } catch { return $false }
}
if (-not (OllamaRepond)) {
    Info "démarrage d'Ollama…"
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 30 -and -not (OllamaRepond); $i++) { Start-Sleep -Seconds 1 }
    if (-not (OllamaRepond)) { Arret "Ollama ne démarre pas. Lancez l'application Ollama depuis le menu Démarrer, puis relancez ce script." }
}
Ok "Ollama répond sur http://127.0.0.1:11434"

# ------------------------------------------------------------------ 4. Modèle de langage
Etape 4 "Modèle de langage « $Modele » (≈ 4 Go la première fois)"
Executer "ollama" @("pull", $Modele) "téléchargement du modèle $Modele impossible"
Ok "modèle $Modele prêt"

# ------------------------------------------------------------------ 5. Vecteurs du corpus
Etape 5 "Vecteurs du corpus (étape 3 du projet)"
if (-not (Test-Path "data\embeddings\embeddings.npy")) {
    Info "calcul en cours : 5 à 10 minutes sur un processeur classique…"
    Executer $venvPython @("scripts\build_embeddings.py") "le calcul des vecteurs a échoué"
    Ok "vecteurs calculés"
} else {
    Ok "vecteurs déjà calculés (data\embeddings\embeddings.npy)"
}

# ------------------------------------------------------------------ 6. Base vectorielle
Etape 6 "Base vectorielle ChromaDB (étape 4 du projet)"
Executer $venvPython @("scripts\build_vectordb.py") "le remplissage de la base vectorielle a échoué"
Ok "base vectorielle prête"

# ------------------------------------------------------------------ Fin
if ($Modele -ne "mistral") {
    Info "`nModèle choisi : $Modele. Avant de lancer l'application : `$env:WEBCOGNITIVE_LLM=`"$Modele`""
}
Write-Host "`n=== Installation terminée ===" -ForegroundColor Green
Write-Host "Pour démarrer l'application : double-clic sur lancer.bat (ou : .venv\Scripts\python.exe scripts\serve_api.py)"
Write-Host "Puis ouvrez http://127.0.0.1:8000/"
$reponse = Read-Host "`nLancer l'application maintenant ? (O/n)"
if ($reponse -notmatch "^[nN]") {
    $env:WEBCOGNITIVE_LLM = $Modele
    Start-Process powershell -ArgumentList "-NoProfile -Command `"Start-Sleep -Seconds 10; Start-Process 'http://127.0.0.1:8000/'`"" -WindowStyle Hidden
    & $venvPython "scripts\serve_api.py"
}
