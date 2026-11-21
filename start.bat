@echo off
REM Read the PDF files in input\ and write the JSON files to output\.
REM Add --gui to start the web interface.
cd /d "%~dp0"
python main.py %*
