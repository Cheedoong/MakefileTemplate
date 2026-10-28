# MakefileTemplate

A generic, single-file Makefile template for C/C++ projects (v0.8).

Copy `Makefile` into your project and run `make`. Nothing else is required:
no CMake, no package manager, no generated files.

```sh
cp Makefile /path/to/your/project/
cd /path/to/your/project
make
```

## Features

* Automatically scans sub-directories for C/C++ sources, or use `SRCDIRS`;
* Correct incremental builds: header dependencies via `-MMD -MP`, no stale `.d` files;
* C, C++ and mixed projects; all common extensions are supported;
* Executables, static libraries and shared libraries (`TYPE=auto|exe|static|shared`);
* Multiple `main()` files become multiple executables, with common objects built once;
* `libs/<name>/{include,lib}` is discovered automatically (no manual `-I`/`-L`);
* Linux, macOS and Windows (Windows needs a POSIX shell, see below);
* Optional cross-compiling and toolchain override;
* `make help`, `make show`, `V=1`, `NODEP=yes`, `make run`;
* Editor tags (`tags` / `ctags`) are kept from the original template.

## Quick start

```sh
# executable (one main)
make

# library project (no main)
make TYPE=static        # lib<PROGRAM>.a
make TYPE=shared        # lib<PROGRAM>.so / .dylib / <PROGRAM>.dll

# explicit entry points (skips the automatic scan)
make MAIN_SRCS="src/tool.cpp"

# show what will be built
make show

# full command lines
make V=1
```

## Usage

1. Copy `Makefile` to the root of your project.
2. Edit only the "User configuration" section if needed. All variables can also
   be overridden on the command line.
3. Run `make`.

The file contains in-place examples for compiling flags, libraries, include
paths, cross-compiling and `CC=$(CXX)`.

## Variables

| Variable | Default | Meaning |
|---|---|---|
| `PROGRAM` | current directory name | Product base name (without extension) |
| `TYPE` | `auto` | `auto`, `exe`, `static` or `shared` |
| `MAIN_SRCS` | auto-detected | Explicit entry-point sources; skips the scan |
| `SRCDIRS` | empty (scan `.`) | Source directories; scanning is recursive |
| `INCLUDE` | empty | Extra `-I` directories |
| `EXTRA_CFLAGS` | `-fdata-sections -ffunction-sections` | Extra compiler flags |
| `EXTRA_LDFLAGS` | empty | Extra linker flags |
| `EXTRA_LIBS` | empty | Compatibility alias for link libraries, e.g. `-lm` |
| `CPPFLAGS` | empty | Preprocessor flags (the template adds `-I` paths) |
| `CFLAGS` / `CXXFLAGS` | `-O3` | Compiler flags |
| `LDFLAGS` | empty | Linker flags |
| `EXE_LDFLAGS` | empty | Executable-only link flags; `-s` strips a release build |
| `CROSS_COMPILE` | empty | Toolchain prefix, e.g. `arm-none-eabi-` |
| `NODEP` | empty | `NODEP=yes` disables dependency generation |
| `V` | empty | `V=1` prints full commands |
| `SRCEXTS` / `HDREXTS` | common C/C++ list | File extensions to scan |
| `ETAGS` / `CTAGS` | `etags` / `ctags` | Tag tools |
| `*_MACOS` / `*_LINUX` / `*_WINDOWS` | see file | OS-specific flag hooks (kept from 0.7) |

## Targets

| Target | Action |
|---|---|
| `make` / `all` | Build the executable(s) or library |
| `objs` | Compile only, do not link |
| `run` | Run the executable (lists choices when there are several) |
| `tags` / `ctags` | Generate editor tags (`etags` / `ctags` required) |
| `clean` | Remove objects and products |
| `distclean` | `clean` plus dependency files and tags |
| `show` | Print effective variables |
| `help` | Print usage |

## Recipes

### Executable

```sh
make                              # one main -> <PROGRAM>
make PROGRAM=myapp                # rename the product
make -j8                          # parallel build
```

### Static / shared library

```sh
make TYPE=static                  # lib<PROGRAM>.a
make TYPE=shared                  # lib<PROGRAM>.so / .dylib / <PROGRAM>.dll
```

A shared library gets `-fPIC` on Linux/macOS. On Windows the template also
exports symbols (`--export-all-symbols`) and generates `lib<PROGRAM>.dll.a`
for consumers.

> Switching from `static` to `shared` on Linux/macOS needs `make clean`
> (the object files differ in PIC-ness).

### Multiple executables

Each source containing a `main()` becomes an executable named after the file:

```text
alpha.cpp              -> alpha
tools/beta.cpp         -> beta
```

All non-entry objects are shared by every executable and compiled once.
If two mains have the same stem (`a/x/main.cpp`, `b/x/main.cpp`), the full
relative path is used (`a_x_main`, `b_x_main`). Root files get no prefix
(`main.cpp` -> `main`).

```sh
make
make run               # lists the executables
./alpha
```

### Local libraries

```text
libs/
└── math/
    ├── include/math.h
    └── lib/libmath.a        # or libmath.so / math.dll + libmath.dll.a
```

`libs/*/include` is added to `-I` and `libs/*/lib` to `-L` automatically.
You only name the library:

```sh
make EXTRA_LIBS=-lmath
```

> A library still needs its own name (`-lmath`). The template does not guess
> library names from directory names.

### Debug / release flags

```sh
make CFLAGS="-O0 -g" CXXFLAGS="-O0 -g"     # debug
make EXE_LDFLAGS=-s                        # stripped release executable
```

The default is `-O3` and no strip, so symbols are available for debugging.

### Cross-compiling

```sh
make CROSS_COMPILE=arm-none-eabi-
```

or override `CC` / `CXX` directly.

### Windows

The template needs a POSIX shell for `sh`, `rm`, `grep` and friends:

* Install **Git for Windows** or **MSYS2**;
* Put its `usr\bin` (Git) or `usr\bin` + `ucrt64\bin` (MSYS2) on `PATH`;
* Use GNU `make` (Git Bash/MSYS2 both provide it).

PowerShell example:

```powershell
$env:PATH = "C:\Program Files\Git\usr\bin;$env:PATH"
make
```

`mingw32-make` also works. The template no longer calls `find`, so the
PowerShell `find.exe` conflict from the original version is gone.

### Clang / other compilers

```sh
make CC=clang CXX=clang++ AR=llvm-ar
```

`CC` and `CXX` are only defaulted to `gcc`/`g++` when make's built-in default
is still in effect, so environment/command-line overrides always win.

### Dependencies

`.d` files are generated next to the objects by the compiler:

* changing a header rebuilds exactly the objects that include it;
* deleting a header gives a normal compiler error, and `make clean` still works;
* `NODEP=yes` disables both generation and inclusion.

`clean` removes objects/products; `distclean` also removes `.d` files and tags.

## How it works (short version)

1. `SOURCES` are discovered with pure make functions (`wildcard`), deduplicated
   and normalised; symbol-linked directories are not followed.
2. One explicit rule is generated per source, choosing `CC` or `CXX` from the
   real file suffix. This also avoids `mingw32-make` matching `%.o: %.C` for
   a `*.c` file on case-insensitive filesystems.
3. `TYPE=auto` uses a line-anchored `grep` for `int main`/`void main`.
4. Static libraries use `ar rcs`; shared libraries use `-shared` (and the
   Windows export/import flags).
5. Entry points are linked with the common objects; a pure-C project links with
   `CC`, anything containing C++ links with `CXX`.

## Known limitations

* `main()` detection is a heuristic. A `main` inside a multi-line block comment,
  an `#if 0` block, a declaration or a string may be misdetected. Set `TYPE=`
  or `MAIN_SRCS=` explicitly when that happens. A false positive fails loudly
  at link time; it never silently produces the wrong product type.
* All non-entry objects are shared by all executables. Keep common code in
  files without `main()`. Two independent programs with same-named symbols
  should be separate projects.
* Symbolic-linked **directories** are not followed (same as the original
  `find -type d`); symbolic-linked **files** work normally. Do not create
  symlink loops on Windows, where `realpath` may not resolve NTFS links.
* Paths containing spaces are not supported (same as the original template).
* No out-of-tree build directory; objects live next to sources.
* No `compile_commands.json`, `make install`, debug/release presets, ccache or
  package-manager integration. Those are deliberate follow-ups; this template
  aims at being small and predictable, not at replacing CMake.

## Migrating from 0.7

| 0.7 | 0.8 |
|---|---|
| `PROGRAM = zzz_pear_test` | defaults to the directory name |
| no library support | `TYPE=auto|exe|static|shared` |
| `src/.foo.d` | `src/foo.d` |
| `PROGRAM` target on Windows | `<PROGRAM>.exe` (no more relinking every run) |
| `-Wl,--strip-all` on Linux links | strip only when `EXE_LDFLAGS=-s` |
| `-v` in macOS link flags | removed (noisy) |
| `EXTRA_LIBS` documented but missing | supported as an alias |
| single executable only | one executable per `main()` |
| `tags` / `ctags` | still available |

`make NODEP=yes`, `make objs`, `make clean`, `make distclean`, `make help`,
`make show`, `SRCDIRS`, `INCLUDE`, `EXTRA_CFLAGS`, `EXTRA_LDFLAGS`,
`CFLAGS`, `CXXFLAGS`, `CPPFLAGS`, `LDFLAGS`, `SRCEXTS`, `HDREXTS`,
`ETAGS`, `CTAGS`, OS-specific flag variables and `CC=$(CXX)` are preserved.

## Tests / CI

The repository ships a regression suite; the template itself is only `Makefile`.

```sh
python3 tests/run_tests.py       # feature matrix (T01-T22)
python3 tests/run_projects.py    # realistic projects (P1-P5)
```

CI runs Ubuntu (gcc and clang), macOS and Windows (MSYS2) on every push.
See `tests/README.md` for details and a manual checklist.

## Users

+ [Pear](https://pear.hk)
+ [HKUST](http://www.ust.hk)

## Reference & Thanks to

+ https://sourceforge.net/projects/gcmakefile/
+ https://github.com/mbcrawfo/GenericMakefile
+ http://blog.csdn.net/kevin1078/article/details/7492619
+ http://www.digitalpeer.com/blog/example

## License

The `Makefile` is distributed under the GPL. As noted in its header, the GPL
applies only to the Makefile itself; you can use it in non-GPL projects.
