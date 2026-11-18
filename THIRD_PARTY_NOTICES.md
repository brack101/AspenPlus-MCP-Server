# Third-Party Notices

This project includes third-party code that is **not** covered by the project's MIT license.

## AspenPlus Python Interface

| | |
|---|---|
| **File in this repository** | `src/aspenplus_mcp/aspen_interface.py` |
| **Upstream** | https://github.com/YouMayCallMeJesus/AspenPlus-Python-Interface |
| **Upstream file** | `CodeLibrary.py` |
| **Upstream version** | 2.1 (per `CITATION.cff`) |
| **Upstream commit** | `2f381f93371d9b774374f9374eb8c825ae9f56de` (2022-06-22, last change to `CodeLibrary.py`; still identical at upstream `9a43c0e`, 2026-08-14) |
| **Author** | Richard Wolfgang ten Hagen |
| **Modifications** | None – byte-identical copy, only renamed (incl. CRLF line endings) |
| **SHA-256** | `38f53b49ad419bf0c8cb45a81031bd78c06c74ad197a6cfe9c26762f1191e4c9` |

### License / terms of use

The upstream repository contains **no license file**. The only statement on usage is
in its README (quoted verbatim):

> Concerning licences and the freedom to use it: You are welcome to use it for any
> project you have. If you start making significant money with it please email me.
> For academic research you are ofcourse welcome to use it but please cite me.

Citation (from upstream `CITATION.cff`):

> ten Hagen, Richard Wolfgang. *AspenPlus Python Interface*, version 2.1, 2022.
> https://github.com/YouMayCallMeJesus/AspenPlus-Python-Interface

The file header additionally asks: *"If you change it, update it, fix something just
email me such that I can also update my version to keep it as coherent as possible."*

### Notes for maintainers

- **Do not modify the file.** Work around its behaviour in `aspen_wrapper.py` instead,
  so it stays diffable against upstream. It is excluded from `black` for this reason.
- Known side effects, contained by `_isolated_vendored_call()` in `aspen_wrapper.py`:
  - `print()` to stdout (would corrupt the MCP stdio JSON-RPC channel)
  - `os.chdir()` in `Simulation.__init__`
  - the COM dispatch (`Apwn.Document`) is created at import time as a class attribute
- To check for upstream changes:
  ```bash
  curl -sL https://raw.githubusercontent.com/YouMayCallMeJesus/AspenPlus-Python-Interface/main/CodeLibrary.py | sha256sum
  ```
- The upstream README now recommends a different implementation
  (https://github.com/adk23333); evaluate it before extending the enhanced mode.
