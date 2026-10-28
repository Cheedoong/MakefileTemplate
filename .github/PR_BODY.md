# Modernize the template: reliable dependencies, Windows fixes, library targets

## Summary

This PR rewrites `Makefile` as v0.8 while keeping the original idea: **one file,
copy it into a project, run `make`**. It fixes several build-breaking bugs,
completes the long-standing `[to-do]` (static/shared libraries), and adds
multi-entry-point support. `tags`/`ctags`, the old variable names and the
OS-specific flag hooks are preserved.

The template is still a single `Makefile` (360 lines, 280 of them code).
`tests/` and `.github/` are maintenance infrastructure, not part of what users copy.

## Problems reproduced before the change

| # | Problem | Evidence |
|---|---|---|
| 1 | A failed dependency generation leaves a truncated `.d`, after which **every** target fails, including `make distclean` | `.main.d` contains only `./`; next run: `main.d:1: *** missing separator. Stop.` |
| 2 | Windows: sources are scanned twice because the filesystem is case-insensitive | `mingw32-make` reports `SOURCES: ./main.c ./main.c` -> `multiple definition of 'main'` |
| 3 | Windows: the target lacks `.exe`, so make relinks on every run | three consecutive `make` runs all execute the link command |
| 4 | MinGW: the default `CC=cc` does not exist | `cc: command not found` |
| 5 | `mingw32-make` matches `%.o: %.C` for a `*.c` file on Windows | `bar.c` is compiled as C++ |
| 6 | Empty `SOURCES`: `grep -l` reads stdin and hangs | 0.25 s vs 6.25 s with an open stdin |
| 7 | Shell preflight using `echo` passes under `cmd.exe`, then `rm` fails | `check=[__ok__]`, then `CreateProcess(NULL, rm ...) failed` |
| 8 | A parse-time collision error also blocks `make clean` / `make help` | `make clean` aborts with the collision message |
| 9 | README documents `EXTRA_LIBS`, which does not exist (issue #1) | variable absent from 0.7 |
| 10 | Header in a subdirectory (`inc/util.h`) needs a manual `-I` | `main.c:1:10: fatal error: util.h: No such file or directory` |

## Changes

### Dependencies and sources

- `-MMD -MP -MF` replaces the hand-written `.%.d` rules. A failed compile can no
  longer leave a partial `.d`.
- Pure `$(wildcard)` recursion replaces `find`; the PowerShell `find.exe`
  conflict from #2 disappears.
- Results are normalised and deduplicated (`$(sort)`), so `.c`/`.C` on Windows
  cannot produce duplicate objects.
- Symbolic-linked directories are not followed (same as `find -type d`); files
  are still picked up. Exceeding the depth limit (8) prints a warning instead of
  silently dropping files.
- Every directory containing a discovered header is appended to `CPPFLAGS`
  (`$(sort $(dir $(HEADERS)))`), so `main.c` + `inc/util.h` works without a
  manual `-I`. `override` keeps these paths when `CPPFLAGS` is set on the
  command line; explicit user paths still come first.

### Platform and compiler detection

- Explicit `Windows_NT` / `Darwin` / `Linux` detection with `.exe`, `.dll`,
  `.dylib` and `.so` suffixes.
- Windows shell preflight probes `sh`, not `echo`, and sets `SHELL` only inside
  the Windows branch.
- `CC`/`CXX`/`AR` are defaulted only when make's built-in default is in effect,
  so `CC=clang`, cross-compilers and `CC=$(CXX)` all work.

### Libraries and entry points

- `TYPE=auto|exe|static|shared`; `auto` builds an executable when a `main()`
  exists and a shared library otherwise.
- Static (`ar rcs`) and shared (`-shared`, `-fPIC` on Unix) libraries.
  On Windows, shared libraries export symbols and generate
  `lib<PROGRAM>.dll.a`.
- One executable per `main()`; common objects are compiled once. Colliding
  stems use the full relative path (`a/x/main.cpp` -> `a_x_main`); the root
  file has no prefix. Residual name collisions are rejected only for
  `TYPE=exe`; `TYPE=static`/`shared` can still build the library.
- `libs/<name>/{include,lib}` is added to `-I`/`-L` automatically; consumers
  only write `EXTRA_LIBS=-l<name>`.

### Developer experience

- `make help`, fixed `make show` (prints `PLATFORM`, `SHELL`, `TYPE`,
  `MAIN_SRCS`, `EXES`, ...), `make run`, `V=1`, `NODEP=yes`.
- `EXE_LDFLAGS` is executable-only; `-s` is opt-in instead of stripping by
  default.
- `EXTRA_LIBS` is accepted as an alias for the old README.
- `make clean` removes objects, products and `.d`; `make distclean` additionally
  removes `TAGS`/`tags`.
- `tags`/`ctags` and the original OS-specific flag variables are preserved.

## Compatibility and behavior changes

- `PROGRAM` defaults to the directory name instead of `zzz_pear_test`.
- `TYPE` is new and defaults to `auto`; a project without `main()` now builds a
  library instead of failing to link.
- Dependency files are `src/foo.d` instead of `src/.foo.d`.
- Windows products carry `.exe` (and no longer relink every time).
- With multiple mains, products are named after the entry-point files.
- Executables are no longer stripped by default; use `make EXE_LDFLAGS=-s` for
  a release build. Libraries always keep their symbols.
- The noisy `-v` was removed from the macOS link flags.
- Header directories are auto-added to `-I`; explicit `CPPFLAGS`/`INCLUDE`
  paths keep precedence. A project header named like a system header can shadow
  it.
- `make clean` now also removes `.d` files (previously `distclean` did).
- `TYPE=static`/`shared` is no longer blocked by a residual executable-name
  collision.
- Windows needs a POSIX shell (Git for Windows or MSYS2) on `PATH`.

All original variables are still accepted:
`PROGRAM`, `SRCDIRS`, `INCLUDE`, `EXTRA_CFLAGS`, `EXTRA_LDFLAGS`, `CFLAGS`,
`CXXFLAGS`, `CPPFLAGS`, `LDFLAGS`, `SRCEXTS`, `HDREXTS`, `ETAGS`, `CTAGS`,
the `*_MACOS`/`*_LINUX`/`*_WINDOWS` hooks, `RM`, `NODEP` and `CC=$(CXX)`.

## Testing

The PR adds a regression suite; it only uses Python 3 and the compiler.

| Environment | Feature matrix | Project scenarios |
|---|---|---|
| Windows 11 + MinGW-w64 gcc 16.2 + GNU make 4.4.1 | 21 passed, 1 skipped (POSIX-only) | 5/5 |
| Ubuntu 24.04 + gcc 13.3 + make 4.3 | 22/22 | 5/5 |
| Ubuntu 24.04 + clang 18.1.3 | 22/22 | 5/5 |
| GitHub Actions: Ubuntu gcc, Ubuntu clang, macOS, Windows/MSYS2 | green | green |

Additional checks:

- 200 source files, `make -j16`: first build 2.4 s, no-op 50 ms, header touch 2.6 s.
- AddressSanitizer flags passed through `CFLAGS`/`EXTRA_LDFLAGS` (heap-buffer-overflow caught).
- Real project: `cJSON` v1.7.18 built as `libcjson.a` and consumed by an app (`42`).

The suite covers C/C++, incremental rebuilds, deleted headers, static/shared
libraries, `TYPE=auto`, multiple mains, collision naming, `libs/`, empty trees,
symlink loops, depth limits, `MAIN_SRCS`, `CC=$(CXX)`, `EXE_LDFLAGS=-s`,
auto header `-I`, `clean`/`distclean` and `help`/`show`/`V=1`.

## Related

- Closes #1 (local library): `libs/<name>/{include,lib}` plus a working
  `EXTRA_LIBS`.
- Supersedes #2 (`find` path): `find` is no longer used at all, so the
  PowerShell/System32 conflict cannot occur. Thanks to @omer-musa-battal for
  diagnosing it; the diagnostic intent is now covered by `make show`.

## Deliberate non-goals / follow-ups

This stays a small, predictable template rather than a build system:

- `compile_commands.json` (clangd), `make install`, debug/release presets,
  ccache, package-manager integration, out-of-tree build directories,
  paths with spaces.
- Multi-architecture matrices and generated sources.

## Checklist

- [x] Single-file drop-in usage preserved
- [x] Old variables and `tags`/`ctags` preserved
- [x] Tests on Windows, Linux (gcc + clang) and macOS
- [x] CI green on all four jobs
- [x] README rewritten, including limitations and migration notes
- [x] No unrelated files changed
