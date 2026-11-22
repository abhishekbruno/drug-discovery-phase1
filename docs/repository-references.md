# Repository references reviewed — 15 November 2026

Reviewed through the GitHub connection for this milestone. No external implementation code or numerical output was copied into Dockpipe.

| Reference | Inspected version/file | Application here |
|---|---|---|
| [Streamlit](https://github.com/streamlit/streamlit/blob/1.50.0/e2e_playwright/st_fragment_run_every.py) | 1.50.0 fragment example, blob `7d0f4a96cc508a4efaa32ecc88db57e352c0b573` | Refresh the selected job's status without repeatedly rebuilding molecular plots. |
| [OdorSig](https://github.com/ODOR-SIG/Automated-Molecular-Docking/blob/main/code/app.py) | `code/app.py`, blob `34ab966cbaca3c3b634d886124ecaebd577930c9` | Visible preparation/docking stages and actionable error feedback. Implement with persisted manifests; retain Dockpipe's background jobs and immutable outputs. |
| [Meeko](https://github.com/forlilab/Meeko/blob/v0.7.1/README.md) | v0.7.1, blob `d91b85c0588421d760186f7b07f17ec6e81df7af` | Confirm the existing ligand/receptor preparation and SDF export boundaries. No dependency upgrade or protocol change. |
| [AutoDock Vina](https://github.com/forlilab/AutoDock-Vina) | Official repository overview; former `ccsb-scripps` repository redirects here | Preserve actual CPU Vina execution and documented search settings. |

The [Streamlit fragment documentation](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment) was also consulted. Implementation stays compatible with pinned Streamlit 1.50.0; newer decorator options are not used. Docking scores remain predictions, not measured affinity or binding-strength classifications.
