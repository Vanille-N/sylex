# SyLeX
## LaTeX compilation framework in Python

SyLeX is a simple build system for LaTeX. It covers what I find to be the main
pain points of LaTeX compilation:
- some documents need to be compiled twice (or even thrice)
- `.aux`, `.toc`, `.log`, etc... files littered everywhere
- `\include` doesn't handle paths relative to the current file
- standalones need separate compilation

Features of SyLeX include:
- double compilation (opt-out),
even triple compilation if a bibliography is included
- separate build directory
- `make` integration
- intuitive syntax to specify the file hierarchy
- built-in support for lazy compilation of standalones
- path expansion to simulate relative paths in `\include` and the like

### Installation

Clone this repository to `/path/to/sylex`.

To start a new project, simply type `/path/to/sylex/sylex.py init`.
`sylex.py` does _not_ need to be in your `$PATH`, nor do you need to specify
its position in your project: `sylex` will clone itself into `.sylex/` so
that invocations can be done locally.


