
clean:
	find . \( -name './simplesurvey/*.pyc' -o -name './simplesurvey/*.pyo' -o -name './simplesurvey/*~' \) -print -delete
	find . -name './simplesurvey/__pycache__' -exec rm -rvf '{}' +
