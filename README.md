# MakefileTemplate
A Generic Makefile Template for C/C++ Projects

## Description

### Features:
* Automatically traverses and lists all (code files in) sub-directories, or you manually add;
* Automatically generates and processes dependencies; 
* Can hanlde cross-compiling or cross-platform projects (e.g. Linux, MacOS, Windows);
* Can work with C projects, C++ projects, or mixed;
* With examples in-file, and flags for high performance with small size of binary; 
* Not only for executable binaries, but also for static & dynamic libraries [to-do].

### Usage:
1. Copy the `Makefile` file to your program source code directory.
2. Customize in the "Customizable Section" only if necessary:
    * to use non-standard C/C++ libraries, set pre-processor or compiler
      options to `<EXTRA_CFLAGS>` and linker ones to `<EXTRA_LIBS>`
    * to search sources in more directories, set to `<SRCDIRS>`
    * to specify your favorite program name, set to `<PROGRAM>`
3. Type `make` to start building your program.

### Make Target:
The Makefile provides the following targets to make:
```Shell
   make            # compile and link
   make NODEP=yes  # compile and link without generating dependencies
   make objs       # compile only (no linking)
   make tags       # create tags for Emacs editor
   make ctags      # create ctags for VI editor
   make clean      # clean objects and the executable file
   make distclean  # clean objects, the executable and dependencies
   make help       # get the usage of the makefile
```

## Users
+ [Pear] (https://pear.hk)
+ [HKUST] (http://www.ust.hk)

## Reference & Thanks to
+ https://sourceforge.net/projects/gcmakefile/
+ https://github.com/mbcrawfo/GenericMakefile
+ http://blog.csdn.net/kevin1078/article/details/7492619
+ http://www.digitalpeer.com/blog/example
