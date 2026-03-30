@echo off
setlocal enabledelayedexpansion

echo.
echo ================================================================
echo   FLASH PROXY INTERCEPTOR - INICIANDO
echo ================================================================
echo.

:: ── Verifica se o script Python existe ────────────────────────────
if not exist "flash_interceptor.py" (
    echo [ERRO] flash_interceptor.py nao encontrado.
    echo        Execute este .bat na mesma pasta do projeto.
    pause
    exit /b 1
)

:: ── Verifica mitmproxy ────────────────────────────────────────────
mitmdump --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] mitmproxy nao encontrado. Execute setup.bat primeiro.
    pause
    exit /b 1
)

:: ── Configura proxy no sistema ────────────────────────────────────
set http_proxy=http://127.0.0.1:8080
set https_proxy=http://127.0.0.1:8080
set HTTP_PROXY=http://127.0.0.1:8080
set HTTPS_PROXY=http://127.0.0.1:8080

:: ── Cria mm.cfg para Flash Player debug ──────────────────────────
echo HTTPProxy=127.0.0.1:8080>       "%USERPROFILE%\mm.cfg"
echo TraceOutputFileEnable=1>>        "%USERPROFILE%\mm.cfg"
echo ErrorReportingEnable=1>>         "%USERPROFILE%\mm.cfg"
echo MaxWarnings=50>>                 "%USERPROFILE%\mm.cfg"
echo PolicyFileLog=1>>                "%USERPROFILE%\mm.cfg"
echo.

echo [OK] Proxy configurado em 127.0.0.1:8080
echo [OK] mm.cfg criado em %USERPROFILE%\mm.cfg
echo.

:: ── Cria pastas de saida ──────────────────────────────────────────
if not exist "captured\swf"    mkdir "captured\swf"
if not exist "captured\logs"   mkdir "captured\logs"
if not exist "captured\tokens" mkdir "captured\tokens"

:: ── Verifica se quer abrir o Flash junto ──────────────────────────
set FLASH_EXE=
set FLASH_SWF=

if "%~1" neq "" (
    set FLASH_EXE=%~1
    echo [*] Flash Player: %FLASH_EXE%
)
if "%~2" neq "" (
    set FLASH_SWF=%~2
    echo [*] SWF alvo:     %FLASH_SWF%
)

:: ── Abre Flash Player em janela separada se fornecido ─────────────
if "%FLASH_EXE%" neq "" (
    echo.
    echo [*] Aguardando 3s para o proxy subir antes de abrir o Flash...
    timeout /t 3 /nobreak >nul
    if "%FLASH_SWF%" neq "" (
        start "" "%FLASH_EXE%" "%FLASH_SWF%"
    ) else (
        start "" "%FLASH_EXE%"
    )
    echo [OK] Flash Player iniciado.
)

:: ── Inicia o mitmproxy com o addon ────────────────────────────────
echo.
echo [*] Iniciando interceptador na porta 8080...
echo     Pressione Ctrl+C para parar.
echo ================================================================
echo.

mitmdump ^
    --listen-host 0.0.0.0 ^
    --listen-port 8080 ^
    --scripts flash_interceptor.py ^
    --set ssl_insecure=true ^
    --set connection_strategy=lazy ^
    --showhost

:: ── Ao encerrar ────────────────────────────────────────────────────
echo.
echo ================================================================
echo   PROXY ENCERRADO
echo ================================================================
echo.
echo  Arquivos capturados:
echo    SWF:    captured\swf\
echo    Logs:   captured\logs\
echo    Tokens: captured\tokens\
echo.

:: Remove configuracao de proxy do sistema
set http_proxy=
set https_proxy=
set HTTP_PROXY=
set HTTPS_PROXY=

pause
