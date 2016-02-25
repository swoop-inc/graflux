PYTHON=`which python`
NAME=`python setup.py --name`

all: test source deb

init:
	pip install -r requirements.txt --use-mirrors

dist: source deb

source:
	$(PYTHON) setup.py sdist

deb:
	$(PYTHON) setup.py --command-packages=stdeb.command bdist_deb

test:
	python -m unittest discover -s test -p "*_test.py"

clean:
	$(PYTHON) setup.py clean
	rm -rf build/ MANIFEST dist build graflux.egg-info deb_dist
	find . -name '*.pyc' -delete

.PHONY: all test clean