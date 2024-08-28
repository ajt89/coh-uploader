include .env

setup:
	- python -m pipenv install --dev

clean:
	- python -m pipenv --rm

format:
	- python -m pipenv run black --line-length 100 .

run-no-args:
	- python -m pipenv run python main.py

run-private-video-count:
	- python -m pipenv run python main.py --private-video-count ${PRIVATE_VIDEO_COUNT}
