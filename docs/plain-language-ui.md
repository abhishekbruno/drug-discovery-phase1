# Plain-language UI pass — 2026-11-16

The workspace now explains docking as a prediction of how a small molecule fits into a protein. A three-step guide explains setup, progress and results. Setup introduces ligands, SMILES, search regions and search effort alongside existing controls. The bundled practice run is clearly distinguished from the validation benchmark.

The results tab presents rank, molecule and predicted score first, with full molecular properties available under an advanced disclosure. Technical pose measurements are also collapsed. Download labels explain the purpose of each file. Progress and recovery text explain which work is retained and what can be retried.

Scientific calculations, defaults and saved output schemas are unchanged. Lower scores are described only as better within the same run, and the UI distinguishes predictions from experimental evidence.

Verification: all six existing UI tests passed; Python compilation and git diff whitespace checks passed. Browser inspection confirmed the guide, result table and setup screen. A 390-pixel viewport reported a document width of 390 pixels. Preview: `images/plain-language-workspace.jpg`.

The previous commit's GitHub scientific checks passed in runs 43732647347 and 43732643124. The GitHub connector returned 404 for the private PR, so repository checks and push used the existing authenticated Git connection.
