#!/usr/bin/env python3
"""Realistic project-level tests for the Makefile template.

Unlike tests/run_tests.py (feature matrix), these projects exercise layouts
that look like actual repositories: include trees, multiple modules, local
libraries, library consumers and mixed C/C++ boundaries.

Usage:
    python tests/run_projects.py
"""

import os
import re
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tests as rt  # noqa: E402

PROJECTS = Path(__file__).resolve().parent / "projects"


def make(project, *args, timeout=180):
    return rt.run([rt.MAKE, *args], project, env=rt.program_env(), timeout=timeout)


def exe(project, name):
    return Path(project) / (name + rt.EXE)


def fresh():
    d = Path(tempfile.mkdtemp(prefix="mfproj-"))
    return d


def add_makefile(d):
    shutil.copy2(rt.ROOT / "Makefile", Path(d) / "Makefile")


def copy_project(name):
    return PROJECTS / name


def p1_cli_app():
    d = fresh()
    try:
        shutil.copytree(copy_project("cli-app"), d, dirs_exist_ok=True)
        add_makefile(d)
        libdir = d / "libs/text/lib"
        libdir.mkdir(parents=True, exist_ok=True)
        rt.ok(rt.run([rt.CC, "-Ilibs/text/include", "-c", "libs/text/src/text.c", "-o", "text.o"],
                     d, env=rt.program_env()), "P1 build local text object")
        rt.ok(rt.run([rt.AR, "rcs", "libs/text/lib/libtext.a", "text.o"],
                     d, env=rt.program_env()), "P1 archive local text lib")
        (d / "text.o").unlink()

        args = ("PROGRAM=cli", "SRCDIRS=src", "INCLUDE=-Iinclude", "EXTRA_LIBS=-ltext")
        rt.ok(make(d, *args), "P1 build")
        r = rt.run([exe(d, "cli")], d, env=rt.program_env())
        rt.ok(r, "P1 run")
        expected = "hello=42\nvalue:42"
        rt.check(r.stdout.strip() == expected, f"P1 unexpected output: {r.stdout!r}")

        objs = [d / "src/main.o", d / "src/core/parser.o", d / "src/core/format.o"]
        for obj in objs:
            rt.check(obj.exists(), f"P1 missing {obj.name}")
        before = [o.stat().st_mtime_ns for o in objs]
        time.sleep(1.2)
        os.utime(d / "include/app/config.h", None)
        rt.ok(make(d, *args), "P1 incremental rebuild")
        for obj, old in zip(objs, before):
            rt.check(obj.stat().st_mtime_ns > old, f"P1 {obj} not rebuilt after config.h change")

        rt.ok(make(d, *args, "clean"), "P1 clean")
        rt.check(not exe(d, "cli").exists() and not (d / "src/main.o").exists(), "P1 clean left products")
        rt.ok(make(d, *args, "-j8"), "P1 parallel build")
        r = rt.run([exe(d, "cli")], d, env=rt.program_env())
        rt.check(r.stdout.strip() == expected, f"P1 parallel output: {r.stdout!r}")
    finally:
        rt.cleanup(d)


def p2_multi_tool():
    d = fresh()
    try:
        shutil.copytree(copy_project("multi-tool"), d, dirs_exist_ok=True)
        add_makefile(d)
        p = make(d, "V=1", "-j8")
        rt.ok(p, "P2 build")
        for name in ("alpha", "beta"):
            rt.check(exe(d, name).exists(), f"P2 missing {name}")
        out = rt.both(p)
        rt.check(out.count("log.cpp") == 1, f"P2 log.cpp compiled more than once:\n{out}")
        rt.check(out.count("util.cpp") == 1, f"P2 util.cpp compiled more than once:\n{out}")
        a = rt.run([exe(d, "alpha")], d, env=rt.program_env())
        b = rt.run([exe(d, "beta")], d, env=rt.program_env())
        rt.check(a.stdout.strip() == "alpha:3", f"P2 alpha output: {a.stdout!r}")
        rt.check(b.stdout.strip() == "beta:7", f"P2 beta output: {b.stdout!r}")
        run = make(d, "run")
        rt.ok(run, "P2 make run")
        rt.check("Multiple executables" in rt.both(run), "P2 make run did not list executables")
    finally:
        rt.cleanup(d)


def p3_static_lib_and_app():
    d = fresh()
    try:
        src = copy_project("static-lib-and-app")
        shutil.copytree(src / "mathlib", d / "lib", dirs_exist_ok=True)
        shutil.copytree(src / "app", d / "app", dirs_exist_ok=True)
        add_makefile(d / "lib")
        add_makefile(d / "app")

        rt.ok(make(d / "lib", "PROGRAM=math", "TYPE=static", "SRCDIRS=src", "INCLUDE=-Iinclude"),
              "P3 build math lib")
        liba = d / "lib" / "libmath.a"
        rt.check(liba.exists(), "P3 libmath.a missing")
        nm = rt.both(rt.run(["nm", liba.name], d / "lib", env=rt.program_env()))
        rt.check("math_add" in nm, f"P3 math_add missing from archive:\n{nm}")

        (d / "app/libs/math/include").mkdir(parents=True, exist_ok=True)
        (d / "app/libs/math/lib").mkdir(parents=True, exist_ok=True)
        shutil.copy2(d / "lib/include/math.h", d / "app/libs/math/include/math.h")
        shutil.copy2(liba, d / "app/libs/math/lib/libmath.a")

        rt.ok(make(d / "app", "PROGRAM=app", "EXTRA_LIBS=-lmath"), "P3 build consumer app")
        r = rt.run([exe(d / "app", "app")], d / "app", env=rt.program_env())
        rt.check(r.stdout.strip() == "42", f"P3 app output: {r.stdout!r}")
    finally:
        rt.cleanup(d)


def p4_c_lib_cpp_app():
    d = fresh()
    try:
        src = copy_project("c-lib-cpp-app")
        shutil.copytree(src / "clib", d / "clib", dirs_exist_ok=True)
        shutil.copytree(src / "app", d / "app", dirs_exist_ok=True)
        add_makefile(d / "clib")
        add_makefile(d / "app")

        p = make(d / "clib", "PROGRAM=cmath", "TYPE=static", "SRCDIRS=src", "INCLUDE=-Iinclude", "V=1")
        rt.ok(p, "P4 build C library")
        out = rt.both(p)
        rt.check(re.search(rf"{re.escape(rt.CC)} .*cmath\.c", out), f"P4 C library not built with {rt.CC}:\n{out}")
        liba = d / "clib" / "libcmath.a"
        rt.check(liba.exists(), "P4 libcmath.a missing")
        nm = rt.both(rt.run(["nm", liba.name], d / "clib", env=rt.program_env()))
        rt.check("c_add" in nm, f"P4 c_add missing from archive:\n{nm}")

        (d / "app/libs/cmath/include").mkdir(parents=True, exist_ok=True)
        (d / "app/libs/cmath/lib").mkdir(parents=True, exist_ok=True)
        shutil.copy2(d / "clib/include/cmath.h", d / "app/libs/cmath/include/cmath.h")
        shutil.copy2(liba, d / "app/libs/cmath/lib/libcmath.a")

        p = make(d / "app", "PROGRAM=app", "EXTRA_LIBS=-lcmath", "V=1")
        rt.ok(p, "P4 build C++ app")
        out = rt.both(p)
        rt.check(re.search(rf"{re.escape(rt.CXX)} .*main\.cpp", out), f"P4 app not compiled with {rt.CXX}:\n{out}")
        rt.check(re.search(rf"{re.escape(rt.CXX)} .*app", out), f"P4 app not linked with {rt.CXX}:\n{out}")
        r = rt.run([exe(d / "app", "app")], d / "app", env=rt.program_env())
        rt.check(r.stdout.strip() == "42", f"P4 app output: {r.stdout!r}")
    finally:
        rt.cleanup(d)


def p5_shared_lib_and_app():
    d = fresh()
    try:
        src = copy_project("shared-lib-and-app")
        shutil.copytree(src / "mathlib", d / "lib", dirs_exist_ok=True)
        shutil.copytree(src / "app", d / "app", dirs_exist_ok=True)
        add_makefile(d / "lib")
        add_makefile(d / "app")

        rt.ok(make(d / "lib", "PROGRAM=math", "TYPE=shared", "SRCDIRS=src", "INCLUDE=-Iinclude"),
              "P5 build shared library")

        (d / "app/libs/math/include").mkdir(parents=True, exist_ok=True)
        (d / "app/libs/math/lib").mkdir(parents=True, exist_ok=True)
        shutil.copy2(d / "lib/include/math.h", d / "app/libs/math/include/math.h")

        if rt.IS_WIN:
            dll = d / "lib" / "math.dll"
            implib = d / "lib" / "libmath.dll.a"
            rt.check(dll.exists(), "P5 math.dll missing")
            rt.check(implib.exists(), "P5 import library missing")
            shutil.copy2(implib, d / "app/libs/math/lib/libmath.dll.a")
            shutil.copy2(dll, d / "app/math.dll")
        else:
            name = "libmath.dylib" if rt.IS_MAC else "libmath.so"
            lib = d / "lib" / name
            rt.check(lib.exists(), f"P5 {name} missing")
            shutil.copy2(lib, d / "app/libs/math/lib" / name)

        rt.ok(make(d / "app", "PROGRAM=app", "EXTRA_LIBS=-lmath"), "P5 build consumer app")
        env = rt.program_env()
        if not rt.IS_WIN:
            key = "DYLD_LIBRARY_PATH" if rt.IS_MAC else "LD_LIBRARY_PATH"
            old = env.get(key, "")
            path = str(d / "app/libs/math/lib")
            env[key] = path + (os.pathsep + old if old else "")
        r = rt.run([exe(d / "app", "app")], d / "app", env=env)
        rt.check(r.returncode == 0, f"P5 app failed to run:\n{r.stderr}")
        rt.check(r.stdout.strip() == "42", f"P5 unexpected output: {r.stdout!r}")
    finally:
        rt.cleanup(d)


CASES = [
    ("P1 cli-app (C, include tree + local lib)", p1_cli_app),
    ("P2 multi-tool (C++, two entry points)", p2_multi_tool),
    ("P3 static library + consumer app", p3_static_lib_and_app),
    ("P4 C library + C++ app", p4_c_lib_cpp_app),
    ("P5 shared library + consumer app", p5_shared_lib_and_app),
]


def main():
    print(f"repo      : {rt.ROOT}")
    print(f"platform  : {'Windows' if rt.IS_WIN else sys.platform}")
    print(f"make      : {rt.MAKE}")
    print(f"CC / CXX  : {rt.CC} / {rt.CXX}")
    print("-" * 72)
    passed = failed = 0
    failures = []
    for name, fn in CASES:
        started = time.time()
        try:
            fn()
            passed += 1
            print(f"PASS  {name}  ({time.time() - started:.2f}s)")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            failures.append((name, exc, traceback.format_exc()))
            print(f"FAIL  {name}  ({time.time() - started:.2f}s)")
            print(f"      {exc}")
    print("-" * 72)
    print(f"summary: {passed} passed, {failed} failed")
    if failures:
        print("\nFailure details:\n")
        for name, exc, tb in failures:
            print(f"### {name}\n{tb}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
