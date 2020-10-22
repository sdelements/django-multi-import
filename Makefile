init:
	pip install -r requirements.txt

lint:
	flake8 --max-line-length 88 --extend-ignore=D

test:
	./runtests.py

coverage:
	coverage run --source=multi_import runtests.py && coverage report
