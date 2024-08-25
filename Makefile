include .env

setup:
	- python -m pipenv install --dev

clean:
	- python -m pipenv --rm

format:
	- python -m pipenv run isort .;\
	python -m pipenv run black .
