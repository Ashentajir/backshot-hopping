@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"
title HopShot Client Launcher

set "SERVER=127.0.0.1"
set "DESTINATIONS=127.0.0.1"
set "PORT=10000"
set "QUIC_PORT=10001"
set "SEED=change-me"
set "PROFILE=balanced"
set "JITTER=64"
set "PORT_MIN=10000"
set "PORT_MAX=65000"
set "PREEMPTIVE=800"
set "DECLARED_UP=0"
set "MTU=0"
set "FEC_K=4"
set "FEC_M=4"
set "PROBE_COUNT=20"
set "PROBE_TIMEOUT=2000"
set "OBFS=false"
set "MASQ=false"
set "RAND_SRC=false"
set "VERBOSE=false"
set "JSON_LOGS=false"

:menu
cls
echo ==================================================
echo   HopShot Client Launcher
echo ==================================================
echo.
echo Current settings:
echo   Server         : %SERVER%
echo   Destinations   : %DESTINATIONS%
echo   Port           : %PORT%
echo   QUIC port      : %QUIC_PORT%
echo   Seed           : %SEED%
echo   Profile        : %PROFILE%
echo   Jitter         : %JITTER%
echo   Preemptive hop : %PREEMPTIVE%
echo   Obfs           : %OBFS%
echo   Masquerade     : %MASQ%
echo   Rand src port  : %RAND_SRC%
echo   Verbose        : %VERBOSE%
echo   JSON logs      : %JSON_LOGS%
echo.
echo 1. Connect and show logs
echo 2. Change destinations
echo 3. Change seed
echo 4. Change profile
echo 5. Change ports
echo 6. Change jitter
echo 7. Change preemptive hop
echo 8. Toggle obfs
echo 9. Toggle masquerade
echo A. Toggle random source port
echo B. Toggle verbose
echo C. Toggle JSON logs
echo S. Save config only
echo E. Exit
echo.
choice /c 123456789ABSE /n /m "Select an option:"

if errorlevel 13 goto :end
if errorlevel 12 goto :save_only
if errorlevel 11 goto :toggle_json
if errorlevel 10 goto :toggle_verbose
if errorlevel 9 goto :toggle_rand
if errorlevel 8 goto :toggle_masq
if errorlevel 7 goto :toggle_obfs
if errorlevel 6 goto :change_preemptive
if errorlevel 5 goto :change_jitter
if errorlevel 4 goto :change_ports
if errorlevel 3 goto :change_seed
if errorlevel 2 goto :change_destinations
if errorlevel 1 goto :start_client
goto :menu

:change_destinations
set "OLD_DESTINATIONS=%DESTINATIONS%"
set /p "DESTINATIONS=Enter destinations (comma separated) [%DESTINATIONS%]: "
if not defined DESTINATIONS (
  set "DESTINATIONS=%OLD_DESTINATIONS%"
)
for /f "tokens=1 delims=, " %%A in ("%DESTINATIONS%") do set "SERVER=%%~A"
goto :menu

:change_seed
set "OLD_SEED=%SEED%"
set /p "SEED=Shared seed [%SEED%]: "
if not defined SEED set "SEED=%OLD_SEED%"
goto :menu

:pick_profile
echo.
echo Choose profile:
echo   1. balanced
echo   2. reliable
echo   3. stealth
echo   4. throughput
choice /c 1234 /n /m "Profile:"
if errorlevel 4 set "PROFILE=throughput"
if errorlevel 3 set "PROFILE=stealth"
if errorlevel 2 set "PROFILE=reliable"
if errorlevel 1 set "PROFILE=balanced"
goto :menu

:change_ports
echo.
echo Current UDP port: %PORT%
echo Current QUIC port: %QUIC_PORT%
set "OLD_PORT=%PORT%"
set "OLD_QUIC_PORT=%QUIC_PORT%"
set /p "PORT=UDP port [%PORT%]: "
if not defined PORT set "PORT=%OLD_PORT%"
set /p "QUIC_PORT=QUIC port [%QUIC_PORT%]: "
if not defined QUIC_PORT set "QUIC_PORT=%OLD_QUIC_PORT%"
goto :menu

:change_jitter
set "OLD_JITTER=%JITTER%"
set /p "JITTER=Packet jitter bytes [%JITTER%]: "
if not defined JITTER set "JITTER=%OLD_JITTER%"
goto :menu

:change_preemptive
set "OLD_PREEMPTIVE=%PREEMPTIVE%"
set /p "PREEMPTIVE=Preemptive hop ms [%PREEMPTIVE%]: "
if not defined PREEMPTIVE set "PREEMPTIVE=%OLD_PREEMPTIVE%"
goto :menu

:toggle_obfs
if /i "%OBFS%"=="true" (
  set "OBFS=false"
) else (
  set "OBFS=true"
)
goto :menu

:toggle_masq
if /i "%MASQ%"=="true" (
  set "MASQ=false"
) else (
  set "MASQ=true"
)
goto :menu

:toggle_rand
if /i "%RAND_SRC%"=="true" (
  set "RAND_SRC=false"
) else (
  set "RAND_SRC=true"
)
goto :menu

:toggle_verbose
if /i "%VERBOSE%"=="true" (
  set "VERBOSE=false"
) else (
  set "VERBOSE=true"
)
goto :menu

:toggle_json
if /i "%JSON_LOGS%"=="true" (
  set "JSON_LOGS=false"
) else (
  set "JSON_LOGS=true"
)
goto :menu

:save_only
call :write_config
echo.
echo Saved client.config.json.
pause
goto :menu

:start_client
call :write_config
echo.
echo Connecting HopShot client with current settings...
call :resolve_python
if not defined PYTHON_LAUNCHER goto :menu
call %PYTHON_LAUNCHER% deploy.py client --config client.config.json
if errorlevel 1 pause
goto :menu

:write_config
setlocal EnableDelayedExpansion
set "DEST_JSON="
for %%A in (%DESTINATIONS%) do (
  if defined DEST_JSON (
    set "DEST_JSON=!DEST_JSON!, "
  )
  set "DEST_JSON=!DEST_JSON!""%%A""
)
(
  echo {
  echo   "server_port": %PORT%,
  echo   "quic_port": %QUIC_PORT%,
  echo   "port_min": %PORT_MIN%,
  echo   "port_max": %PORT_MAX%,
  echo   "shared_seed": "%SEED%",
  echo   "profile": "%PROFILE%",
  echo   "obfs": %OBFS%,
  echo   "rand_src_port": %RAND_SRC%,
  echo   "jitter_bytes": %JITTER%,
  echo   "preemptive_hop_ms": %PREEMPTIVE%,
  echo   "declared_up_kbps": %DECLARED_UP%,
  echo   "masquerade": %MASQ%,
  echo   "mtu": %MTU%,
  echo   "fec_k": %FEC_K%,
  echo   "fec_m": %FEC_M%,
  echo   "probe_count": %PROBE_COUNT%,
  echo   "probe_timeout_ms": %PROBE_TIMEOUT%,
  echo   "destinations": [!DEST_JSON!],
  echo   "resolvers": ["1.1.1.1"],
  echo   "verbose": %VERBOSE%,
  echo   "log_file": "client.log",
  echo   "json_logs": %JSON_LOGS%,
  echo   "metrics_file": "client.metrics.jsonl"
  echo }
) > client.config.json
endlocal
exit /b 0

:end
endlocal
exit /b 0

:resolve_python
set "PYTHON_LAUNCHER="
where py >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_LAUNCHER=py -3"
  exit /b 0
)
where python >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_LAUNCHER=python"
  exit /b 0
)
echo Python launcher not found. Install Python 3.14 or newer, then run this again.
pause
exit /b 1
