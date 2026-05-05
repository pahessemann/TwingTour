PYTHON ?= C:/Users/paulh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe
NODE ?= C:/Users/paulh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe

.PHONY: help run test check check-js map logs clean

help:
	@echo EuroTwingo targets:
	@echo   make run       - start the local server on http://127.0.0.1:8010
	@echo   make test      - run backend unit tests
	@echo   make check-js  - syntax-check frontend and tooling JavaScript
	@echo   make check     - run all checks
	@echo   make map       - regenerate the pixel Europe country layer
	@echo   make logs      - print local server logs
	@echo   make clean     - remove Python caches and local server logs

run:
	"$(PYTHON)" app.py

test:
	"$(PYTHON)" -m unittest discover -s tests

check-js:
	"$(NODE)" --check frontend/components/MapView.js
	"$(NODE)" --check frontend/assets/europeCountries.js
	"$(NODE)" --check tools/generate_europe_pixel_map.js

check: check-js test

map:
	"$(NODE)" tools/generate_europe_pixel_map.js

logs:
	@"$(PYTHON)" -c "from pathlib import Path; [print(f'--- {p.name} ---\n{p.read_text(errors=\"replace\")[-4000:]}') for p in map(Path, ['server.out.log', 'server.err.log']) if p.exists()]"

clean:
	"$(PYTHON)" -c "from pathlib import Path; import shutil; [shutil.rmtree(p, ignore_errors=True) for p in Path('.').rglob('__pycache__')]; [p.unlink(missing_ok=True) for p in Path('.').rglob('*.pyc')]; [Path(name).unlink(missing_ok=True) for name in ['server.out.log', 'server.err.log']]"
