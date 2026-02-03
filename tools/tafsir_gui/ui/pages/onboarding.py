from __future__ import annotations

from nicegui import ui


def render():
    ui.markdown(
        """
### Welcome
This guided wizard will run the Text Manipulation Pipeline end-to-end without. 
Progress, logs, and validation are visible at every step.

**What happens:**
- Pre-flight checks catch missing keys, cache issues, file problems, and DB access.
- The pipeline ingests your input, probes Gemini for structure rules, builds the schema, then runs annotation + bulk inserts.
- You can pause/resume or auto-resume after temporary API limits.
"""
    )


__all__ = ["render"]
