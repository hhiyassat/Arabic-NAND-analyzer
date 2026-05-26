@echo off
REM run_morph.bat — تشغيل المحلّل الصرفي على Windows
REM
REM الاستخدام:
REM   run_morph.bat "كَتَبَ"
REM   run_morph.bat --file my_text.txt
REM   run_morph.bat --csv words.csv --csv-out result.csv

cd /d "%~dp0"
python morph.py %*
pause
