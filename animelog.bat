@echo off
SETLOCAL
set player="C:\Program Files\Combined Community Codec Pack\MPC\mpc-hc.exe"
:: Enter your path to your player here
set batchloc=%~dp0
set str1=%1
set is_a_movie=True
if [%str1%] == [%str1:.=%] set is_a_movie=False
if [%str1%] == [] set is_a_movie=False
if %is_a_movie%==True (
	start "" /max /high %player%  %* 
	REM the string was a filename, thus start movieplayer 
	if not [%player:mpc-hc=%]==[%player%] wmic process where name="mpc-hc.exe" setpriority 128 > nul
	REM set mpc-hc to max-priority because of some child-spawning behavior (only if the mpc-hc is the player)
	REM >nul supresses the wmic output to shell
	)
cd %batchloc%
python animelog.py %*
:: log the series if it was a filename, or perform the requested action if it was not
ENDLOCAL