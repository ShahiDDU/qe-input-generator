"""
Step-by-step test of the QE input generator.
Run with:  python3 test_input.py

Each step prints what was set and shows the running input file.
Press ENTER to continue between steps.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qe.input_writer import PWInput
from config import PSEUDOPOT_DIR, ATOMIC_MASSES

SEP  = "=" * 60
SEP2 = "-" * 60

def pause(msg=""):
    print(f"\n{SEP2}")
    if msg:
        print(f"  {msg}")
    input("  Press ENTER to continue to next step...")
    print()


def show(pw, title="Current input file"):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")
    print(pw.to_string())


# ─────────────────────────────────────────────────────────────
print(SEP)
print("  QE INPUT GENERATOR — Step-by-step test")
print(f"  Pseudopotential directory: {PSEUDOPOT_DIR}")
print(SEP)
pause("Starting with Step 1: Crystal Structure")


# ═════════════════════════════════════════════════════════════
# STEP 1 — Crystal Structure  (Silicon FCC, 2 atoms, ibrav=0)
# ═════════════════════════════════════════════════════════════
print("STEP 1 — Crystal Structure")
print(SEP2)

pw = PWInput()

# Silicon conventional FCC cell (a = 5.43 Å), 2-atom primitive cell
a = 5.431  # Å
pw.system['ibrav'] = 0
pw.system['nat']   = 2
pw.system['ntyp']  = 1

pw.cell_parameters = [
    [0.0,   a/2,  a/2],
    [a/2,   0.0,  a/2],
    [a/2,   a/2,  0.0],
]

pw.atomic_positions = [
    ('Si',  0.0,          0.0,          0.0),
    ('Si',  a/4,          a/4,          a/4),
]
pw.pos_units = 'angstrom'

print(f"  Material  : Silicon (diamond cubic)")
print(f"  ibrav     : 0  (free cell, CELL_PARAMETERS card)")
print(f"  nat       : {pw.system['nat']}")
print(f"  ntyp      : {pw.system['ntyp']}")
print(f"  Lattice a : {a} Å  (FCC primitive vectors)")

show(pw, "After Step 1 — Structure")
pause("Step 2: Pseudopotentials")


# ═════════════════════════════════════════════════════════════
# STEP 2 — Pseudopotentials
# ═════════════════════════════════════════════════════════════
print("STEP 2 — Pseudopotentials")
print(SEP2)

pseudo_file = "Si.pbe-nl-rrkjus_psl.1.0.0.UPF"
full_path   = os.path.join(PSEUDOPOT_DIR, pseudo_file)
exists      = os.path.isfile(full_path)

pw.atomic_species = [
    ('Si', ATOMIC_MASSES['Si'], pseudo_file),
]
pw.control['pseudo_dir'] = PSEUDOPOT_DIR

print(f"  Element   : Si")
print(f"  Mass      : {ATOMIC_MASSES['Si']} amu")
print(f"  Pseudo    : {pseudo_file}")
print(f"  File OK?  : {'✓ found' if exists else '✗ NOT FOUND at ' + full_path}")

show(pw, "After Step 2 — Pseudopotentials")
pause("Step 3: CONTROL namelist (calculation type)")


# ═════════════════════════════════════════════════════════════
# STEP 3 — CONTROL namelist
# ═════════════════════════════════════════════════════════════
print("STEP 3 — CONTROL namelist")
print(SEP2)

pw.control.update({
    'calculation'  : 'scf',
    'restart_mode' : 'from_scratch',
    'prefix'       : 'silicon',
    'outdir'       : './tmp',
    'pseudo_dir'   : PSEUDOPOT_DIR,
    'verbosity'    : 'low',
    'tprnfor'      : True,
    'tstress'      : True,
})

print(f"  calculation   : {pw.control['calculation']}")
print(f"  prefix        : {pw.control['prefix']}")
print(f"  outdir        : {pw.control['outdir']}")
print(f"  tprnfor       : {pw.control['tprnfor']}  (compute forces)")
print(f"  tstress       : {pw.control['tstress']}  (compute stress tensor)")

show(pw, "After Step 3 — CONTROL")
pause("Step 4: SYSTEM namelist (cutoffs, smearing)")


# ═════════════════════════════════════════════════════════════
# STEP 4 — SYSTEM namelist
# ═════════════════════════════════════════════════════════════
print("STEP 4 — SYSTEM namelist")
print(SEP2)

pw.system.update({
    'ecutwfc'     : 40.0,    # Ry — wavefunction cutoff
    'ecutrho'     : 320.0,   # Ry — charge density cutoff (8× ecutwfc for USPP/PAW)
    'occupations' : 'smearing',
    'smearing'    : 'methfessel-paxton',
    'degauss'     : 0.02,    # Ry
})

print(f"  ecutwfc       : {pw.system['ecutwfc']} Ry")
print(f"  ecutrho       : {pw.system['ecutrho']} Ry  (= 8 × ecutwfc)")
print(f"  occupations   : {pw.system['occupations']}")
print(f"  smearing      : {pw.system['smearing']}")
print(f"  degauss       : {pw.system['degauss']} Ry")

show(pw, "After Step 4 — SYSTEM")
pause("Step 5: ELECTRONS namelist (SCF convergence)")


# ═════════════════════════════════════════════════════════════
# STEP 5 — ELECTRONS namelist
# ═════════════════════════════════════════════════════════════
print("STEP 5 — ELECTRONS namelist")
print(SEP2)

pw.electrons.update({
    'conv_thr'         : 1.0e-8,  # Ry
    'mixing_beta'      : 0.7,
    'electron_maxstep' : 100,
    'mixing_mode'      : 'plain',
    'diagonalization'  : 'david',
})

print(f"  conv_thr          : {pw.electrons['conv_thr']} Ry")
print(f"  mixing_beta       : {pw.electrons['mixing_beta']}")
print(f"  electron_maxstep  : {pw.electrons['electron_maxstep']}")
print(f"  mixing_mode       : {pw.electrons['mixing_mode']}")
print(f"  diagonalization   : {pw.electrons['diagonalization']}")

show(pw, "After Step 5 — ELECTRONS")
pause("Step 6: K-Points")


# ═════════════════════════════════════════════════════════════
# STEP 6 — K-Points
# ═════════════════════════════════════════════════════════════
print("STEP 6 — K-Points")
print(SEP2)

pw.kpoints = {
    'type'  : 'automatic',
    'mesh'  : [8, 8, 8],
    'shift' : [0, 0, 0],
}

print(f"  type   : {pw.kpoints['type']}")
print(f"  mesh   : {pw.kpoints['mesh']}")
print(f"  shift  : {pw.kpoints['shift']}")
print(f"  (Gamma-centered 8×8×8 — good for Si SCF)")

show(pw, "After Step 6 — K-Points")
pause("Step 7: Save input file to disk")


# ═════════════════════════════════════════════════════════════
# STEP 7 — Save to file
# ═════════════════════════════════════════════════════════════
print("STEP 7 — Save input file")
print(SEP2)

out_dir  = os.path.expanduser("~/qe_test_si")
out_file = os.path.join(out_dir, "silicon.scf.in")
os.makedirs(out_dir, exist_ok=True)
pw.save(out_file)

print(f"  Written to : {out_file}")
print(f"  File size  : {os.path.getsize(out_file)} bytes")

pause("Step 8: Validate — re-read and diff")


# ═════════════════════════════════════════════════════════════
# STEP 8 — Validate: re-read and print final file
# ═════════════════════════════════════════════════════════════
print("STEP 8 — Final validation")
print(SEP2)

with open(out_file) as f:
    content = f.read()

print(f"\n{'='*60}")
print("  FINAL INPUT FILE (silicon.scf.in)")
print(f"{'='*60}")
print(content)

# Quick sanity checks
checks = {
    "&CONTROL"         : "&CONTROL" in content,
    "&SYSTEM"          : "&SYSTEM" in content,
    "&ELECTRONS"       : "&ELECTRONS" in content,
    "CELL_PARAMETERS"  : "CELL_PARAMETERS" in content,
    "ATOMIC_SPECIES"   : "ATOMIC_SPECIES" in content,
    "ATOMIC_POSITIONS" : "ATOMIC_POSITIONS" in content,
    "K_POINTS"         : "K_POINTS" in content,
    "Si pseudopotential": pseudo_file in content,
    "ecutwfc = 40"     : "ecutwfc = 40" in content,
}

print(f"\n{'='*60}")
print("  SANITY CHECKS")
print(f"{'='*60}")
all_ok = True
for label, ok in checks.items():
    status = "✓" if ok else "✗"
    print(f"  {status}  {label}")
    if not ok:
        all_ok = False

print()
if all_ok:
    print("  All checks passed ✓")
    print(f"\n  To run QE (if pw.x is available):")
    print(f"    cd {out_dir}")
    print(f"    pw.x -in silicon.scf.in | tee silicon.scf.out")
else:
    print("  Some checks failed — review the output above.")

print(f"\n{SEP}")
print("  Test complete.")
print(SEP)
