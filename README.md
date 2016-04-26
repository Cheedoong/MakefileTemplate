# MakefileTemplate
A Generic Makefile Template for C/C++ Programs

## Description

### Usage:
+ 1. Copy the Makefile to your program directory.
+ 2. Customize in the "Customizable Section" only if necessary:
      * to use non-standard C/C++ libraries, set pre-processor or compiler
      options to <MY_CFLAGS> and linker ones to <MY_LIBS>
      (See Makefile.gtk+-2.0 for an example)
    * to search sources in more directories, set to <SRCDIRS>
    * to specify your favorite program name, set to <PROGRAM>
+ 3. Type make to start building your program.

### Make Target:
The Makefile provides the following targets to make:
-   $ make           compile and link
-   $ make NODEP=yes compile and link without generating dependencies
-   $ make objs      compile only (no linking)
-   $ make tags      create tags for Emacs editor
-   $ make ctags     create ctags for VI editor
-   $ make clean     clean objects and the executable file
-   $ make distclean clean objects, the executable and dependencies
-   $ make help      get the usage of the makefile

## Users
+ Pear (https://pear.hk)
+ HKUST (http://www.ust.hk)

## Reference & Thanks to
+ https://sourceforge.net/projects/gcmakefile/
+ https://github.com/mbcrawfo/GenericMakefile
+ http://my.oschina.net/taisha/blog/55055
