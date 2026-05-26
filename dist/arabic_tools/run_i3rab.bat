@echo off
REM run_i3rab.bat — تشغيل محرّك الإعراب على Windows
REM
REM الاستخدام:
REM   run_i3rab.bat "إِنَّ اللَّهَ غَفُورٌ رَحِيمٌ"
REM   run_i3rab.bat --csv my_sentences.csv --csv-out result.csv

cd /d "%~dp0"
python i3rab.py %*
pause
