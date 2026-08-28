# GUI local notes

The Tkinter GUI, `voice_memos_exporter.py`, exists only on the local branch
`gui/local-app`. It is not published, released, or distributed.

Its UI structure is derived from `rudrakabir/voice-memos-exporter`. The database
access and export logic were replaced by this fork's `vmx_core` module.

The upstream license status is unresolved. Do not add a `LICENSE` file or SPDX
identifier while that remains unresolved.

`vmx_core.py` is the single export engine. The GUI and the CLI,
`export_voice_memos.py`, are two front ends over the same core API. The GUI does
not parse CLI stdout and does not shell out to the CLI.

Run the GUI with:

```bash
python3 voice_memos_exporter.py
```

Grant Full Disk Access to the terminal application that runs Python, not to a
`.app` bundle.
