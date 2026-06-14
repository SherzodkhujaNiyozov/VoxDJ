# Aria — yagona .exe yig'ish (PyInstaller, --noconsole, tray ilova)
# Ishlatish:  ./build.ps1
# Natija:     dist/Aria.exe
#
# Eslatma: modellar (models/) .exe ichiga QO'SHILMAYDI — ular katta. .exe yonida
# models/ papkasi bo'lishi yoki birinchi marta download_models.py orqali yuklanishi kerak.

$ErrorActionPreference = "Stop"

# Venv borligini tekshiramiz
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Avval venv yarating va deps o'rnating:" -ForegroundColor Yellow
    Write-Host "  py -m venv .venv"
    Write-Host "  .venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller"
    exit 1
}

$py = ".venv\Scripts\python.exe"

# PyInstaller bormi?
& $py -m pip show pyinstaller *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller o'rnatilmoqda..." -ForegroundColor Cyan
    & $py -m pip install pyinstaller
}

Write-Host "Aria yig'ilmoqda..." -ForegroundColor Cyan
& $py -m PyInstaller `
    --noconfirm `
    --onefile `
    --noconsole `
    --name Aria `
    --collect-all vosk `
    --hidden-import comtypes `
    --hidden-import pyttsx3.drivers `
    --hidden-import pyttsx3.drivers.sapi5 `
    aria\__main__.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nTayyor: dist\Aria.exe" -ForegroundColor Green
    Write-Host "models\ papkasini .exe yoniga qo'ying yoki download_models.py ishlating."
} else {
    Write-Host "Build xatosi." -ForegroundColor Red
    exit 1
}
