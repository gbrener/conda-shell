"%PYTHON%" setup.py --quiet install --single-version-externally-managed --record=record.txt
if errorlevel 1 exit 1
