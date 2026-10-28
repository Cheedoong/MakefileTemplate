# Regression tests

`run_tests.py` builds small throw-away projects in a temp directory and checks the
root `Makefile`. It needs only Python 3.8+ and a C/C++ toolchain.

## Requirements

| Platform | Requirements |
|---|---|
| Linux | `make`, `gcc`/`g++` (or clang), `ar`, `nm`, Python 3 |
| macOS | Xcode command line tools, `make`, Python 3 |
| Windows | GNU make, MinGW-w64 gcc, **Git Bash or MSYS2** on `PATH` (for `sh`, `rm`, `grep`), Python 3 |

The Makefile itself only requires a POSIX shell on Windows; the tests use the same
assumption.

## Run

### Linux / macOS

```bash
python3 tests/run_tests.py
```

Use clang instead of gcc:

```bash
CC=clang CXX=clang++ python3 tests/run_tests.py
```

### Windows (PowerShell)

```powershell
# Add Git's POSIX tools if they are not already on PATH
$env:PATH = "D:\Git\usr\bin;$env:PATH"
python tests\run_tests.py
```

If `make` is only available as `mingw32-make`:

```powershell
$env:MAKE = "mingw32-make"
python tests\run_tests.py
```

Environment overrides: `MAKE`, `CC`, `CXX`, `AR`.

## Ubuntu manual verification

```bash
sudo apt update
sudo apt install -y build-essential python3 make

git clone -b feat/v0.8-portable https://github.com/OnlyRicardo/MakefileTemplate.git
cd MakefileTemplate
python3 tests/run_tests.py

# optional: repeat with clang
CC=clang CXX=clang++ python3 tests/run_tests.py
```

The script prints `PASS` / `FAIL` / `SKIP` per case and exits non-zero on failure.
`SKIP` is expected for platform-specific cases (Windows shell preflight, POSIX symlink).

### Manual checklist (things worth eyeballing)

- [ ] Empty directory: `timeout 10 make` returns promptly, prints
      `No source files found` and `Nothing to be done`.
- [ ] Copy only `Makefile` into a new directory with one `main.c`; `make` builds and runs.
- [ ] Touch a header: only objects that include it are recompiled.
- [ ] Delete a header: `make` fails with a readable compiler error; `make clean` still works.
- [ ] `make TYPE=static`: `lib<PROGRAM>.a` exists and `nm` shows the symbol.
- [ ] `make TYPE=shared`: `lib<PROGRAM>.so` (or `.dylib`) exists; `nm -D` / `nm -g` shows the symbol.
- [ ] `make -n tags` parses (whether `etags` is installed does not matter).
- [ ] `make help` and `make show` print the expected information.
- [ ] `make EXE_LDFLAGS=-s` produces a smaller executable (release strip).
- [ ] Collision: `main.cpp`, `sub/main.cpp`, `a/x/main.cpp`, `b/x/main.cpp`
      produce `main`, `sub_main`, `a_x_main`, `b_x_main`; `make clean` works.
- [ ] Symlink loop (Linux/macOS): `ln -s .. loop` does not duplicate sources.
- [ ] 9-level directory tree prints a `depth limit` warning instead of silently
      dropping files.

## What each case covers

| Case | Coverage |
|---|---|
| T01 | C executable, multi-directory, incremental no-op, duplicate-source guard |
| T02 | C++ multi-directory; header change recompiles only affected objects |
| T03 | Compile failure then fix without deleting `.d` |
| T04 | Deleted header; `clean` remains usable |
| T05 | Static library and symbols |
| T06 | Shared library, symbols, Windows export table + import library |
| T07 | `TYPE=auto` chooses executable vs library |
| T08 | Mixed C/C++; `.c` vs `.C` compiler selection |
| T09 | `make -j8` |
| T10 | `clean` vs `distclean` |
| T11 | Multiple `main()`; common objects compiled once |
| T12 | Single-main naming (`PROGRAM`) |
| T13 | Commented-out `main` does not silently produce a wrong product |
| T14 | `help` / `show` / `V=1` / `objs` / `tags` dry-run |
| T15 | `libs/<name>/{include,lib}` auto-discovery |
| T16 | Empty project does not hang; Windows missing-shell preflight |
| T17 | Symbolic-link loop (POSIX only) |
| T18 | Collision renaming + residual-collision error |
| T19 | Depth-limit warning |
