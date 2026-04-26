"""QE GUI — Streamlit web application for Quantum ESPRESSO input generation."""
from __future__ import annotations

import copy
import glob
import gzip
import io
import os
import sys
import tarfile
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

APP_VERSION = "1.3.0"
CHANGELOG = """
**v1.3.0** — Manual k-point editor for band structure; ZIP + tar.gz downloads; version tracking
**v1.2.0** — White theme; user-uploadable pseudopotentials; no hardcoded paths
**v1.1.0** — Cloud detection; IS_CLOUD mode; uploaded pseudo bundled in ZIP
**v1.0.0** — Initial release: 6-step wizard, presets, CIF import, DFT+U, SOC
"""

import streamlit as st

# Add QEGUI root to path so internal imports work regardless of cwd
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

st.set_page_config(
    page_title="QE Input Generator",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Import QE backend (do NOT modify these modules)
from qe.input_writer import PWInput
from qe.output_parser import parse_scf_output
from qe.runner import QERunner
from config import (
    CALC_TYPES, OCCUPATION_TYPES, SMEARING_TYPES,
    MIXING_MODES, DIAG_TYPES, ION_DYNAMICS, CELL_DYNAMICS,
    get_atomic_mass,
)

# ─── Cloud detection ──────────────────────────────────────────────────────────
IS_CLOUD: bool = (
    os.getenv("STREAMLIT_SHARING_MODE") == "streamlit_sharing"
    or os.getenv("IS_CLOUD", "").lower() in ("1", "true", "yes")
)

# ─── Preset structures ────────────────────────────────────────────────────────
PRESETS: Dict[str, Dict] = {
    "Si diamond (2 atoms)": {
        "elements": ["Si"],
        "nat": 2,
        "ntyp": 1,
        "cell": [[0.0, 2.7155, 2.7155],
                 [2.7155, 0.0, 2.7155],
                 [2.7155, 2.7155, 0.0]],
        "positions": [("Si", 0.0, 0.0, 0.0),
                      ("Si", 1.35775, 1.35775, 1.35775)],
        "desc": "Si diamond cubic, a=5.431 Å, FCC primitive cell",
    },
    "Fe BCC (1 atom)": {
        "elements": ["Fe"],
        "nat": 1,
        "ntyp": 1,
        "cell": [[2.87, 0.0, 0.0],
                 [0.0, 2.87, 0.0],
                 [0.0, 0.0, 2.87]],
        "positions": [("Fe", 0.0, 0.0, 0.0)],
        "desc": "Fe BCC, a=2.87 Å, conventional cubic cell",
    },
    "Cu FCC (1 atom)": {
        "elements": ["Cu"],
        "nat": 1,
        "ntyp": 1,
        "cell": [[0.0, 1.8075, 1.8075],
                 [1.8075, 0.0, 1.8075],
                 [1.8075, 1.8075, 0.0]],
        "positions": [("Cu", 0.0, 0.0, 0.0)],
        "desc": "Cu FCC, a=3.615 Å, primitive cell",
    },
    "Al FCC (1 atom)": {
        "elements": ["Al"],
        "nat": 1,
        "ntyp": 1,
        "cell": [[0.0, 2.025, 2.025],
                 [2.025, 0.0, 2.025],
                 [2.025, 2.025, 0.0]],
        "positions": [("Al", 0.0, 0.0, 0.0)],
        "desc": "Al FCC, a=4.05 Å, primitive cell",
    },
    "MgO rocksalt (2 atoms)": {
        "elements": ["Mg", "O"],
        "nat": 2,
        "ntyp": 2,
        "cell": [[0.0, 2.105, 2.105],
                 [2.105, 0.0, 2.105],
                 [2.105, 2.105, 0.0]],
        "positions": [("Mg", 0.0, 0.0, 0.0),
                      ("O", 2.105, 2.105, 2.105)],
        "desc": "MgO rocksalt, a=4.21 Å, FCC primitive cell",
    },
    "TiO2 rutile (6 atoms)": {
        "elements": ["Ti", "O"],
        "nat": 6,
        "ntyp": 2,
        "cell": [[4.594, 0.0, 0.0],
                 [0.0, 4.594, 0.0],
                 [0.0, 0.0, 2.959]],
        "positions": [
            ("Ti", 0.0,    0.0,    0.0),
            ("Ti", 2.297,  2.297,  1.4795),
            ("O",  1.4065, 1.4065, 0.0),
            ("O",  3.1875, 0.8065, 1.4795),
            ("O",  0.8065, 3.1875, 1.4795),
            ("O",  3.1875, 3.1875, 0.0),
        ],
        "desc": "TiO2 rutile, a=4.594 Å, c=2.959 Å, tetragonal conventional cell",
    },
}

# ─── High-symmetry k-paths ────────────────────────────────────────────────────
KPATHS: Dict[str, List[Tuple]] = {
    "FCC (Γ-X-M-Γ-R-X)": [
        ("G", [0.0, 0.0, 0.0]),
        ("X", [0.5, 0.0, 0.5]),
        ("M", [0.5, 0.5, 0.0]),
        ("G", [0.0, 0.0, 0.0]),
        ("R", [0.5, 0.5, 0.5]),
        ("X", [0.5, 0.0, 0.5]),
    ],
    "BCC (Γ-H-N-Γ-P-H)": [
        ("G", [0.0, 0.0, 0.0]),
        ("H", [0.5, -0.5, 0.5]),
        ("N", [0.0, 0.0, 0.5]),
        ("G", [0.0, 0.0, 0.0]),
        ("P", [0.25, 0.25, 0.25]),
        ("H", [0.5, -0.5, 0.5]),
    ],
    "Simple Cubic (Γ-X-M-Γ-R-X)": [
        ("G", [0.0, 0.0, 0.0]),
        ("X", [0.5, 0.0, 0.0]),
        ("M", [0.5, 0.5, 0.0]),
        ("G", [0.0, 0.0, 0.0]),
        ("R", [0.5, 0.5, 0.5]),
        ("X", [0.5, 0.0, 0.0]),
    ],
    "Hexagonal (Γ-M-K-Γ-A-L-H-A)": [
        ("G", [0.0, 0.0, 0.0]),
        ("M", [0.5, 0.0, 0.0]),
        ("K", [1/3, 1/3, 0.0]),
        ("G", [0.0, 0.0, 0.0]),
        ("A", [0.0, 0.0, 0.5]),
        ("L", [0.5, 0.0, 0.5]),
        ("H", [1/3, 1/3, 0.5]),
        ("A", [0.0, 0.0, 0.5]),
    ],
    "Tetragonal (Γ-X-M-Γ-Z-R-A-Z)": [
        ("G", [0.0, 0.0, 0.0]),
        ("X", [0.5, 0.0, 0.0]),
        ("M", [0.5, 0.5, 0.0]),
        ("G", [0.0, 0.0, 0.0]),
        ("Z", [0.0, 0.0, 0.5]),
        ("R", [0.5, 0.0, 0.5]),
        ("A", [0.5, 0.5, 0.5]),
        ("Z", [0.0, 0.0, 0.5]),
    ],
}

# ─── Session state defaults ───────────────────────────────────────────────────
_DEFAULTS: Dict[str, Any] = {
    "step": 0,
    "elements": [],
    "nat": 0,
    "ntyp": 0,
    "cell_parameters": None,
    "atomic_positions": [],
    "pos_units": "angstrom",
    "calc_type": "scf",
    "prefix": "pwscf",
    "outdir": "./tmp",
    "restart_mode": "from_scratch",
    "ecutwfc": 60.0,
    "ecutrho": 480.0,
    "occupations": "smearing",
    "smearing": "methfessel-paxton",
    "degauss": 0.01,
    "nbnd": 0,
    "nspin": 1,
    "noncolin": False,
    "lspinorb": False,
    "lda_plus_u": False,
    "hubbard_u": {},
    "conv_thr": 1.0e-8,
    "mixing_beta": 0.7,
    "electron_maxstep": 200,
    "mixing_mode": "plain",
    "diagonalization": "david",
    "ion_dynamics": "bfgs",
    "nstep": 100,
    "cell_dynamics": "bfgs",
    "press_conv_thr": 0.5,
    "kpoints_type": "automatic",
    "kpoints_nx": 4,
    "kpoints_ny": 4,
    "kpoints_nz": 4,
    "kpoints_s0": 0,
    "kpoints_s1": 0,
    "kpoints_s2": 0,
    "kpoints_path_key": list(KPATHS.keys())[0],
    "kpoints_npoints": 20,
    "kpoints_band_mode": "preset",   # "preset" or "manual"
    "kpoints_manual_text": "",       # raw crystal_b block for manual entry
    "pseudo_map": {},           # {elem: filename}
    "uploaded_pseudos": {},     # {filename: bytes} — user-uploaded UPF files
    "pseudo_source": "upload",  # "upload" or "folder"
    "pseudo_folder": "",        # user-specified folder path
    "pseudo_dir_for_input": "./pseudo",  # written into the input file
    "qe_bin_dir": "",           # user-specified QE binary folder
    "work_dir": "./qe_run",
    "qe_nproc": 1,
    "job_running": False,
    "job_done": False,
    "job_output_lines": [],
    "output_file": "",
    "structure_summary": {},
}

for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

ss = st.session_state

# ─── Steps definition ─────────────────────────────────────────────────────────
STEPS = [
    ("1", "Crystal Structure"),
    ("2", "Pseudopotentials"),
    ("3", "CONTROL + SYSTEM"),
    ("4", "ELECTRONS + IONS + CELL"),
    ("5", "K-Points + Download"),
    ("6", "Results"),
]

# ─── Helper: find pseudopotentials ───────────────────────────────────────────

def _match_pseudos_in_names(element: str, names: List[str]) -> List[str]:
    """Return names that look like pseudopotentials for element, priority-ordered."""
    import re
    el = element
    el_low = el.lower()
    paw, pbe, other = [], [], []
    for n in names:
        n_low = n.lower()
        if not (n_low.startswith(el_low + ".") or n_low.startswith(el_low + "_")):
            continue
        if "kjpaw" in n_low or "paw" in n_low:
            paw.append(n)
        elif "pbe" in n_low or "rrkjus" in n_low:
            pbe.append(n)
        else:
            other.append(n)
    return paw + pbe + other


def find_pseudos_uploaded(element: str) -> List[str]:
    """Return uploaded UPF filenames matching element."""
    return _match_pseudos_in_names(element, list(ss.uploaded_pseudos.keys()))


def find_pseudos_folder(element: str, folder: str) -> List[str]:
    """Return UPF filenames matching element in user-specified folder."""
    if not folder or not os.path.isdir(folder):
        return []
    all_names = [
        os.path.basename(p)
        for p in sorted(glob.glob(os.path.join(folder, "*.UPF")))
        + sorted(glob.glob(os.path.join(folder, "*.upf")))
    ]
    return _match_pseudos_in_names(element, all_names)


def suggest_ecutwfc_from_bytes(content: bytes) -> Optional[float]:
    """Try to read ecutwfc hint from UPF file bytes."""
    import re
    try:
        text = content[:4096].decode("utf-8", errors="replace")
        for line in text.splitlines():
            low = line.lower()
            if "wfc_cutoff" in low or "ecutwfc" in low or "kinetic energy cutoff" in low:
                nums = re.findall(r"[\d]+\.?[\d]*", line)
                for n in nums:
                    val = float(n)
                    if 10 < val < 500:
                        return val
            if "z_valence" in low:
                break
    except Exception:
        pass
    return None


def suggest_ecutwfc_from_file(upf_filename: str, folder: str) -> Optional[float]:
    """Try to read ecutwfc hint from UPF file in a folder."""
    fp = os.path.join(folder, upf_filename)
    if not os.path.isfile(fp):
        return None
    try:
        with open(fp, "rb") as f:
            return suggest_ecutwfc_from_bytes(f.read(4096))
    except Exception:
        return None


# ─── Helper: build PWInput from session state ─────────────────────────────────

def build_pwinput() -> PWInput:
    """Assemble a PWInput object from current session state."""
    pw = PWInput()
    # CONTROL
    pw.control["calculation"] = ss.calc_type
    pw.control["prefix"] = ss.prefix
    pw.control["outdir"] = ss.outdir
    pw.control["restart_mode"] = ss.restart_mode
    pw.control["pseudo_dir"] = ss.pseudo_dir_for_input or "./pseudo"
    # SYSTEM
    pw.system["ibrav"] = 0
    pw.system["nat"] = ss.nat
    pw.system["ntyp"] = ss.ntyp
    pw.system["ecutwfc"] = ss.ecutwfc
    pw.system["ecutrho"] = ss.ecutrho
    pw.system["occupations"] = ss.occupations
    if ss.occupations == "smearing":
        pw.system["smearing"] = ss.smearing
        pw.system["degauss"] = ss.degauss
    else:
        pw.system.pop("smearing", None)
        pw.system.pop("degauss", None)
    if ss.nbnd > 0:
        pw.system["nbnd"] = ss.nbnd
    if ss.nspin in (1, 2):
        pw.system["nspin"] = ss.nspin
    if ss.noncolin:
        pw.system["noncolin"] = True
    if ss.lspinorb:
        pw.system["lspinorb"] = True
    if ss.lda_plus_u and ss.hubbard_u:
        pw.system["lda_plus_u"] = True
        for i, elem in enumerate(sorted(ss.elements)):
            u_val = ss.hubbard_u.get(elem, 0.0)
            if u_val > 0:
                pw.system[f"Hubbard_U({i+1})"] = u_val

    # ELECTRONS
    pw.electrons["conv_thr"] = ss.conv_thr
    pw.electrons["mixing_beta"] = ss.mixing_beta
    pw.electrons["electron_maxstep"] = ss.electron_maxstep
    pw.electrons["mixing_mode"] = ss.mixing_mode
    pw.electrons["diagonalization"] = ss.diagonalization

    # IONS
    if ss.calc_type in ("relax", "vc-relax", "md", "vc-md"):
        pw.ions["ion_dynamics"] = ss.ion_dynamics
        if ss.calc_type in ("md", "vc-md"):
            pw.ions["nstep"] = ss.nstep

    # CELL
    if ss.calc_type in ("vc-relax", "vc-md"):
        pw.cell["cell_dynamics"] = ss.cell_dynamics
        pw.cell["press_conv_thr"] = ss.press_conv_thr

    # Structure
    pw.cell_parameters = ss.cell_parameters
    pw.atomic_positions = [tuple(p) for p in ss.atomic_positions]
    pw.pos_units = ss.pos_units

    # Atomic species
    pw.atomic_species = []
    for elem in sorted(set(s for s, *_ in ss.atomic_positions)):
        pseudo = ss.pseudo_map.get(elem, f"{elem}.UPF")
        mass = get_atomic_mass(elem)
        pw.atomic_species.append((elem, mass, pseudo))

    # K-points
    ktype = ss.kpoints_type
    if ktype == "gamma":
        pw.kpoints = {"type": "gamma"}
    elif ktype == "automatic":
        pw.kpoints = {
            "type": "automatic",
            "mesh": [ss.kpoints_nx, ss.kpoints_ny, ss.kpoints_nz],
            "shift": [ss.kpoints_s0, ss.kpoints_s1, ss.kpoints_s2],
        }
    elif ktype == "crystal_b":
        if ss.kpoints_band_mode == "manual" and ss.kpoints_manual_text.strip():
            # Parse raw manual block and inject into PWInput
            raw_lines = [l for l in ss.kpoints_manual_text.strip().splitlines()
                         if l.strip() and not l.strip().lower().startswith("k_points")]
            pts = []
            try:
                declared_n = int(raw_lines[0].strip())
                for line in raw_lines[1:declared_n+1]:
                    parts = line.split()
                    pts.append((float(parts[0]), float(parts[1]), float(parts[2]), int(float(parts[3]))))
            except Exception:
                pts = []
        else:
            path_key = ss.kpoints_path_key
            kpath    = KPATHS.get(path_key, [])
            npts     = ss.kpoints_npoints
            pts = [(coords[0], coords[1], coords[2], npts if i < len(kpath)-1 else 1)
                   for i, (_, coords) in enumerate(kpath)]
        pw.kpoints = {"type": "crystal_b", "points": pts}

    return pw


# ─── Helper: structure from preset ───────────────────────────────────────────

def load_preset(name: str):
    p = PRESETS[name]
    ss.elements = list(p["elements"])
    ss.nat = p["nat"]
    ss.ntyp = p["ntyp"]
    ss.cell_parameters = [list(row) for row in p["cell"]]
    ss.atomic_positions = [list(pos) for pos in p["positions"]]
    ss.pos_units = "angstrom"
    ss.pseudo_map = {}
    _update_structure_summary()


def _update_structure_summary():
    """Recompute structure summary metrics."""
    import numpy as np
    if ss.cell_parameters and ss.atomic_positions:
        cell = np.array(ss.cell_parameters)
        a = float(np.linalg.norm(cell[0]))
        b = float(np.linalg.norm(cell[1]))
        c = float(np.linalg.norm(cell[2]))
        vol = float(abs(np.dot(cell[0], np.cross(cell[1], cell[2]))))
        elems = sorted(set(p[0] for p in ss.atomic_positions))
        ss.elements = elems
        ss.nat = len(ss.atomic_positions)
        ss.ntyp = len(elems)
        ss.structure_summary = {"a": a, "b": b, "c": c, "volume": vol}
    else:
        ss.structure_summary = {}


def _cell_params_text() -> str:
    if not ss.cell_parameters:
        return ""
    lines = []
    for row in ss.cell_parameters:
        lines.append(f"  {row[0]:14.9f}  {row[1]:14.9f}  {row[2]:14.9f}")
    return "\n".join(lines)


def _positions_text() -> str:
    lines = []
    for pos in ss.atomic_positions:
        sym = pos[0]
        x, y, z = float(pos[1]), float(pos[2]), float(pos[3])
        lines.append(f"  {sym:<4s}  {x:14.9f}  {y:14.9f}  {z:14.9f}")
    return "\n".join(lines)


def _parse_cell_text(text: str) -> Optional[List[List[float]]]:
    rows = []
    for line in text.strip().splitlines():
        nums = line.split()
        if len(nums) >= 3:
            try:
                rows.append([float(nums[0]), float(nums[1]), float(nums[2])])
            except ValueError:
                return None
    return rows if len(rows) == 3 else None


def _parse_positions_text(text: str) -> Optional[List[Tuple]]:
    positions = []
    for line in text.strip().splitlines():
        parts = line.split()
        if len(parts) >= 4:
            try:
                positions.append((parts[0], float(parts[1]), float(parts[2]), float(parts[3])))
            except ValueError:
                return None
    return positions if positions else None


def _check_qe_binary(name: str) -> bool:
    d = ss.get("qe_bin_dir", "").strip()
    if d:
        return os.path.isfile(os.path.join(d, name))
    # fallback: check PATH
    import shutil
    return shutil.which(name) is not None


def _archive_files() -> Dict[str, bytes]:
    """Return dict of {path_in_archive: bytes} for all downloadable files."""
    pw = build_pwinput()
    files: Dict[str, bytes] = {f"{ss.prefix}.in": pw.to_string().encode()}
    for fname, fbytes in ss.uploaded_pseudos.items():
        if ss.pseudo_map and fname in ss.pseudo_map.values():
            files[f"pseudo/{fname}"] = fbytes
    return files


def _build_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, data in _archive_files().items():
            zf.writestr(path, data)
    return buf.getvalue()


def _build_targz() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path, data in _archive_files().items():
            info = tarfile.TarInfo(name=path)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚛️ QE Input Generator")
    st.caption(f"Quantum ESPRESSO 7.x  ·  v{APP_VERSION}")
    with st.expander("📋 Changelog"):
        st.markdown(CHANGELOG)
    st.divider()

    for i, (num, label) in enumerate(STEPS):
        if IS_CLOUD and i >= 5:
            continue
        is_done    = i < ss.step
        is_current = i == ss.step
        prefix_str = "✅ " if is_done else ("▶ " if is_current else "   ")
        btn_style  = "primary" if is_current else "secondary"
        if st.button(
            f"{prefix_str}Step {num}: {label}",
            key=f"nav_btn_{i}",
            use_container_width=True,
            type=btn_style,
        ):
            ss.step = i
            st.rerun()

    st.divider()
    max_step = 4 if IS_CLOUD else len(STEPS) - 1
    col_b, col_n = st.columns(2)
    if col_b.button("Back", disabled=ss.step == 0, use_container_width=True):
        ss.step -= 1
        st.rerun()
    if col_n.button("Next", disabled=ss.step >= max_step, use_container_width=True):
        ss.step += 1
        st.rerun()

    if not IS_CLOUD:
        st.divider()
        with st.expander("⚙️ Settings", expanded=False):
            new_bin = st.text_input(
                "QE binary folder",
                value=ss.qe_bin_dir,
                placeholder="/path/to/qe/bin",
                help="Folder containing pw.x, ph.x, etc. Leave blank to use system PATH.",
                key="sidebar_qe_bin",
            )
            if new_bin != ss.qe_bin_dir:
                ss.qe_bin_dir = new_bin
                st.rerun()

        st.markdown("**QE binaries**")
        for bname in ["pw.x", "ph.x", "bands.x", "dos.x"]:
            ok = _check_qe_binary(bname)
            st.markdown(f"{'🟢' if ok else '🔴'} `{bname}`")

    if ss.elements:
        st.divider()
        st.markdown(f"**Elements:** `{' '.join(ss.elements)}`")
        st.markdown(f"**Calc:** `{ss.calc_type}`")
        if ss.nat:
            st.markdown(f"**Atoms:** {ss.nat}  |  **Types:** {ss.ntyp}")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 0 — Crystal Structure
# ═════════════════════════════════════════════════════════════════════════════
def step_structure():
    st.header("Step 1 · Crystal Structure")
    st.markdown(
        "Provide the crystal structure: upload a **CIF** file, choose a **preset**, "
        "or paste/edit structure text directly."
    )

    tab_upload, tab_preset, tab_manual = st.tabs([
        "Upload CIF", "Presets", "Manual Edit",
    ])

    # ── Upload CIF ────────────────────────────────────────────────────────────
    with tab_upload:
        f = st.file_uploader("Upload CIF file", type=["cif"])
        if f:
            raw = f.read()
            try:
                from pymatgen.io.cif import CifParser
                from pymatgen.io.pwscf import PWInput as PmgPWInput
                import tempfile, numpy as np
                with tempfile.NamedTemporaryFile(suffix=".cif", delete=False) as tmp:
                    tmp.write(raw)
                    tmp_path = tmp.name
                parser = CifParser(tmp_path)
                struct = parser.parse_structures(primitive=False)[0]
                os.unlink(tmp_path)

                cell = struct.lattice.matrix.tolist()
                positions = []
                for site in struct.sites:
                    positions.append((
                        str(site.specie.symbol),
                        float(site.coords[0]),
                        float(site.coords[1]),
                        float(site.coords[2]),
                    ))

                ss.cell_parameters = cell
                ss.atomic_positions = positions
                ss.pos_units = "angstrom"
                ss.pseudo_map = {}
                _update_structure_summary()
                st.success(f"CIF loaded: {struct.formula}, {len(positions)} atoms.")
            except Exception as e:
                st.error(f"CIF import failed: {e}")

    # ── Presets ───────────────────────────────────────────────────────────────
    with tab_preset:
        preset_name = st.selectbox("Choose a preset structure", list(PRESETS.keys()))
        p_info = PRESETS[preset_name]
        col1, col2 = st.columns([1, 3])
        if col1.button("Load Preset", type="primary"):
            load_preset(preset_name)
            st.success(f"Loaded: {preset_name}")
        col2.info(
            f"{p_info['desc']} | "
            f"**{p_info['nat']}** atoms | "
            f"Elements: `{', '.join(p_info['elements'])}`"
        )

    # ── Manual edit ───────────────────────────────────────────────────────────
    with tab_manual:
        st.markdown("**CELL_PARAMETERS (angstrom)** — one vector per row (3 floats each):")
        cell_default = _cell_params_text()
        cell_txt = st.text_area(
            "Cell vectors", value=cell_default, height=120,
            key="cell_text_area",
            help="Three rows, each with 3 numbers (ax ay az), (bx by bz), (cx cy cz) in Angstrom.",
        )

        st.markdown("**ATOMIC_POSITIONS (angstrom)** — symbol x y z per line:")
        pos_default = _positions_text()
        pos_txt = st.text_area(
            "Atomic positions", value=pos_default, height=200,
            key="pos_text_area",
            help="One atom per line: Element  x  y  z  (Angstrom).",
        )

        if st.button("Apply Manual Structure", type="primary"):
            new_cell = _parse_cell_text(cell_txt)
            new_pos  = _parse_positions_text(pos_txt)
            errs = []
            if new_cell is None:
                errs.append("Cell parameters: need exactly 3 rows with 3 numbers each.")
            if new_pos is None:
                errs.append("Atomic positions: need at least 1 row with symbol + 3 numbers.")
            if errs:
                for e in errs:
                    st.error(e)
            else:
                ss.cell_parameters = new_cell
                ss.atomic_positions = new_pos
                ss.pos_units = "angstrom"
                ss.pseudo_map = {}
                _update_structure_summary()
                st.success("Structure updated.")

    # ── Summary ───────────────────────────────────────────────────────────────
    st.divider()
    if ss.cell_parameters and ss.atomic_positions:
        summ = ss.structure_summary
        st.subheader("Structure Summary")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Atoms (nat)", ss.nat)
        c2.metric("Types (ntyp)", ss.ntyp)
        c3.metric("Volume (Å³)", f"{summ.get('volume', 0):.3f}")
        c4.metric("Elements", ", ".join(ss.elements) or "—")

        c1, c2, c3 = st.columns(3)
        c1.metric("a (Å)", f"{summ.get('a', 0):.4f}")
        c2.metric("b (Å)", f"{summ.get('b', 0):.4f}")
        c3.metric("c (Å)", f"{summ.get('c', 0):.4f}")

        with st.expander("Cell Parameters (Å)"):
            st.code(
                "CELL_PARAMETERS angstrom\n" + _cell_params_text(),
                language="text",
            )

        with st.expander("Atomic Positions (Å)"):
            st.code(
                f"ATOMIC_POSITIONS {{{ss.pos_units}}}\n" + _positions_text(),
                language="text",
            )
    else:
        st.info("No structure loaded yet — use one of the tabs above.")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 1 — Pseudopotentials
# ═════════════════════════════════════════════════════════════════════════════
def step_pseudopotentials():
    st.header("Step 2 · Pseudopotentials")
    st.markdown(
        "Upload your **UPF pseudopotential files** from your computer, "
        "or point to a folder on this machine that contains them."
    )

    if not ss.elements:
        st.warning("No structure loaded. Go to **Step 1** and load a crystal structure first.")
        return

    # ── Source selector ────────────────────────────────────────────────────────
    tab_upload, tab_folder = st.tabs(["📤 Upload UPF Files", "📁 Use Folder Path"])

    with tab_upload:
        st.markdown(
            "Upload one or more `.UPF` files from your computer. "
            "They will be matched to your structure elements automatically."
        )
        uploaded = st.file_uploader(
            "Select UPF pseudopotential files",
            type=["UPF", "upf"],
            accept_multiple_files=True,
            key="pseudo_uploader",
            help="Quantum ESPRESSO UPF format pseudopotential files.",
        )
        if uploaded:
            for f in uploaded:
                ss.uploaded_pseudos[f.name] = f.read()
            ss.pseudo_source = "upload"
            ss.pseudo_dir_for_input = "./pseudo"
            st.success(f"✅ {len(ss.uploaded_pseudos)} file(s) loaded: "
                       f"{', '.join(ss.uploaded_pseudos.keys())}")

        if ss.uploaded_pseudos:
            with st.expander(f"Uploaded files ({len(ss.uploaded_pseudos)})"):
                for fname in sorted(ss.uploaded_pseudos):
                    sz = len(ss.uploaded_pseudos[fname])
                    st.markdown(f"- `{fname}` ({sz//1024} KB)")
            if st.button("Clear all uploaded files", type="secondary"):
                ss.uploaded_pseudos = {}
                ss.pseudo_map = {}
                st.rerun()

    with tab_folder:
        st.markdown("If this machine has a pseudopotential library, enter its path:")
        folder_input = st.text_input(
            "Pseudopotential folder path",
            value=ss.pseudo_folder,
            placeholder="/path/to/pseudopotentials",
            key="pseudo_folder_input",
            help="Folder containing UPF files on this machine.",
        )
        ss.pseudo_folder = folder_input.strip()
        if ss.pseudo_folder:
            if os.path.isdir(ss.pseudo_folder):
                n = len(glob.glob(os.path.join(ss.pseudo_folder, "*.UPF"))
                        + glob.glob(os.path.join(ss.pseudo_folder, "*.upf")))
                st.success(f"✅ Folder found — {n} UPF files detected.")
                ss.pseudo_source = "folder"
                ss.pseudo_dir_for_input = ss.pseudo_folder
            else:
                st.error("Folder not found. Check the path.")

    # ── pseudo_dir written into the input file ─────────────────────────────────
    st.divider()
    pseudo_dir_val = st.text_input(
        "pseudo_dir (written into input file)",
        value=ss.pseudo_dir_for_input,
        key="pseudo_dir_input",
        help=(
            "This path will appear as pseudo_dir in &CONTROL. "
            "When you run QE, this folder must contain the UPF files. "
            "If you uploaded files and downloaded the ZIP, they are in a pseudo/ subfolder."
        ),
    )
    ss.pseudo_dir_for_input = pseudo_dir_val

    # ── Per-element selector ───────────────────────────────────────────────────
    st.divider()
    st.subheader("Select pseudopotential for each element")

    if ss.pseudo_source == "upload":
        avail_source = {elem: find_pseudos_uploaded(elem) for elem in ss.elements}
    else:
        avail_source = {
            elem: find_pseudos_folder(elem, ss.pseudo_folder) for elem in ss.elements
        }

    pseudo_map: Dict[str, str] = dict(ss.pseudo_map)
    ecutwfc_hints: List[float] = []
    all_found = True

    for elem in sorted(set(p[0] for p in ss.atomic_positions)):
        avail = avail_source.get(elem, [])
        if not avail:
            st.error(
                f"❌ No UPF file found for **{elem}**. "
                "Upload the pseudopotential file using the tab above."
            )
            all_found = False
            continue

        current = pseudo_map.get(elem, avail[0])
        if current not in avail:
            current = avail[0]

        c1, c2 = st.columns([1, 3])
        c1.markdown(f"**{elem}**")
        chosen = c2.selectbox(
            f"Pseudo for {elem}", avail,
            index=avail.index(current),
            key=f"pseudo_{elem}",
            label_visibility="collapsed",
        )
        pseudo_map[elem] = chosen

        # ecutwfc hint
        if ss.pseudo_source == "upload" and chosen in ss.uploaded_pseudos:
            hint = suggest_ecutwfc_from_bytes(ss.uploaded_pseudos[chosen])
        elif ss.pseudo_source == "folder":
            hint = suggest_ecutwfc_from_file(chosen, ss.pseudo_folder)
        else:
            hint = None
        if hint:
            ecutwfc_hints.append(hint)
            st.caption(f"  💡 ecutwfc hint from UPF: {hint:.0f} Ry")

    ss.pseudo_map = pseudo_map

    # ── Cutoff suggestion ──────────────────────────────────────────────────────
    st.divider()
    st.subheader("Cutoff Energy")

    suggested_wfc = max(ecutwfc_hints) if ecutwfc_hints else 60.0
    suggested_rho = suggested_wfc * 8
    if ecutwfc_hints:
        st.success(
            f"💡 **Suggested ecutwfc = {suggested_wfc:.0f} Ry** (from UPF file headers)  |  "
            f"ecutrho = {suggested_rho:.0f} Ry"
        )
    else:
        st.info(
            f"No cutoff hint found in UPF files. Using default: "
            f"**ecutwfc = {suggested_wfc:.0f} Ry**, ecutrho = {suggested_rho:.0f} Ry. "
            "Increase to 80–100 Ry for O, N, F."
        )

    col1, col2 = st.columns(2)
    with col1:
        ss.ecutwfc = st.number_input(
            "ecutwfc (Ry)", min_value=10.0, max_value=500.0,
            value=float(ss.ecutwfc), step=5.0, key="ecutwfc_input",
        )
    with col2:
        ss.ecutrho = st.number_input(
            "ecutrho (Ry)", min_value=40.0, max_value=4000.0,
            value=float(ss.ecutrho), step=10.0, key="ecutrho_input",
            help="4× ecutwfc for norm-conserving, 8–12× for ultrasoft/PAW.",
        )

    if st.button(f"Apply suggested values (ecutwfc={suggested_wfc:.0f}, ecutrho={suggested_rho:.0f} Ry)"):
        ss.ecutwfc = suggested_wfc
        ss.ecutrho = suggested_rho
        st.success("Applied.")

    if not all_found:
        st.error("Upload missing pseudopotential files before continuing.")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 2 — CONTROL + SYSTEM
# ═════════════════════════════════════════════════════════════════════════════
def step_control_system():
    st.header("Step 3 · CONTROL + SYSTEM Namelists")

    # Calculation type
    calc_type = st.selectbox(
        "Calculation type",
        CALC_TYPES,
        index=CALC_TYPES.index(ss.calc_type) if ss.calc_type in CALC_TYPES else 0,
        key="calc_type_sel",
        help=(
            "scf: self-consistent field  |  nscf: non-self-consistent (for DOS/bands post-processing)\n"
            "bands: band structure  |  relax: atomic relaxation (fixed cell)\n"
            "vc-relax: variable-cell relaxation  |  md: molecular dynamics\n"
            "vc-md: variable-cell MD"
        ),
    )
    ss.calc_type = calc_type

    calc_descs = {
        "scf": "Self-consistent field — computes ground-state electron density and total energy.",
        "nscf": "Non-SCF — computes eigenvalues at fixed charge density (for DOS, PDOS post-processing).",
        "bands": "Band structure — computes eigenvalues along a k-path. Requires prior SCF charge density.",
        "relax": "Ionic relaxation (fixed cell) — minimises forces on atoms using BFGS or damped dynamics.",
        "vc-relax": "Variable-cell relaxation — minimises forces and stress tensor simultaneously.",
        "md": "Born-Oppenheimer molecular dynamics at fixed cell volume.",
        "vc-md": "Variable-cell molecular dynamics — allows cell to evolve during MD.",
    }
    st.info(f"**{calc_type}** — {calc_descs.get(calc_type, '')}")

    if calc_type in ("nscf", "bands"):
        st.warning(
            "Run an **scf** calculation first and keep the same `outdir` and `prefix`. "
            "QE reuses the charge density from the SCF step."
        )

    st.divider()

    # ── &CONTROL ─────────────────────────────────────────────────────────────
    with st.expander("&CONTROL", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            ss.prefix = st.text_input(
                "prefix", value=ss.prefix, key="ctrl_prefix",
                help="Label used for output files (e.g. pwscf → pwscf.out, pwscf.xml).",
            )
            ss.outdir = st.text_input(
                "outdir", value=ss.outdir, key="ctrl_outdir",
                help="Directory for temporary files and charge density.",
            )
        with c2:
            ss.restart_mode = st.selectbox(
                "restart_mode",
                ["from_scratch", "restart"],
                index=0 if ss.restart_mode == "from_scratch" else 1,
                key="ctrl_restart",
                help="from_scratch: start new calculation  |  restart: continue from checkpoint.",
            )
            st.text_input(
                "pseudo_dir (set in Step 2)",
                value=ss.pseudo_dir_for_input or "./pseudo",
                disabled=True,
                help="Set this path in Step 2 · Pseudopotentials.",
            )

        if calc_type in ("relax", "vc-relax"):
            st.info(
                "For relaxations, QE writes the optimised structure to "
                "`{outdir}/{prefix}.out`. The final geometry can be extracted with `grep -A nat 'ATOMIC_POSITIONS'`."
            )

    # ── &SYSTEM ───────────────────────────────────────────────────────────────
    with st.expander("&SYSTEM — Basic", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            occ = st.selectbox(
                "occupations",
                OCCUPATION_TYPES,
                index=OCCUPATION_TYPES.index(ss.occupations) if ss.occupations in OCCUPATION_TYPES else 0,
                key="sys_occ",
                help=(
                    "smearing: metallic broadening (required for metals)\n"
                    "fixed: insulator/semiconductor (integer occupations)\n"
                    "tetrahedra: accurate for DOS but requires many k-points"
                ),
            )
            ss.occupations = occ
        with c2:
            if occ == "smearing":
                smear = st.selectbox(
                    "smearing",
                    SMEARING_TYPES,
                    index=SMEARING_TYPES.index(ss.smearing) if ss.smearing in SMEARING_TYPES else 1,
                    key="sys_smearing",
                    help=(
                        "methfessel-paxton: recommended for metals\n"
                        "gaussian: safe for semiconductors/insulators\n"
                        "fermi-dirac: physically correct but slower convergence"
                    ),
                )
                ss.smearing = smear
        with c3:
            if occ == "smearing":
                dg = st.number_input(
                    "degauss (Ry)", value=float(ss.degauss),
                    min_value=0.001, max_value=0.5, step=0.005,
                    format="%.4f", key="sys_degauss",
                    help="Smearing width in Rydberg. 0.01–0.02 Ry for metals, 0.001–0.005 Ry for semiconductors.",
                )
                ss.degauss = dg

        if occ == "smearing":
            if ss.smearing == "methfessel-paxton":
                st.info(
                    "Methfessel-Paxton smearing is the standard choice for metals. "
                    "Use degauss = 0.01–0.02 Ry. Check that entropy contribution is < 1 meV/atom."
                )
            elif ss.smearing == "gaussian":
                st.info(
                    "Gaussian smearing is safe for semiconductors. Keep degauss small (0.005–0.01 Ry)."
                )
        elif occ == "fixed":
            st.info(
                "Fixed occupations: suitable for insulators and semiconductors with a clear gap. "
                "Do NOT use for metals — QE will fail to converge."
            )
        elif occ.startswith("tetrahedra"):
            st.info(
                "Tetrahedron method: very accurate for DOS. Requires a dense, uniform k-mesh. "
                "Not suitable for relaxations or sparse k-grids."
            )

        nbnd = st.number_input(
            "nbnd (0 = auto)", value=int(ss.nbnd), min_value=0, max_value=2000, step=1,
            key="sys_nbnd",
            help="Number of bands. 0 = use QE default (half the number of electrons + a few). "
                 "Increase for nscf/DOS calculations to include empty states.",
        )
        ss.nbnd = nbnd

    # ── Spin settings ─────────────────────────────────────────────────────────
    with st.expander("Spin & Magnetism"):
        c1, c2 = st.columns(2)
        with c1:
            nspin = st.selectbox(
                "nspin",
                [1, 2],
                index=0 if ss.nspin == 1 else 1,
                key="sys_nspin",
                help="1: non-spin-polarised (default)  |  2: collinear spin-polarised (ferromagnetic/antiferromagnetic).",
            )
            ss.nspin = nspin
            if nspin == 2:
                st.info(
                    "Spin-polarised calculation. Set starting_magnetization in ATOMIC_SPECIES "
                    "to break symmetry. Typical values: Fe≈0.5, Co≈0.4, Ni≈0.3 (in units of total magnetisation)."
                )
        with c2:
            noncolin = st.checkbox(
                "noncolin (non-collinear)", value=ss.noncolin, key="sys_noncolin",
                help="Enable non-collinear magnetism. Required for spin-orbit coupling calculations.",
            )
            ss.noncolin = noncolin
            lspinorb = st.checkbox(
                "lspinorb (spin-orbit)", value=ss.lspinorb, key="sys_lspinorb",
                help="Include spin-orbit coupling. Requires fully-relativistic pseudopotentials and noncolin=True.",
            )
            ss.lspinorb = lspinorb
            if lspinorb and not noncolin:
                st.warning("lspinorb requires noncolin = True.")
            if lspinorb:
                st.warning(
                    "Spin-orbit coupling requires **fully-relativistic** pseudopotentials "
                    "(look for `_rel` or `fr` in the filename)."
                )

    # ── Hubbard U ─────────────────────────────────────────────────────────────
    with st.expander("DFT+U (Hubbard U)"):
        lda_plus_u = st.checkbox(
            "lda_plus_u", value=ss.lda_plus_u, key="sys_ldapu",
            help="Enable DFT+U (LDA+U/GGA+U) correction. Recommended for strongly-correlated d/f systems.",
        )
        ss.lda_plus_u = lda_plus_u
        if lda_plus_u:
            if not ss.elements:
                st.warning("Load a structure first to configure Hubbard U per element.")
            else:
                st.markdown(
                    "Set Hubbard U values (eV) for each element. Use 0 for non-correlated elements."
                )
                hubbard_u: Dict[str, float] = dict(ss.hubbard_u)
                for elem in sorted(ss.elements):
                    u_val = st.number_input(
                        f"Hubbard U for {elem} (eV)",
                        value=float(hubbard_u.get(elem, 0.0)),
                        min_value=0.0, max_value=20.0, step=0.5,
                        key=f"hub_u_{elem}",
                        help=f"U parameter for {elem}. Typical values: Fe 2–6 eV, Ti 3–5 eV, Mn 2–5 eV. Use 0 to skip.",
                    )
                    hubbard_u[elem] = u_val
                ss.hubbard_u = hubbard_u
                st.info(
                    "DFT+U applies a Hubbard correction to localised d or f orbitals. "
                    "Common values: Fe(d)=4 eV, Ni(d)=6 eV, Ti(d)=3 eV, Ce(f)=5 eV. "
                    "Optimise U by comparing with experimental band gap or magnetic moment."
                )
        else:
            st.caption("Enable lda_plus_u above to configure Hubbard U parameters.")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 3 — ELECTRONS + IONS + CELL
# ═════════════════════════════════════════════════════════════════════════════
def step_electrons_ions_cell():
    st.header("Step 4 · ELECTRONS + IONS + CELL Namelists")
    calc_type = ss.calc_type

    # ── &ELECTRONS ────────────────────────────────────────────────────────────
    with st.expander("&ELECTRONS", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            conv_thr = st.number_input(
                "conv_thr (Ry)", value=float(ss.conv_thr),
                min_value=1e-14, max_value=1e-4, step=None,
                format="%.2e", key="elec_conv_thr",
                help=(
                    "SCF convergence threshold in Rydberg. "
                    "1e-8 Ry is standard for total energy; 1e-10 Ry for phonons; "
                    "1e-6 Ry is acceptable for pre-relaxation."
                ),
            )
            ss.conv_thr = conv_thr

            mixing_beta = st.number_input(
                "mixing_beta", value=float(ss.mixing_beta),
                min_value=0.01, max_value=1.0, step=0.05,
                format="%.3f", key="elec_mixing_beta",
                help=(
                    "Linear mixing parameter. 0.3–0.7 is typical. "
                    "Reduce to 0.1–0.2 for difficult metallic or magnetic systems. "
                    "Too large → oscillations; too small → slow convergence."
                ),
            )
            ss.mixing_beta = mixing_beta

        with c2:
            electron_maxstep = st.number_input(
                "electron_maxstep", value=int(ss.electron_maxstep),
                min_value=10, max_value=2000, step=10,
                key="elec_maxstep",
                help="Maximum number of SCF iterations. Increase if convergence is not reached.",
            )
            ss.electron_maxstep = electron_maxstep

            mixing_mode = st.selectbox(
                "mixing_mode",
                MIXING_MODES,
                index=MIXING_MODES.index(ss.mixing_mode) if ss.mixing_mode in MIXING_MODES else 0,
                key="elec_mixing_mode",
                help=(
                    "plain: simple linear mixing (robust, works everywhere)\n"
                    "TF: Thomas-Fermi mixing (better for metals)\n"
                    "local-TF: spatially varying TF (for inhomogeneous systems)"
                ),
            )
            ss.mixing_mode = mixing_mode

            diag = st.selectbox(
                "diagonalization",
                DIAG_TYPES,
                index=DIAG_TYPES.index(ss.diagonalization) if ss.diagonalization in DIAG_TYPES else 0,
                key="elec_diag",
                help=(
                    "david: Davidson algorithm (fast, default for most systems)\n"
                    "cg: conjugate-gradient (stable but slower)\n"
                    "rmm-davidson: RMM-DIIS with Davidson for problematic cases"
                ),
            )
            ss.diagonalization = diag

        if diag == "david":
            st.info(
                "Davidson diagonalisation is the default and fastest for most systems. "
                "If SCF oscillates, try **cg** or reduce mixing_beta."
            )
        elif diag == "cg":
            st.info(
                "CG diagonalisation is more robust but slower. "
                "Useful for poorly converging metallic systems."
            )

    # ── &IONS ─────────────────────────────────────────────────────────────────
    show_ions = calc_type in ("relax", "vc-relax", "md", "vc-md")
    with st.expander("&IONS", expanded=show_ions):
        if not show_ions:
            st.caption(
                "IONS namelist is only active for: relax, vc-relax, md, vc-md. "
                f"Current calculation type is **{calc_type}**."
            )
        else:
            c1, c2 = st.columns(2)
            with c1:
                ion_dyn_opts = ION_DYNAMICS
                ion_dyn = st.selectbox(
                    "ion_dynamics",
                    ion_dyn_opts,
                    index=ion_dyn_opts.index(ss.ion_dynamics) if ss.ion_dynamics in ion_dyn_opts else 0,
                    key="ions_dyn",
                    help=(
                        "bfgs: quasi-Newton (recommended for relax/vc-relax)\n"
                        "damp: damped dynamics\n"
                        "verlet: Verlet MD (for md)\n"
                        "langevin: Langevin thermostat (for NVT MD)\n"
                        "fire: FIRE algorithm (good for large systems)"
                    ),
                )
                ss.ion_dynamics = ion_dyn

            with c2:
                if calc_type in ("md", "vc-md"):
                    nstep = st.number_input(
                        "nstep (MD steps)", value=int(ss.nstep),
                        min_value=1, max_value=100000, step=100,
                        key="ions_nstep",
                        help="Number of ionic/MD steps.",
                    )
                    ss.nstep = nstep

            if ion_dyn == "bfgs":
                st.info(
                    "BFGS is the recommended algorithm for structural relaxations. "
                    "It converges rapidly for well-behaved systems (typically 20–100 steps)."
                )
            elif ion_dyn in ("verlet", "langevin"):
                st.info(
                    "MD integration. Set dt (timestep) in IONS namelist manually if needed. "
                    "Default timestep is 20 a.u. (~0.5 fs)."
                )

    # ── &CELL ─────────────────────────────────────────────────────────────────
    show_cell = calc_type in ("vc-relax", "vc-md")
    with st.expander("&CELL", expanded=show_cell):
        if not show_cell:
            st.caption(
                "CELL namelist is only active for: vc-relax, vc-md. "
                f"Current calculation type is **{calc_type}**."
            )
        else:
            c1, c2 = st.columns(2)
            with c1:
                cell_dyn_opts = CELL_DYNAMICS
                cell_dyn = st.selectbox(
                    "cell_dynamics",
                    cell_dyn_opts,
                    index=cell_dyn_opts.index(ss.cell_dynamics) if ss.cell_dynamics in cell_dyn_opts else 0,
                    key="cell_dyn",
                    help=(
                        "bfgs: quasi-Newton (recommended for vc-relax)\n"
                        "damp-pr: damped Parrinello-Rahman dynamics\n"
                        "pr: Parrinello-Rahman barostat (for vc-md)"
                    ),
                )
                ss.cell_dynamics = cell_dyn
            with c2:
                press_conv_thr = st.number_input(
                    "press_conv_thr (kbar)", value=float(ss.press_conv_thr),
                    min_value=0.01, max_value=100.0, step=0.1,
                    format="%.2f", key="cell_press_thr",
                    help=(
                        "Pressure convergence threshold in kbar. "
                        "0.5 kbar is standard; use 0.1 kbar for high-precision work."
                    ),
                )
                ss.press_conv_thr = press_conv_thr

            st.info(
                "Variable-cell relaxation optimises both atomic positions and the unit cell shape/volume. "
                "BFGS cell_dynamics is recommended. "
                "If the cell becomes unphysical, restart with a better initial guess."
            )


# ═════════════════════════════════════════════════════════════════════════════
# STEP 4 — K-Points + Download
# ═════════════════════════════════════════════════════════════════════════════
def step_kpoints_download():
    st.header("Step 5 · K-Points + Download")

    # ── K-point type ─────────────────────────────────────────────────────────
    ktype_opts = ["automatic", "gamma", "crystal_b"]
    ktype_labels = {
        "automatic": "Automatic mesh (nx ny nz + shift)",
        "gamma":     "Gamma-only (single k-point)",
        "crystal_b": "Line mode (band structure path)",
    }
    ktype = st.radio(
        "K-point sampling type",
        ktype_opts,
        index=ktype_opts.index(ss.kpoints_type) if ss.kpoints_type in ktype_opts else 0,
        format_func=lambda x: ktype_labels[x],
        horizontal=True,
        key="ktype_radio",
    )
    ss.kpoints_type = ktype

    st.divider()

    if ktype == "automatic":
        st.markdown(
            "**Suggested meshes:** 4×4×4 (coarse), 6×6×6 (standard), "
            "8×8×8 (accurate), 12×12×12 (high-precision). "
            "For 2D slabs: set **nz=1**. For molecules: use Gamma-only."
        )
        c1, c2, c3 = st.columns(3)
        nx = c1.number_input("nx", 1, 30, int(ss.kpoints_nx), key="kp_nx")
        ny = c2.number_input("ny", 1, 30, int(ss.kpoints_ny), key="kp_ny")
        nz = c3.number_input("nz", 1, 30, int(ss.kpoints_nz), key="kp_nz")
        ss.kpoints_nx, ss.kpoints_ny, ss.kpoints_nz = int(nx), int(ny), int(nz)

        c4, c5, c6 = st.columns(3)
        s0 = c4.number_input("shift x", 0, 1, int(ss.kpoints_s0), key="kp_s0")
        s1 = c5.number_input("shift y", 0, 1, int(ss.kpoints_s1), key="kp_s1")
        s2 = c6.number_input("shift z", 0, 1, int(ss.kpoints_s2), key="kp_s2")
        ss.kpoints_s0, ss.kpoints_s1, ss.kpoints_s2 = int(s0), int(s1), int(s2)

        kpoints_preview = (
            "K_POINTS automatic\n"
            f"  {int(nx)} {int(ny)} {int(nz)}  {int(s0)} {int(s1)} {int(s2)}"
        )
        st.info(
            "Shift of 0 0 0 includes Gamma point (recommended for most calculations). "
            "Shift 1 1 1 gives a Monkhorst-Pack mesh shifted away from Gamma."
        )

    elif ktype == "gamma":
        kpoints_preview = "K_POINTS gamma"
        st.info(
            "Single Gamma k-point: use for large supercells (50+ atoms), molecules in a box, "
            "or quick pre-tests. Not suitable for band structure or converged DOS."
        )

    else:  # crystal_b
        st.info(
            "💡 Band structure k-path. **Prerequisites**: run an **scf** calculation first "
            "to generate the charge density, then use `calculation = bands` and `restart_mode = restart`."
        )

        band_tab_preset, band_tab_manual = st.tabs([
            "🗺️ Preset High-Symmetry Path", "✏️ Manual K-Points",
        ])

        with band_tab_preset:
            path_keys = list(KPATHS.keys())
            path_key = st.selectbox(
                "Crystal system / k-path",
                path_keys,
                index=path_keys.index(ss.kpoints_path_key) if ss.kpoints_path_key in path_keys else 0,
                key="kpath_sel",
            )
            ss.kpoints_path_key = path_key
            kpath = KPATHS[path_key]

            npts = st.slider(
                "K-points per segment", 10, 80, int(ss.kpoints_npoints), 5, key="kpts_slider",
            )
            ss.kpoints_npoints = npts

            path_label = " → ".join(lbl for lbl, _ in kpath)
            st.success(f"**Path:** {path_label}  ·  {npts} pts/segment")

            # Build block
            preset_lines = [f"K_POINTS crystal_b", f"  {len(kpath)}"]
            for i, (lbl, coords) in enumerate(kpath):
                n = npts if i < len(kpath) - 1 else 1
                preset_lines.append(
                    f"  {coords[0]:.6f}  {coords[1]:.6f}  {coords[2]:.6f}  {n}  ! {lbl}"
                )
            preset_block = "\n".join(preset_lines)

            with st.expander("K-point coordinates"):
                rows = [
                    {"Label": lbl, "kx": f"{k[0]:.6f}", "ky": f"{k[1]:.6f}", "kz": f"{k[2]:.6f}"}
                    for lbl, k in kpath
                ]
                st.table(rows)

            if st.button("Load preset into manual editor →", key="load_to_manual"):
                ss.kpoints_manual_text = preset_block
                ss.kpoints_band_mode = "manual"
                st.info("Preset loaded into the Manual K-Points tab — switch there to edit.")

            if ss.kpoints_band_mode != "manual":
                ss.kpoints_band_mode = "preset"
                kpoints_preview = preset_block

        with band_tab_manual:
            st.markdown(
                "Write your own `K_POINTS crystal_b` block. "
                "Format: **kx ky kz npoints** per line (fractional reciprocal coordinates). "
                "The last point must have **npoints = 1**."
            )
            st.code(
                "K_POINTS crystal_b\n"
                "  5\n"
                "  0.000000  0.000000  0.000000  20  ! Gamma\n"
                "  0.500000  0.000000  0.500000  20  ! X\n"
                "  0.500000  0.250000  0.750000  20  ! W\n"
                "  0.500000  0.500000  0.500000  20  ! L\n"
                "  0.000000  0.000000  0.000000   1  ! Gamma",
                language="text",
            )

            manual_txt = st.text_area(
                "K_POINTS block",
                value=ss.kpoints_manual_text or (
                    "K_POINTS crystal_b\n"
                    "  5\n"
                    "  0.000000  0.000000  0.000000  20  ! Gamma\n"
                    "  0.500000  0.000000  0.500000  20  ! X\n"
                    "  0.500000  0.250000  0.750000  20  ! W\n"
                    "  0.500000  0.500000  0.500000  20  ! L\n"
                    "  0.000000  0.000000  0.000000   1  ! Gamma"
                ),
                height=220,
                key="kpoints_manual_area",
                help="Paste or type your full K_POINTS block here.",
            )

            # Validate: count header vs actual lines
            parse_ok = True
            parse_msg = ""
            try:
                mlines = [l for l in manual_txt.strip().splitlines() if l.strip()]
                if not mlines[0].strip().lower().startswith("k_points"):
                    parse_ok = False
                    parse_msg = "First line must be `K_POINTS crystal_b`"
                else:
                    declared_n = int(mlines[1].strip())
                    kpt_lines  = [l for l in mlines[2:] if l.strip() and not l.strip().startswith("!")]
                    if len(kpt_lines) != declared_n:
                        parse_ok = False
                        parse_msg = f"Header says {declared_n} points but {len(kpt_lines)} lines found."
            except Exception as ex:
                parse_ok = False
                parse_msg = f"Parse error: {ex}"

            if parse_ok:
                st.success(f"✅ Valid — {declared_n} k-points defined.")
            else:
                st.error(f"❌ {parse_msg}")

            if st.button("Use this manual block", type="primary", key="apply_manual_kpts"):
                ss.kpoints_manual_text = manual_txt
                ss.kpoints_band_mode = "manual"
                st.success("Manual k-points will be used in the input file.")

            if ss.kpoints_band_mode == "manual":
                kpoints_preview = ss.kpoints_manual_text or preset_block
            else:
                kpoints_preview = preset_block

        # Resolve which block to use
        if ss.kpoints_band_mode == "manual" and ss.kpoints_manual_text.strip():
            kpoints_preview = ss.kpoints_manual_text
        else:
            kpoints_preview = preset_block

    st.divider()
    st.subheader("K-Points Preview")
    st.code(kpoints_preview, language="text")

    # ── Full input file preview ───────────────────────────────────────────────
    st.divider()
    st.subheader("Full Input File Preview")
    has_structure = bool(ss.cell_parameters and ss.atomic_positions and ss.elements)
    has_pseudos   = bool(ss.pseudo_map)

    if not has_structure:
        st.warning("Load a structure in Step 1 before previewing the input file.")
    elif not has_pseudos:
        st.warning("Select pseudopotentials in Step 2 before previewing the input file.")
    else:
        try:
            pw = build_pwinput()
            input_text = pw.to_string()
            st.code(input_text, language="text")

            # ── Downloads ────────────────────────────────────────────────────
            st.divider()
            st.subheader("Download")
            col1, col2, col3 = st.columns(3)
            col1.download_button(
                "⬇️ Input file (.in)",
                input_text,
                file_name=f"{ss.prefix}.in",
                mime="text/plain",
                type="primary",
                help="Download only the pw.x input file.",
            )
            col2.download_button(
                "⬇️ All as ZIP",
                _build_zip(),
                file_name=f"{ss.prefix}_inputs.zip",
                mime="application/zip",
                help="Input file + pseudopotentials bundled in a ZIP archive.",
            )
            col3.download_button(
                "⬇️ All as tar.gz",
                _build_targz(),
                file_name=f"{ss.prefix}_inputs.tar.gz",
                mime="application/gzip",
                help="Input file + pseudopotentials bundled in a tar.gz archive (common on Linux/HPC).",
            )
        except Exception as e:
            st.error(f"Input file generation error: {e}")
            return

    # ── Run QE ────────────────────────────────────────────────────────────────
    st.divider()

    if IS_CLOUD:
        st.info(
            "Running QE is not available in the cloud deployment. "
            "Download the input files above and run pw.x on your local machine or HPC cluster."
        )
        st.markdown(
            """
**Example command:**
```bash
mpirun -np 4 pw.x -in pwscf.in > pwscf.out
```
Or submit via SLURM:
```bash
#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=16
module load quantum-espresso
mpirun -np 16 pw.x -in pwscf.in > pwscf.out
```
"""
        )
        return

    st.subheader("Run QE Locally")

    c1, c2, c3 = st.columns(3)
    with c1:
        qe_bin = st.text_input(
            "QE binary folder",
            value=ss.qe_bin_dir,
            placeholder="/path/to/qe/bin  (blank = use PATH)",
            key="run_qe_bin",
            help="Folder containing pw.x. Leave blank if pw.x is already in your system PATH.",
        )
        ss.qe_bin_dir = qe_bin.strip()
    with c2:
        work_dir = st.text_input(
            "Working directory",
            value=ss.work_dir,
            placeholder="./qe_run",
            key="wd_input",
            help="Folder where input/output files will be written.",
        )
        ss.work_dir = work_dir.strip() or "./qe_run"
    with c3:
        nproc = st.number_input(
            "MPI processes", 1, 128, int(ss.qe_nproc), key="np_input",
            help="Number of MPI processes. Use 1 for serial run.",
        )
        ss.qe_nproc = int(nproc)

    # Resolve pw.x path
    if ss.qe_bin_dir:
        pw_exe = os.path.join(ss.qe_bin_dir, "pw.x")
    else:
        import shutil
        pw_exe = shutil.which("pw.x") or "pw.x"
    pw_available = os.path.isfile(pw_exe)

    if not pw_available:
        st.warning(
            f"pw.x not found at `{pw_exe}`. "
            "Enter the correct QE binary folder above, or download the input files and run manually."
        )

    if not has_structure or not has_pseudos:
        st.warning("Complete Steps 1–2 before running QE.")
        return

    col_w, col_r, col_s = st.columns(3)

    if col_w.button("Write input files", type="secondary"):
        try:
            os.makedirs(ss.work_dir, exist_ok=True)
            pw = build_pwinput()
            in_path = os.path.join(ss.work_dir, f"{ss.prefix}.in")
            pw.save(in_path)
            st.success(f"Input file written: `{in_path}`")
        except Exception as e:
            st.error(f"Write error: {e}")

    run_disabled = ss.job_running
    if col_r.button("Run pw.x", type="primary", disabled=run_disabled):
        try:
            os.makedirs(ss.work_dir, exist_ok=True)
            # Write uploaded pseudos into work_dir/pseudo/
            if ss.uploaded_pseudos and ss.pseudo_source == "upload":
                pseudo_subdir = os.path.join(ss.work_dir, "pseudo")
                os.makedirs(pseudo_subdir, exist_ok=True)
                for fname, fbytes in ss.uploaded_pseudos.items():
                    with open(os.path.join(pseudo_subdir, fname), "wb") as pf:
                        pf.write(fbytes)
                ss.pseudo_dir_for_input = pseudo_subdir

            pw = build_pwinput()
            in_file  = f"{ss.prefix}.in"
            out_file = f"{ss.prefix}.out"
            pw.save(os.path.join(ss.work_dir, in_file))

            runner = QERunner(
                calc_dir    = ss.work_dir,
                input_file  = in_file,
                output_file = out_file,
                executable  = pw_exe,
                nproc       = ss.qe_nproc,
            )
            ss.job_output_lines = []
            ss.output_file = os.path.join(ss.work_dir, out_file)

            def _on_line(line):
                ss.job_output_lines.append(line.rstrip())
                if len(ss.job_output_lines) > 200:
                    ss.job_output_lines = ss.job_output_lines[-200:]

            def _on_finish(returncode, error):
                ss.job_running = False
                ss.job_done = True

            ok = runner.start(on_line=_on_line, on_finish=_on_finish)
            if ok:
                ss.job_running = True
                ss.job_done = False
                st.success(f"pw.x started (PID {runner.pid})")
            else:
                st.error("Failed to start pw.x.")
        except Exception as e:
            st.error(f"Launch error: {e}")

    if col_s.button("Stop", disabled=not ss.job_running):
        ss.job_running = False
        ss.job_done = True
        st.warning("Stop requested. The process may still finish its current step.")

    # Live output
    if ss.job_running:
        st.info("pw.x is running — page auto-refreshes every 3 s")
        if ss.job_output_lines:
            tail = "\n".join(ss.job_output_lines[-30:])
            st.code(tail, language="text")
        else:
            st.caption("Waiting for output...")
        time.sleep(3)
        st.rerun()
    elif ss.job_done:
        st.success("Job finished. Go to **Step 6** to view results.")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 5 — Results
# ═════════════════════════════════════════════════════════════════════════════
def step_results():
    st.header("Step 6 · Results")

    if IS_CLOUD:
        st.info(
            "Results parsing is not available in the cloud version. "
            "Download the output file and parse it locally, or use the QE GUI locally."
        )
        return

    rdir = st.text_input(
        "Results directory", value=ss.work_dir, key="res_dir",
        help="Directory containing QE output files.",
    )
    prefix_res = st.text_input(
        "Prefix", value=ss.prefix, key="res_prefix",
        help="Same prefix used in CONTROL namelist.",
    )
    out_path = os.path.join(rdir, f"{prefix_res}.out")

    if not os.path.isdir(rdir):
        st.warning("Directory does not exist.")
        return

    # Output file status
    st.subheader("Output Files")
    out_files = [f"{prefix_res}.out", f"{prefix_res}.xml",
                 f"{prefix_res}.dos", f"{prefix_res}.dat"]
    cols = st.columns(4)
    for i, fn in enumerate(out_files):
        fp = os.path.join(rdir, fn)
        cols[i % 4].markdown(f"{'✅' if os.path.isfile(fp) else '⬜'} `{fn}`")

    st.divider()

    if st.button("Parse output file", type="primary"):
        if not os.path.isfile(out_path):
            st.warning(f"Output file not found: `{out_path}`")
        else:
            res = parse_scf_output(out_path)

            # Metrics
            c1, c2, c3, c4 = st.columns(4)
            energy = res.get("total_energy")
            fermi  = res.get("fermi_energy")
            iters  = res.get("iterations", [])
            c1.metric("Total Energy (eV)", f"{energy:.6f}" if energy is not None else "—")
            c2.metric("Fermi Energy (eV)", f"{fermi:.4f}" if fermi is not None else "—")
            c3.metric("SCF iterations",    str(len(iters)))
            c4.metric("Converged", "Yes" if res["converged"] else "No")

            if res["converged"]:
                st.success("SCF calculation converged.")
            else:
                st.error(
                    "SCF did not converge. "
                    "Try: increase electron_maxstep, reduce mixing_beta, "
                    "change diagonalization algorithm, or check your structure."
                )

            # Forces table
            forces = res.get("forces", [])
            if forces and ss.atomic_positions:
                st.subheader("Forces (Ry/au)")
                import pandas as pd
                symbols = [p[0] for p in ss.atomic_positions]
                rows = []
                for i, (fx, fy, fz) in enumerate(forces):
                    sym = symbols[i] if i < len(symbols) else f"atom{i+1}"
                    fmag = (fx**2 + fy**2 + fz**2) ** 0.5
                    rows.append({"Atom": i+1, "Element": sym,
                                 "Fx": f"{fx:.6f}", "Fy": f"{fy:.6f}",
                                 "Fz": f"{fz:.6f}", "|F|": f"{fmag:.6f}"})
                st.dataframe(rows, use_container_width=True)

            # Warnings
            if res.get("warnings"):
                with st.expander(f"Warnings ({len(res['warnings'])})"):
                    for w in res["warnings"]:
                        st.warning(w)

            # Energy convergence plot
            if len(iters) > 1:
                st.subheader("Energy Convergence")
                import matplotlib.pyplot as plt
                fig, ax = plt.subplots(figsize=(9, 3))
                steps  = [it[0] for it in iters]
                energs = [it[1] for it in iters]
                ax.plot(steps, energs, "b-o", ms=3, lw=1.5)
                ax.set_xlabel("SCF iteration")
                ax.set_ylabel("Total energy (eV)")
                ax.set_title("Electronic SCF convergence")
                ax.grid(alpha=0.35)
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()

    # Output file tail
    st.divider()
    st.subheader("Output file tail (last 40 lines)")
    if os.path.isfile(out_path):
        try:
            with open(out_path, "r", errors="replace") as f:
                all_lines = f.readlines()
            tail_lines = all_lines[-40:]
            st.code("".join(tail_lines), language="text")
        except Exception as e:
            st.error(f"Cannot read output file: {e}")
    else:
        st.caption(f"Output file not found: `{out_path}`")

    # Download output
    if os.path.isfile(out_path):
        st.divider()
        st.subheader("Download Output")
        with open(out_path, "rb") as f:
            out_bytes = f.read()
        st.download_button(
            "Download output file",
            out_bytes,
            file_name=f"{prefix_res}.out",
            mime="text/plain",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
[
    step_structure,
    step_pseudopotentials,
    step_control_system,
    step_electrons_ions_cell,
    step_kpoints_download,
    step_results,
][ss.step]()
