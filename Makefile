init:
	pip install -r requirements.txt

lint:
	flake8

test:
	PYTHONWARNINGS=all ./runtests.py

coverage:
	coverage run --source=multi_import runtests.py && coverage report
