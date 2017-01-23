python_files := (find . -path '*/.*' -prune -o -name '*.py' -print0)

clean:
	find . \( -name '*.pyc' -o -name '*.pyo' -o -name '*~' \) -print -delete
	find . -name '__pycache__' -exec rm -rvf '{}' +

test: autopep8 lint clean
	py.test --durations=10 --random tests -v -s -x

autopep8:
	@echo 'Auto Formatting...'
	@$(python_files) | xargs -0 autopep8 --jobs 0 --in-place --aggressive

lint:
	@echo 'Linting...'
	@$(python_files) | xargs -0 -n200 -P16 flake8

autolint: autopep8 lint
