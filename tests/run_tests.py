#!/usr/bin/env python3
"""Cross-platform regression suite for the Makefile template.

Usage:
    python tests/run_tests.py
    MAKE=mingw32-make python tests/run_tests.py
    CC=clang CXX=clang++ python tests/run_tests.py

Only Python 3.8+ standard library is required.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"
EXE = ".exe" if IS_WIN else ""
SHARED_EXT = ".dll" if IS_WIN else (".dylib" if IS_MAC else ".so")


class SkipTest(Exception):
    pass


def _prepend_paths(env, paths):
    good = []
    for item in paths:
        if item and Path(item).exists():
            good.append(str(item))
    env["PATH"] = os.pathsep.join(good + [env.get("PATH", "")])


def _setup_path():
    if not IS_WIN:
        return
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    extra = [Path(r"D:\Git\usr\bin")]
    for pattern in (
        "ezwinports.make_*/bin",
        "BrechtSanders.WinLibs.POSIX.UCRT_*/mingw64/bin",
        "mingw64/bin",
    ):
        extra.extend(local.glob("Microsoft/WinGet/Packages/" + pattern))
    extra.extend([Path(r"C:\msys64\ucrt64\bin"), Path(r"C:\msys64\mingw64\bin")])
    _prepend_paths(os.environ, extra)


_setup_path()
ENV = os.environ.copy()
MAKE = os.environ.get("MAKE") or shutil.which("make") or shutil.which("mingw32-make") or "make"
CC = os.environ.get("CC") or "gcc"
CXX = os.environ.get("CXX") or "g++"
AR = os.environ.get("AR") or "ar"


def run(cmd, cwd, env=None, timeout=180):
    return subprocess.run(
        [str(x) for x in cmd],
        cwd=str(cwd),
        env=env or ENV,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=timeout,
    )


def make(project, *args, env=None, timeout=180):
    return run([MAKE, *args], project, env=env, timeout=timeout)


def ok(proc, label=""):
    if proc.returncode != 0:
        raise AssertionError(
            f"{label or 'command'} failed (exit {proc.returncode})\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
        )


def check(cond, message):
    if not cond:
        raise AssertionError(message)


def both(proc):
    return (proc.stdout or "") + "\n" + (proc.stderr or "")


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def prepare(fixture=None):
    d = Path(tempfile.mkdtemp(prefix="mftest-"))
    if fixture:
        src = FIXTURES / fixture
        if src.exists():
            shutil.copytree(src, d, dirs_exist_ok=True)
    shutil.copy2(ROOT / "Makefile", d / "Makefile")
    return d


def cleanup(d):
    shutil.rmtree(d, ignore_errors=True)


def exe_path(d, program="demo"):
    return d / (program + EXE)


def shared_path(d, program="demo"):
    if IS_WIN:
        return d / (program + SHARED_EXT)
    return d / (("lib" if not IS_MAC else "lib") + program + SHARED_EXT)


def program_env():
    env = ENV.copy()
    env.update({"CC": CC, "CXX": CXX, "AR": AR})
    return env


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def t01_c_exe():
    d = prepare("c-exe")
    try:
        args = ("PROGRAM=demo", "SRCDIRS=. src", "CPPFLAGS=-I./inc")
        p = make(d, *args, env=program_env())
        ok(p, "T01 build")
        exe = exe_path(d)
        check(exe.exists(), "demo executable not created")
        r = run([exe], d, env=program_env())
        check(r.returncode == 0 and r.stdout.strip() == "5", f"unexpected run output: {r.stdout!r}")
        p2 = make(d, *args, env=program_env())
        ok(p2, "T01 second make")
        q = run([MAKE, "-q", "all", *args], d, env=program_env())
        check(q.returncode == 0, "second make should be up to date")
        show = make(d, *args, "show", env=program_env()).stdout
        sources = [l for l in show.splitlines() if l.strip().startswith("SOURCES")]
        check(sources and sources[0].count(".c") == 2, f"SOURCES duplicated/missing: {sources}")
    finally:
        cleanup(d)


def t02_cpp_multi_header():
    d = prepare("cpp-multi")
    try:
        args = ("PROGRAM=demo", "SRCDIRS=. src", "CPPFLAGS=-I./inc")
        ok(make(d, *args, env=program_env()), "T02 build")
        files = ("main.o", "src/util.o", "src/other.o")
        before = {f: (d / f).stat().st_mtime_ns for f in files}
        time.sleep(1.2)
        os.utime(d / "inc/util.h", None)
        ok(make(d, *args, env=program_env()), "T02 rebuild")
        for f in ("main.o", "src/util.o"):
            check((d / f).stat().st_mtime_ns > before[f], f"{f} was not rebuilt after header change")
        check((d / "src/other.o").stat().st_mtime_ns == before["src/other.o"],
              "unrelated object was rebuilt")
    finally:
        cleanup(d)


def t03_compile_error_recovery():
    d = prepare()
    try:
        write(d / "main.c", "#error boom\n")
        check(make(d, "PROGRAM=demo", env=program_env()).returncode != 0, "broken source should fail")
        write(d / "main.c", "int main(void){ return 0; }\n")
        ok(make(d, "PROGRAM=demo", env=program_env()), "T03 recovery without deleting .d")
    finally:
        cleanup(d)


def t04_delete_header_clean():
    d = prepare("c-exe")
    try:
        args = ("PROGRAM=demo", "SRCDIRS=. src", "CPPFLAGS=-I./inc")
        ok(make(d, *args, env=program_env()), "T04 initial build")
        (d / "inc/util.h").unlink()
        check(make(d, *args, env=program_env()).returncode != 0, "missing header should fail")
        ok(make(d, *args, "clean", env=program_env()), "T04 clean after missing header")
    finally:
        cleanup(d)


def t05_static_lib():
    d = prepare("auto-lib")
    try:
        ok(make(d, "PROGRAM=demo", "TYPE=static", env=program_env()), "T05 static build")
        lib = d / "libdemo.a"
        check(lib.exists(), "libdemo.a not created")
        out = both(run(["nm", lib.name], d, env=program_env()))
        check("foo" in out, f"symbol foo missing from static lib:\n{out}")
        check("main" not in out, f"main unexpectedly present in static lib:\n{out}")
    finally:
        cleanup(d)


def t06_shared_lib():
    d = prepare("auto-lib")
    try:
        ok(make(d, "PROGRAM=demo", "TYPE=shared", env=program_env()), "T06 shared build")
        lib = shared_path(d)
        check(lib.exists(), f"{lib.name} not created")
        if IS_WIN:
            check((d / "libdemo.dll.a").exists(), "import library libdemo.dll.a missing")
            out = both(run(["objdump", "-p", lib.name], d, env=program_env()))
            check("foo" in out, f"export foo missing from DLL:\n{out}")
        else:
            flag = "-g" if IS_MAC else "-D"
            out = both(run(["nm", flag, lib.name], d, env=program_env()))
            check("foo" in out, f"symbol foo missing from shared lib:\n{out}")
    finally:
        cleanup(d)


def t07_auto_type():
    d = prepare("c-exe")
    try:
        ok(make(d, "PROGRAM=demo", "SRCDIRS=. src", "CPPFLAGS=-I./inc", env=program_env()),
           "T07 auto exe")
        check(exe_path(d).exists(), "auto did not produce executable")
    finally:
        cleanup(d)
    d = prepare("auto-lib")
    try:
        ok(make(d, "PROGRAM=demo", env=program_env()), "T07 auto lib")
        check(shared_path(d).exists(), "auto did not produce library")
    finally:
        cleanup(d)


def t08_mixed_extensions():
    d = prepare("mixed")
    try:
        write(d / "upper.C", 'extern "C" int upper(void){ return 3; }\n')
        p = make(d, "PROGRAM=demo", f"CC={CC}", f"CXX={CXX}", "V=1", env=program_env())
        ok(p, "T08 mixed build")
        out = both(p)
        check(re.search(rf"{re.escape(CC)} .*\ba\.c\b", out), f"a.c was not compiled with {CC}:\n{out}")
        check(re.search(rf"{re.escape(CXX)} .*\bb\.cpp\b", out), f"b.cpp was not compiled with {CXX}:\n{out}")
        check(re.search(rf"{re.escape(CXX)} .*\bupper\.C\b", out), f"upper.C was not compiled with {CXX}:\n{out}")
        check(re.search(rf"{re.escape(CXX)} .*demo", out), f"link did not use {CXX}:\n{out}")
    finally:
        cleanup(d)


def t09_parallel():
    d = prepare("c-exe")
    try:
        ok(make(d, "-j8", "PROGRAM=demo", "SRCDIRS=. src", "CPPFLAGS=-I./inc", env=program_env()),
           "T09 parallel build")
        check(exe_path(d).exists(), "parallel build did not create executable")
    finally:
        cleanup(d)


def t10_clean_distclean():
    d = prepare("c-exe")
    try:
        args = ("PROGRAM=demo", "SRCDIRS=. src", "CPPFLAGS=-I./inc")
        ok(make(d, *args, env=program_env()), "T10 build")
        ok(make(d, *args, "clean", env=program_env()), "T10 clean")
        check(not (d / "main.o").exists() and not exe_path(d).exists(), "clean left objects/products")
        check(any(d.glob("*.d")), "clean should leave dependency files (distclean removes them)")
        ok(make(d, *args, env=program_env()), "T10 rebuild")
        ok(make(d, *args, "distclean", env=program_env()), "T10 distclean")
        check(not any(d.glob("*.d")), "distclean left dependency files")
    finally:
        cleanup(d)


def t11_multi_main():
    d = prepare("multi-main")
    try:
        p = make(d, "V=1", env=program_env())
        ok(p, "T11 multi-main build")
        for name in ("alpha", "beta"):
            check((d / (name + EXE)).exists(), f"{name} executable missing")
        out = both(p)
        check(out.count("common.cpp") == 1, f"common.cpp compiled more than once:\n{out}")
        a = run([d / ("alpha" + EXE)], d, env=program_env())
        b = run([d / ("beta" + EXE)], d, env=program_env())
        check(a.stdout.strip() == "alpha 7" and b.stdout.strip() == "beta 7",
              f"unexpected multi-main output: {a.stdout!r} / {b.stdout!r}")
    finally:
        cleanup(d)


def t12_single_main_name():
    d = prepare("c-exe")
    try:
        ok(make(d, "PROGRAM=demo", "SRCDIRS=. src", "CPPFLAGS=-I./inc", env=program_env()),
           "T12 build")
        check(exe_path(d).exists(), "single main did not honour PROGRAM=demo")
    finally:
        cleanup(d)


def t13_main_false_positive():
    d = prepare("main-false-positive")
    try:
        p = make(d, "PROGRAM=demo", env=program_env())
        check(p.returncode != 0, "commented-out main should not silently build an executable")
        ok(make(d, "PROGRAM=demo", "TYPE=static", env=program_env()), "T13 TYPE=static override")
        check((d / "libdemo.a").exists(), "TYPE=static did not produce a library")
    finally:
        cleanup(d)


def t14_targets_and_v():
    d = prepare("c-exe")
    try:
        args = ("PROGRAM=demo", "SRCDIRS=. src", "CPPFLAGS=-I./inc")
        ok(make(d, *args, env=program_env()), "T14 build")
        help_out = make(d, "help", env=program_env()).stdout
        for target in ("tags", "ctags", "run"):
            check(target in help_out, f"help does not mention {target}")
        show_out = make(d, *args, "show", env=program_env()).stdout
        check("TYPE" in show_out and "SOURCES" in show_out, "show output incomplete")
        ok(make(d, "-n", "tags", env=program_env()), "T14 tags dry-run")
        ok(make(d, *args, "clean", env=program_env()), "T14 clean")
        ok(make(d, *args, "objs", env=program_env()), "T14 objs")
        check((d / "main.o").exists() and not exe_path(d).exists(), "objs should compile only")
        ok(make(d, *args, "clean", env=program_env()), "T14 clean before V=1")
        p = make(d, *args, "V=1", env=program_env())
        ok(p, "T14 V=1 build")
        check("-c" in both(p), "V=1 did not print compile commands")
    finally:
        cleanup(d)


def t15_local_libs():
    d = prepare("local-libs")
    try:
        (d / "libs/math/lib").mkdir(parents=True, exist_ok=True)
        ok(run([CC, "-Ilibs/math/include", "-c", "libs/math/src/math.c", "-o", "math.o"], d, env=program_env()),
           "build local lib object")
        ok(run([AR, "rcs", "libs/math/lib/libmath.a", "math.o"], d, env=program_env()),
           "archive local lib")
        ok(make(d, "PROGRAM=demo", "EXTRA_LIBS=-lmath", env=program_env()), "T15 app build")
        r = run([exe_path(d)], d, env=program_env())
        check(r.stdout.strip() == "5", f"unexpected local-lib output: {r.stdout!r}")
    finally:
        cleanup(d)


def t16_empty_and_no_shell():
    d = prepare()
    try:
        t0 = time.time()
        p = make(d, timeout=10)
        elapsed = time.time() - t0
        check(elapsed < 10, "empty project hung")
        ok(p, "T16 empty project")
        check("No source files" in both(p), "missing empty-project warning")
    finally:
        cleanup(d)
    if not IS_WIN:
        return
    d = prepare()
    try:
        write(d / "main.c", "int main(void){ return 0; }\n")
        env = ENV.copy()
        parts = [p for p in env["PATH"].split(os.pathsep)
                 if "Git\\usr\\bin" not in p and "msys" not in p.lower()]
        env["PATH"] = os.pathsep.join(parts)
        if shutil.which("sh", path=env["PATH"]):
            raise SkipTest("a POSIX shell is still on PATH")
        p = run([MAKE], d, env=env)
        check(p.returncode != 0, "make without sh should fail")
        check("No POSIX shell" in both(p), f"missing actionable error:\n{both(p)}")
    finally:
        cleanup(d)


def t17_symlink_loop():
    if IS_WIN:
        raise SkipTest("symlink loop test is POSIX-only")
    d = prepare()
    try:
        write(d / "main.c", "int main(void){ return 0; }\n")
        os.symlink("..", d / "loop")
        ok(make(d, "PROGRAM=demo", env=program_env()), "T17 symlink loop build")
        objs = list(d.rglob("*.o"))
        check(len(objs) == 1, f"symlink loop duplicated sources: {[str(x) for x in objs]}")
    finally:
        cleanup(d)


def t18_collision_names():
    d = prepare("multi-main-collision")
    try:
        ok(make(d, "PROGRAM=demo", env=program_env()), "T18 collision build")
        for name in ("main", "sub_main", "a_x_main", "b_x_main"):
            check((d / (name + EXE)).exists(), f"{name} executable missing")
        ok(make(d, "clean", env=program_env()), "T18 clean after collision rename")
    finally:
        cleanup(d)
    d = prepare()
    try:
        write(d / "a_b/main.c", "int main(void){ return 0; }\n")
        write(d / "a/b/main.c", "int main(void){ return 0; }\n")
        p = make(d, "PROGRAM=demo", env=program_env())
        check(p.returncode != 0, "residual collision should fail")
        check("MAIN_SRCS" in both(p), f"residual collision message lacks MAIN_SRCS:\n{both(p)}")
    finally:
        cleanup(d)


def t19_depth_warning():
    d = prepare()
    try:
        deep = d
        for i in range(1, 10):
            deep = deep / f"d{i}"
            deep.mkdir()
        write(deep / "main.c", "int main(void){ return 0; }\n")
        p = make(d, "PROGRAM=demo", env=program_env())
        ok(p, "T19 deep tree")
        check("depth limit" in both(p), f"missing depth-limit warning:\n{both(p)}")
    finally:
        cleanup(d)


CASES = [
    ("T01 C exe", t01_c_exe),
    ("T02 C++ multi-dir + header change", t02_cpp_multi_header),
    ("T03 compile error recovery", t03_compile_error_recovery),
    ("T04 delete header + clean", t04_delete_header_clean),
    ("T05 static library", t05_static_lib),
    ("T06 shared library", t06_shared_lib),
    ("T07 TYPE=auto", t07_auto_type),
    ("T08 mixed C/C++ + .c/.C", t08_mixed_extensions),
    ("T09 make -j8", t09_parallel),
    ("T10 clean/distclean", t10_clean_distclean),
    ("T11 multi-main", t11_multi_main),
    ("T12 single-main naming", t12_single_main_name),
    ("T13 main false positive", t13_main_false_positive),
    ("T14 help/show/V=1/objs/tags", t14_targets_and_v),
    ("T15 libs/ auto-discovery", t15_local_libs),
    ("T16 empty / no shell", t16_empty_and_no_shell),
    ("T17 symlink loop", t17_symlink_loop),
    ("T18 collision names", t18_collision_names),
    ("T19 depth warning", t19_depth_warning),
]


def main():
    print(f"repo      : {ROOT}")
    print(f"platform  : {'Windows' if IS_WIN else sys.platform}")
    print(f"make      : {MAKE}")
    print(f"CC / CXX  : {CC} / {CXX}")
    print("-" * 72)
    passed = skipped = failed = 0
    failures = []
    for name, fn in CASES:
        started = time.time()
        try:
            fn()
            passed += 1
            print(f"PASS  {name}  ({time.time() - started:.2f}s)")
        except SkipTest as exc:
            skipped += 1
            print(f"SKIP  {name}  ({exc})")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            failures.append((name, exc, traceback.format_exc()))
            print(f"FAIL  {name}  ({time.time() - started:.2f}s)")
            print(f"      {exc}")
    print("-" * 72)
    print(f"summary: {passed} passed, {failed} failed, {skipped} skipped")
    if failures:
        print("\nFailure details:\n")
        for name, exc, tb in failures:
            print(f"### {name}\n{tb}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
