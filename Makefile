.PHONY: clean install test

PREFIX ?= /usr/local
EXEC_DIR = $(PREFIX)/bin

clean:
	-rm -r ve/
	-rm ._bootstrap.etag
	-rm bootstrap.cfg
	-rm pre-reqs.txt
	-rm pre-requirements.txt
	-rm requirements.txt
	-rm requirements.py_*
	-rm requirements.pypy_*

install:
	install -m 0755 bootstrap.py $(EXEC_DIR)/bootstrap.py

test:
	./tests.py

uninstall:
	-rm -f $(EXEC_DIR)/bootstrap.py
