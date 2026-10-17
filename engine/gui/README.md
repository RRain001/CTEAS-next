# CTEAS GUI

Run:

```bash
./calpuff-cli desktopgui
```

Or, from the repository root:

```bash
.venv/bin/python -m engine.ui.desktop.main
```

The only supported GUI is the PySide6 desktop GUI. Legacy `webgui` and
`streamlitgui` entrypoints have been removed.

- Select case from `project/cases/*`
- Edit preprocess parameters
- Save directly to `project/cases/<case>/case.yaml`
- Run pipeline via `calpuff-cli` (`stage` + `resume`)
- View live run logs
