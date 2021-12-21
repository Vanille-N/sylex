# SyLeX
## LaTeX compilation framework in Python

SyLeX is a simple build system for LaTeX. It covers what I find to be the main
pain points of LaTeX compilation:
- some documents need to be compiled twice
- `.aux`, `.toc`, `.log`, etc... files littered everywhere
- `\include` doesn't handle paths relative to the current file

Features of SyLeX include:
- double compilation (opt-out with the `QUICK` option),
even triple compilation if a bibliography is included
- separate build directory
- `make` integration
- intuitive syntax to specify the file hierarchy
- built-in support for lazy compilation of standalones
- path expansion to simulate relative paths in `\include`


