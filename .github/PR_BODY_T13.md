# Fix T13: ignore comments when detecting `main()`

Follow-up to #3 (T13). The current entry-point check is a line-anchored `grep`
over raw source, so a `main` inside a multi-line block comment is still treated
as an entry point:

```c
/*
int main(void) { return 0; }
*/
int foo(void) { return 1; }
```

That makes `TYPE=auto` try to link an executable, and `TYPE=static`/`shared`
still excludes `foo.o` from the archive.

## Changes

The change is local to the entry-point section; the Makefile grows from 360 to
371 lines (288 code lines).

- Use a broad candidate grep (`MAIN_HINT`, no line anchor) to find files that
  mention `int/void main`.
- For candidates that contain `//`, `/*`, or `#if`, preprocess only that file
  with `$(CC)/$(CXX) -E -P $(CPPFLAGS)` and apply the original line-anchored
  check to the output.
- If preprocessing fails, fall back to the raw grep, so a real `main()` is not
  missed.
- Files without comments or `#if` keep the original raw check, avoiding a
  compiler invocation on every normal build.
- T13 now verifies:
  - `TYPE=auto` builds a library for a comment-only `main`;
  - `TYPE=exe` still fails when there is no real entry point;
  - `TYPE=static` includes the `foo` symbol and does not include `main`;
  - a real `main` after a block comment is still detected.

## Behavior

- `TYPE=auto` on a source whose only `main` is commented now builds a library
  instead of failing to link.
- A real `main` after a comment keeps working.
- This is a follow-up behavior change; normal executable projects are unchanged.

## Testing

| Environment | unit | projects |
|---|---|---|
| Windows 11 + MinGW gcc 16.2 + make 4.4.1 | 21 passed / 1 POSIX-only skip | 5/5 |
| Ubuntu 24.04 + gcc 13.3 | 22/22 | 5/5 |
| Ubuntu 24.04 + clang 18.1.3 | 22/22 | 5/5 |

GitHub Actions on the branch is green:
https://github.com/OnlyRicardo/MakefileTemplate/actions/runs/41029995019
(Ubuntu gcc, Ubuntu clang, macOS, Windows).

## Known limits

The detector remains deliberately moderate:

- a declaration (`int main(int, char**);`) can still be mistaken for a
  definition;
- a `main` in a string literal or an included header can still be misdetected;
- preprocessing failures fall back to raw grep, which may reproduce the old
  comment false positive rather than miss a real entry point.
