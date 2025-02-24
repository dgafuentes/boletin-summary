@echo off
cd "C:\boletin-summary"

call .venv\Scripts\activate

echo =========================== >> task_review.txt
echo Fecha y hora: %date% %time% >> task_review.txt
echo =========================== >> task_review.txt

python boletin_summary.py >> task_review.txt 2>&1