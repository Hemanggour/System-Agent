@echo off

echo ================================
echo Running isort (import sorting)...
echo ================================
isort . --skip .venv

echo ================================
echo Running black (code formatter)...
echo ================================
black . --exclude="(.venv)"

echo ================================
echo Running flake8 (style checker)...
echo ================================
flake8 . --exclude=.venv,docs/ --max-line-length=100 --ignore=E203,W503

echo ================================
echo All checks completed!