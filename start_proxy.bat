@echo off
setlocal enabledelayedexpansion

echo.
echo ================================================================
echo   FLASH PROXY INTERCEPTOR - INICIANDO
echo ================================================================
echo.

:: Verifica se o script Python existe
if not exist "flash_interceptor.py" (
    echo [ERRO] flash_interceptor.py nao encontrado.
    echo        Este .bat deve estar na mesma pasta que flash_interceptor.py
    pause
    exit /b 1
)

:: Verifica mitmproxy
mitmdump --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] mitmproxy nao encontrado. Execute setup.bat primeiro.
    pause
    exit /b 1
)

:: Configura proxy nas variaveis de ambiente da sessao
set http_proxy=http://127.0.0.1:8080
set https_proxy=http://127.0.0.1:8080
set HTTP_PROXY=http://127.0.0.1:8080
set HTTPS_PROXY=http://127.0.0.1:8080

:: Configura proxy no Internet Options do Windows (usado pelo Flash standalone)
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 1 /f >nul 2>&1
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer /t REG_SZ /d "127.0.0.1:8080" /f >nul 2>&1

echo [OK] Proxy ativado: 127.0.0.1:8080

:: Cria mm.cfg para Flash Player debug (captura logs internos do Flash)
(
echo HTTPProxy=127.0.0.1:8080
echo TraceOutputFileEnable=1
echo ErrorReportingEnable=1
echo MaxWarnings=50
echo PolicyFileLog=1
) > "%USERPROFILE%\mm.cfg"

echo [OK] mm.cfg criado em %USERPROFILE%\mm.cfg

:: Cria pastas de saida
if not exist "captured\swf"    mkdir "captured\swf"
if not exist "captured\logs"   mkdir "captured\logs"
if not exist "captured\tokens" mkdir "captured\tokens"

echo [OK] Pastas criadas: captured\swf  captured\logs  captured\tokens
echo.
echo ----------------------------------------------------------------
echo   Certificado TLS (para capturar HTTPS):
echo   Com o proxy rodando, acesse no navegador: http://mitm.it
echo   Baixe e instale o certificado Windows.
echo ----------------------------------------------------------------
echo.
echo [*] Iniciando interceptador na porta 8080...
echo     Pressione Ctrl+C para parar.
echo ================================================================
echo.

:: Inicia o mitmproxy
:: Nota: use -s (nao --scripts) em versoes recentes do mitmproxy
mitmdump -s flash_interceptor.py --listen-host 0.0.0.0 --listen-port 8080 --set ssl_insecure=true

:: Ao encerrar: remove proxy do sistema
echo.
echo [*] Desativando proxy do sistema...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f >nul 2>&1
set http_proxy=
set https_proxy=
set HTTP_PROXY=
set HTTPS_PROXY=
echo [OK] Proxy do sistema DESATIVADO.
echo     Configuracoes aplicadas ao Internet Settings do Windows.
echo.
echo  Arquivos capturados:
echo    SWF:    captured\swf\
echo    Logs:   captured\logs\
echo    Tokens: captured\tokens\
echo.
echo [OK] Proxy desativado. Pressione qualquer tecla para fechar.
pause >nul
