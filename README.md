# QE Input Generator — Free Online Quantum ESPRESSO GUI

> Generate Quantum ESPRESSO pw.x input files online — no installation, no coding.

A free, web-based GUI for [Quantum ESPRESSO](https://www.quantum-espresso.org/) input file generation. Designed for researchers, students, and computational physicists who want to set up DFT calculations, band structure calculations, and structural relaxations quickly and correctly.

**🌐 Try it live →** *(deploy your own on [Streamlit Community Cloud](https://share.streamlit.io) for free)*

Built with [Streamlit](https://streamlit.io). Works in any browser — no installation required.

---

## Features

- **6-step wizard** — guided workflow from structure to ready-to-run input files
- **Crystal structure** — upload CIF (via pymatgen), choose from 6 presets, or enter manually
- **Pseudopotentials** — upload your own UPF files from your computer **or** point to a folder on the machine; ecutwfc auto-suggested from UPF file headers
- **CONTROL + SYSTEM** — all 7 calculation types with smart defaults and contextual tips:
  - `scf`, `nscf`, `bands`, `relax`, `vc-relax`, `md`, `vc-md`
  - Smearing (Methfessel-Paxton, Gaussian, Fermi-Dirac, cold)
  - DFT+U (Hubbard U per element)
  - Spin-orbit coupling (noncolin + lspinorb)
- **ELECTRONS + IONS + CELL** — convergence, mixing, diagonalisation, BFGS relaxation, variable-cell dynamics
- **K-Points** — automatic mesh, Gamma-only, or band structure paths
  - **Preset high-symmetry paths** — FCC, BCC, HEX, Tetragonal, Simple Cubic
  - **Manual k-point editor** — write your own `K_POINTS crystal_b` block with live validation; load a preset and edit it
- **Download** — `.in` file only, ZIP, or **tar.gz** (all include your pseudopotentials)
- **Run pw.x locally** — specify your QE binary folder, working directory, and MPI processes; live output tail
- **Results viewer** — parse pw.x output, SCF convergence plot, forces table, energy and Fermi level
- **Version tracking** — version number and changelog visible in sidebar

---

## Screenshots

| Step 1 — Structure | Step 2 — Pseudopotentials | Step 5 — K-Points & Download |
|---|---|---|
| CIF upload / presets | Upload UPF from your computer | Manual k-point editor + tar.gz |

---

## Quick Start (local)

```bash
git clone https://github.com/ShahiDDU/qe-input-generator.git
cd qe-input-generator
pip install -r requirements.txt
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## Deploy on Streamlit Community Cloud (free)

1. Fork this repo to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io) → **Create app**
3. Select your fork, branch `main`, file `app.py`
4. Click **Deploy**

> **Note:** The Run pw.x button is automatically hidden in the cloud version. All input file generation and download works fully in the cloud.

---

## Pseudopotentials

This app does **not** bundle any pseudopotential files. You must provide your own UPF files, which you can obtain from:

| Library | URL | Notes |
|---------|-----|-------|
| PSlibrary | [gitlab.com/dalcorso/pslibrary](https://gitlab.com/dalcorso/pslibrary) | Recommended, PAW & USPP |
| SSSP | [materialscloud.org/discover/sssp](https://www.materialscloud.org/discover/sssp) | Verified efficiency/accuracy |
| ONCVPSP | [pseudo-dojo.org](http://www.pseudo-dojo.org) | Norm-conserving |
| QE website | [quantum-espresso.org/pseudopotentials](https://www.quantum-espresso.org/pseudopotentials) | Various sets |

In the app, go to **Step 2** and either:
- **Upload UPF files** directly from your computer (they get bundled in the ZIP/tar.gz download), or
- **Enter a folder path** on the local machine where your UPF files live

---

## Band Structure K-Points

In Step 5, when you select **Line mode (band structure)**:

**Preset paths** (auto-generated):

| Crystal system | Path |
|---|---|
| FCC | Γ → X → M → Γ → R → X |
| BCC | Γ → H → N → Γ → P → H |
| Hexagonal | Γ → M → K → Γ → A → L → H → A |
| Tetragonal | Γ → X → M → Γ → Z → R → A → Z |
| Simple Cubic | Γ → X → M → Γ → R → X |

**Manual editor** — paste your own `K_POINTS crystal_b` block:
```
K_POINTS crystal_b
  5
  0.000000  0.000000  0.000000  20  ! Gamma
  0.500000  0.000000  0.500000  20  ! X
  0.500000  0.250000  0.750000  20  ! W
  0.500000  0.500000  0.500000  20  ! L
  0.000000  0.000000  0.000000   1  ! Gamma
```
Click **"Load preset → manual editor"** to start from a preset and customise it.

---

## Preset Structures

| Preset | Formula | Description |
|--------|---------|-------------|
| Si diamond | Si₂ | FCC primitive cell, a = 5.431 Å |
| Fe BCC | Fe | Cubic cell, a = 2.87 Å |
| Cu FCC | Cu | FCC primitive cell, a = 3.615 Å |
| Al FCC | Al | FCC primitive cell, a = 4.05 Å |
| MgO rocksalt | MgO | FCC primitive cell, a = 4.21 Å |
| TiO₂ rutile | Ti₂O₄ | Tetragonal, a = 4.594 Å, c = 2.959 Å |

---

## Updating

Every `git push` to `main` automatically redeploys on Streamlit Cloud.

```bash
# edit app.py — bump APP_VERSION and add a line to CHANGELOG at the top
git add -A
git commit -m "v1.x: describe what changed"
git push
```

The new version number and changelog are shown in the sidebar for users to see.

---

## Requirements

| Package | Purpose |
|---------|---------|
| `streamlit` | Web UI framework |
| `pymatgen` | CIF parsing and structure conversion |
| `numpy` | Numerical operations |
| `matplotlib` | SCF convergence plots |
| `ase` | Auxiliary structure utilities |

---

## Project Structure

```
qe-input-generator/
├── app.py                  # Main Streamlit application (v1.3.0)
├── config.py               # Element data, calc type lists, path defaults
├── qe/
│   ├── input_writer.py     # PWInput class — builds pw.x input files
│   ├── output_parser.py    # Parses pw.x output (energy, forces, convergence)
│   └── runner.py           # QERunner — subprocess manager for pw.x
├── test_input.py           # Step-by-step terminal test for the backend
├── requirements.txt
└── .streamlit/
    └── config.toml         # White theme and server settings
```

---

## Running the Terminal Test

To verify the input generator works without the GUI:

```bash
python3 test_input.py
```

This walks through all 8 steps (structure → pseudos → CONTROL → SYSTEM → ELECTRONS → K-points → save → validate) and prints the growing input file at each step.

---

## Related Projects

- [VASP Input Generator](https://github.com/ShahiDDU/vasp-input-generator) — same wizard UI for VASP (INCAR, POSCAR, KPOINTS, POTCAR)

---

## Keywords

`Quantum ESPRESSO` `QE input generator` `pw.x` `pwscf` `DFT` `density functional theory` `ab initio` `materials science` `computational physics` `band structure` `structural relaxation` `pseudopotentials` `UPF` `HSE` `DFT+U` `Hubbard U` `spin-orbit coupling` `molecular dynamics` `streamlit` `online DFT tool` `KPOINTS crystal_b`

---

## License

This project is open-source. Quantum ESPRESSO itself is free and open-source under the GPL license. Pseudopotential files have their own individual licenses — check the source library for details.
