lint:
	poetry run flake8 . --extend-ignore=D,E501,W601 --extend-exclude=docs/ --statistics --count

test:
	poetry run python ./runtests.py
