# Fix T13: ignore comments when detecting `main()`

Follow-up to #3 / T13.

The current entry-point check is a line-anchored `grep` over raw source, so a
`main` inside a multi-line block comment is still treated as an entry point:

```c
/*
int main(void) { return 0; }
*/
int foo(void) { return 1; }
```

That makes `TYPE=auto` try to link an executable, and `TYPE=static`/`shared`
still excludes `foo.o` from the archive.

## Method

The fix does **not** try to parse C comments with a regex. It delegates comment
removal to the compiler, which already implements the C/C++ lexical rules, and
keeps the Makefile logic small:

1. **Broad candidate scan** — `MAIN_HINT` matches `int/void main` anywhere in
   the line (no `^`), so a real entry following a comment is not missed:
   ```make
   MAIN_HINT := (int|void)[[:space:]]+main[[:space:]]*\(
   ```
2. **Only ambiguous files are preprocessed** — `MAIN_MAYBE` selects candidates
   containing `//`, `/*`, or a preprocessor conditional:
   ```make
   MAIN_MAYBE := ... grep -lE '/\*|//|^[[:space:]]*[[:punct:]]if' $(MAIN_CAND)
   ```
   Files without comments/`#if` keep the original raw check, so a normal build
   does not invoke the compiler a second time.
3. **Preprocess, then apply the strict check** — for ambiguous candidates:
   ```make
   $(CC or CXX) -E -P $(CPPFLAGS) file
   ```
   `-E -P` removes comments and resolves `#if` blocks. The final match still
   uses the strict line-anchored `MAIN_RE`.
4. **Fallback without missing a real main** — if preprocessing fails, `cat`
   feeds the original source to the same final grep. This may preserve the old
   comment false positive, but never silently drops a real entry point.
5. **Empty-candidate guard** — `grep -l` is not called with an empty file list,
   avoiding a stdin read/hang (the old A1 class of failure).

The Makefile grows from 360 to 371 lines (288 code lines); the change is local
to the entry-point section.

## Behavior

- A source whose only `main` is in `//`, `/* ... */`, or `#if 0` is now treated
  as a library: `TYPE=auto` builds a shared library instead of failing to link.
- `TYPE=exe` still fails when there is no real entry point.
- `TYPE=static` includes the real `foo` object and does not contain `main`.
- A real `main` after a comment (`/* note */ int main(...)`) is still detected.
- Normal executable projects are unchanged.

T13 now verifies all of the above, including the `nm` symbol check on the static
library and the “main after a block comment” case.

## Testing

| Environment | unit | projects |
|---|---|---|
| Windows 11 + MinGW gcc 16.2 + make 4.4.1 | 21 passed / 1 POSIX-only skip | 5/5 |
| Ubuntu 24.04 + gcc 13.3 | 22/22 | 5/5 |
| Ubuntu 24.04 + clang 18.1.3 | 22/22 | 5/5 |
| Ubuntu + GNU make 3.81 (macOS parser proxy) | 22/22 | 5/5 |

GitHub Actions on the branch is green for Ubuntu gcc, Ubuntu clang, macOS and
Windows:

https://github.com/OnlyRicardo/MakefileTemplate/actions/runs/41030227045

## Compatibility

- GNU make 3.81 compatible: the shell probe avoids nested `if` constructs and
  uses no literal `#` in the Makefile regex (macOS make treats `#` as a comment).
- No new tools or dependencies: `-E -P` uses the compiler already required by
  the template.
- Preprocessing is limited to comment/`#if` candidates; the empty list guard
  prevents the old `grep` stdin hang.

## Known limits

The detector remains deliberately moderate:

- a declaration (`int main(int, char**);`) can still be mistaken for a
  definition;
- a `main` in a string literal or an included header can still be misdetected;
- preprocessing failures fall back to raw grep, which may reproduce the old
  comment false positive rather than miss a real entry point.
