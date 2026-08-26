# Project Rules

## Purpose

These rules define the common engineering conventions for the `py_gui_xcp`
project. They apply to new code and to touched code during maintenance.

## Python Style

- Follow [PEP 8](https://peps.python.org/pep-0008/).
- Use four spaces for indentation. Do not use tabs.
- Keep lines at a readable length. Prefer a maximum of 88 characters where practical.
- Use two blank lines between top-level classes and functions.
- Use one blank line between methods inside a class.
- Prefer clear, small functions over deeply nested logic.
- Add type hints to public functions, methods, and non-obvious attributes.
- Use docstrings for public classes and methods that have non-obvious behavior.
- Avoid unused imports, duplicate imports, wildcard imports, and dead code.
- Use ASCII for source files unless Unicode is required by the user interface.

## Naming

- Use `snake_case` for variables, functions, methods, and module names.
- Use `PascalCase` for classes.
- Use `UPPER_SNAKE_CASE` for module-level constants.
- Use descriptive names. Avoid abbreviations unless they are established domain terms such as `XCP`, `DAQ`, or `ECU`.
- Use a leading underscore for internal implementation details.
- Use consistent terminology. Prefer `signal`, `widget`, `data_manager`, `timestamp`, and `value`.

## Classes and Modules

- Keep one primary responsibility per class and module.
- Keep reusable behavior in base classes only when all subclasses share the same contract.
- Subclasses may override `export_state()` and `import_state()` for widget-specific state, but must call `super()` when preserving common state.
- Do not duplicate shared behavior between widgets. Extend `WidgetBase` hooks instead.
- Keep UI code in `ui/`, XCP and data-flow code in `xcp/`, and application orchestration in `pyxcp_gui_app.py`.

## Qt and GUI Rules

- Create and modify Qt widgets only on the GUI thread.
- Use Qt signals and slots to deliver data from worker threads to widgets.
- Do not update widgets directly from `QThread.run()` or other worker-thread code.
- Stop worker threads and timers before destroying their widgets.
- Disconnect or release widget-owned resources during `closeEvent()`.
- Reuse common context-menu and persistence behavior from `WidgetBase`.
- Keep context-menu actions safe when there is no selected row or signal.
- Avoid blocking dialogs or long-running operations on the GUI thread.

## DataManager and Signals

- Access shared signal state through `DataManager` APIs.
- Widgets must acquire signal ownership when they display or plot a signal.
- Widgets must release signal ownership when a signal is removed or the widget closes.
- A signal must not be deleted while another widget still references it.
- Keep thread-protected state inside `DataManager`; do not mutate shared state from widgets without an API.
- Worker data must use the tuple contract `(timestamp, name, value)` unless the contract is deliberately changed everywhere.
- Unknown incoming signals must be handled explicitly and must not cause an uncontrolled `KeyError`.

## Widget State and Persistence

- All `WidgetBase` subclasses must support `export_state()` and `import_state()`.
- Common window state belongs in `WidgetBase`.
- Widget-specific state belongs in the subclass state dictionary.
- State data must be composed of simple, validated, serializable values.
- Loading a project must replace the current workspace rather than append duplicate widgets.
- New widget types must be added to both project save and project load registries.
- Preserve compatibility with existing project files when changing the persistence schema.
- Do not persist live samples or transient worker state unless explicitly required.

## Error Handling

- Catch only exceptions that can be handled meaningfully.
- Do not use bare `except` or silently discard exceptions with `pass`.
- Report connection, configuration, and persistence failures through logging or a user-visible status message.
- Preserve the original exception context when re-raising or wrapping errors.
- Validate external and persisted data before using it.

## Testing and Validation

- Run bytecode compilation for changed Python modules:
  `\.venv\Scripts\python.exe -m py_compile <files>`
- Add focused tests for signal ownership, widget state round-trips, and context-menu actions.
- Use headless Qt testing with `QT_QPA_PLATFORM=offscreen` where a display is not available.
- Test both normal behavior and edge cases such as empty selections, duplicate names, removed signals, and malformed state.
- Do not rely only on manual GUI testing for data-flow or persistence changes.

## Change Review

- Prefer the smallest change that solves the problem.
- Do not change unrelated files or reformat untouched code without a reason.
- Review threading, ownership, persistence, and shutdown behavior for every GUI change.
- Remove obsolete comments and TODOs when the related code is changed.
- Update this document when a project-wide convention changes.
