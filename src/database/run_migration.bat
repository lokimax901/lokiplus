@echo off
echo Starting migration to Supabase...

REM Activate virtual environment
call ..\..\.venv\Scripts\activate.bat

REM Run migration
echo Running migration script...
python migrate_to_supabase.py

REM Run verification
echo Running verification script...
python verify_migration.py

REM Deactivate virtual environment
deactivate

echo Migration process completed.
pause 