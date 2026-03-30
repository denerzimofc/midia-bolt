@echo off
setlocal enabledelayedexpansion

echo.
echo ================================================================
echo   FLASH PROXY INTERCEPTOR - SETUP
echo ================================================================
echo.

:: ── 1. Verifica Python ────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH.
    echo        Instale Python 3.10+ em: https://python.org/downloads
    echo        Marque "Add Python to PATH" durante a instalacao!
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo [OK] %%v

:: ── 2. Atualiza pip ───────────────────────────────────────────────
echo.
echo [*] Atualizando pip...
python -m pip install --upgrade pip --quiet

:: ── 3. Instala mitmproxy ──────────────────────────────────────────
echo [*] Instalando mitmproxy...
python -m pip install mitmproxy --quiet
if errorlevel 1 (
    echo [ERRO] Falha ao instalar mitmproxy
    pause
    exit /b 1
)
echo [OK] mitmproxy instalado.

:: ── 4. Gera certificados mitmproxy ───────────────────────────────
echo.
echo [*] Gerando certificados TLS do mitmproxy...
mitmdump --version >nul 2>&1
if errorlevel 1 (
    :: tenta via python -m
    python -m mitmproxy.tools.main --version >nul 2>&1
)

:: Roda uma vez para gerar o ~/.mitmproxy/mitmproxy-ca-cert.pem
start /B mitmdump --listen-port 9999 --quiet 2>nul
timeout /t 3 /nobreak >nul
taskkill /F /IM mitmdump.exe >nul 2>&1

set CERT_DIR=%USERPROFILE%\.mitmproxy
echo [OK] Certificados em: %CERT_DIR%

:: ── 5. Instrucoes para instalar o certificado no Windows ─────────
echo.
echo ================================================================
echo   IMPORTANTE: Instale o certificado CA do mitmproxy
echo ================================================================
echo.
echo  1. Abra: %CERT_DIR%\mitmproxy-ca-cert.p12
echo  2. Clique em "Instalar Certificado"
echo  3. Selecione: "Computador Local"
echo  4. Selecione: "Autoridades de Certificacao Raiz Confiaveis"
echo  5. Confirme a instalacao
echo.
echo  Ou rode como ADMINISTRADOR o comando abaixo:
echo.
echo  certutil -addstore root "%CERT_DIR%\mitmproxy-ca-cert.pem"
echo.

:: Tenta instalar automaticamente (requer elevacao)
net session >nul 2>&1
if not errorlevel 1 (
    echo [*] Instalando certificado automaticamente (modo admin)...
    certutil -addstore -f root "%CERT_DIR%\mitmproxy-ca-cert.pem" >nul 2>&1
    if not errorlevel 1 (
        echo [OK] Certificado instalado no sistema.
    ) else (
        echo [AVISO] Nao foi possivel instalar automaticamente.
        echo         Siga as instrucoes manuais acima.
    )
) else (
    echo [AVISO] Sem privilegios de admin - instale o certificado manualmente.
)

:: ── 6. Cria pastas de saida ───────────────────────────────────────
if not exist "captured\swf"    mkdir "captured\swf"
if not exist "captured\logs"   mkdir "captured\logs"
if not exist "captured\tokens" mkdir "captured\tokens"
echo [OK] Pastas criadas em: captured\

:: ── 7. Instrucoes Flash Player ────────────────────────────────────
echo.
echo ================================================================
echo   CONFIGURACAO DO FLASH PLAYER STANDALONE
echo ================================================================
echo.
echo  Opcao A - Via variavel de ambiente (automatico pelo start_proxy.bat):
echo    set http_proxy=http://127.0.0.1:8080
echo    set https_proxy=http://127.0.0.1:8080
echo    FlashPlayerDebugger.exe jogo.swf
echo.
echo  Opcao B - Via mm.cfg (Flash Player debug):
echo    Crie: %%USERPROFILE%%\mm.cfg
echo    Conteudo:
echo      HTTPProxy=127.0.0.1:8080
echo      TraceOutputFileEnable=1
echo      ErrorReportingEnable=1
echo      MaxWarnings=50
echo.
echo ================================================================
echo   SETUP CONCLUIDO!
echo   Execute: start_proxy.bat
echo ================================================================
echo.
pause
