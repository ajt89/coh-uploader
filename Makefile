include .env

setup:
	- python -m pipenv install --dev

clean:
	- python -m pipenv --rm

format:
	- python -m pipenv run black --line-length 100 .

run:
	- python -m pipenv run python main.py
