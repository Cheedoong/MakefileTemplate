# Project-level tests

These are realistic mini-projects, not unit fixtures. Each one is copied to a
temp directory, gets the root `Makefile`, is built and exercised.

Run all:

```bash
python3 tests/run_projects.py
```

The projects intentionally do **not** contain a `Makefile`; the runner copies
the template under test. Nothing here is installed or left in the repository.

| Project | Layout | What it catches |
|---|---|---|
| `cli-app` | C, `include/app/`, `src/core/`, `libs/text/` | nested includes, multiple modules, local library, incremental rebuild, `-j8`, clean |
| `multi-tool` | C++, `src/common/`, `tools/alpha.cpp`, `tools/beta.cpp` | multiple entry points, shared common objects compiled once, `make run` |
| `static-lib-and-app` | C library project + consumer app | `TYPE=static`, symbols in `libmath.a`, `libs/<name>/{include,lib}` consumption |
| `c-lib-cpp-app` | C library + C++ app (`extern "C"`) | mixed-language boundary, `gcc` for the library, `g++` for the app/link |

Expected result:

```
summary: 4 passed, 0 failed
```

On Windows the executables get `.exe`; the runner handles that automatically.
