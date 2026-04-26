"""Generate Quantum ESPRESSO pw.x input files."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_atomic_mass, PSEUDOPOT_DIR


class PWInput:
    """Builds and serialises a pw.x input file."""

    def __init__(self):
        self.control = {
            'calculation': 'scf',
            'restart_mode': 'from_scratch',
            'prefix': 'pwscf',
            'outdir': './tmp',
            'pseudo_dir': PSEUDOPOT_DIR,
            'verbosity': 'low',
            'tprnfor': True,
            'tstress': True,
        }
        self.system = {
            'ibrav': 0,
            'nat': 1,
            'ntyp': 1,
            'ecutwfc': 60.0,
            'ecutrho': 480.0,
            'occupations': 'smearing',
            'smearing': 'methfessel-paxton',
            'degauss': 0.01,
        }
        self.electrons = {
            'conv_thr': 1.0e-8,
            'mixing_beta': 0.7,
            'electron_maxstep': 200,
        }
        self.ions = {
            'ion_dynamics': 'bfgs',
        }
        self.cell = {
            'cell_dynamics': 'bfgs',
            'press_conv_thr': 0.5,
        }
        # list of (symbol, mass, pseudo_filename)
        self.atomic_species = []
        # list of (symbol, x, y, z)
        self.atomic_positions = []
        self.pos_units = 'angstrom'
        # k-points dict
        self.kpoints = {
            'type': 'automatic',
            'mesh': [4, 4, 4],
            'shift': [0, 0, 0],
        }
        # 3x3 list of lists (only used when ibrav=0)
        self.cell_parameters = None

    # ------------------------------------------------------------------
    def to_string(self):
        lines = []

        def _fmt(v):
            if isinstance(v, bool):
                return '.true.' if v else '.false.'
            if isinstance(v, str):
                return f"'{v}'"
            if isinstance(v, float):
                return f'{v:g}'
            return str(v)

        def _section(tag, d):
            lines.append(f'&{tag}')
            for k, v in d.items():
                if v is not None:
                    lines.append(f'  {k} = {_fmt(v)},')
            lines.append('/')
            lines.append('')

        _section('CONTROL', self.control)
        _section('SYSTEM', self.system)
        _section('ELECTRONS', self.electrons)

        calc = self.control.get('calculation', 'scf')
        if calc in ('relax', 'vc-relax', 'md', 'vc-md'):
            _section('IONS', self.ions)
        if calc in ('vc-relax', 'vc-md'):
            _section('CELL', self.cell)

        if self.cell_parameters is not None and self.system.get('ibrav', 0) == 0:
            lines.append('CELL_PARAMETERS angstrom')
            for row in self.cell_parameters:
                lines.append(f'  {row[0]:14.9f}  {row[1]:14.9f}  {row[2]:14.9f}')
            lines.append('')

        lines.append('ATOMIC_SPECIES')
        for sym, mass, pseudo in self.atomic_species:
            lines.append(f'  {sym:<4s}  {mass:10.5f}  {pseudo}')
        lines.append('')

        lines.append(f'ATOMIC_POSITIONS {{{self.pos_units}}}')
        for sym, x, y, z in self.atomic_positions:
            lines.append(f'  {sym:<4s}  {x:14.9f}  {y:14.9f}  {z:14.9f}')
        lines.append('')

        ktype = self.kpoints.get('type', 'automatic')
        if ktype == 'gamma':
            lines.append('K_POINTS gamma')
        elif ktype == 'automatic':
            m = self.kpoints['mesh']
            s = self.kpoints['shift']
            lines.append('K_POINTS automatic')
            lines.append(f'  {m[0]} {m[1]} {m[2]}  {s[0]} {s[1]} {s[2]}')
        elif ktype in ('crystal_b', 'tpiba_b'):
            pts = self.kpoints.get('points', [])
            lines.append(f'K_POINTS {ktype}')
            lines.append(f'  {len(pts)}')
            for pt in pts:
                lines.append(
                    f'  {pt[0]:.6f}  {pt[1]:.6f}  {pt[2]:.6f}  {pt[3]}'
                )
        return '\n'.join(lines) + '\n'

    # ------------------------------------------------------------------
    @classmethod
    def from_ase(cls, atoms, calc_type='scf', ecutwfc=60.0,
                 pseudo_dir=None, pseudo_map=None):
        """Construct from an ASE Atoms object."""
        pw = cls()
        if pseudo_dir:
            pw.control['pseudo_dir'] = pseudo_dir

        syms_sorted = sorted(set(atoms.get_chemical_symbols()))
        pw.control['calculation'] = calc_type
        pw.system['ibrav'] = 0
        pw.system['nat'] = len(atoms)
        pw.system['ntyp'] = len(syms_sorted)
        pw.system['ecutwfc'] = ecutwfc
        pw.system['ecutrho'] = ecutwfc * 8

        if calc_type in ('relax', 'vc-relax', 'md', 'vc-md'):
            pw.ions['ion_dynamics'] = 'bfgs'
        if calc_type in ('vc-relax', 'vc-md'):
            pw.cell['cell_dynamics'] = 'bfgs'

        pw.cell_parameters = atoms.get_cell().tolist()

        pm = pseudo_map or {}
        for sym in syms_sorted:
            mass = get_atomic_mass(sym)
            pseudo = pm.get(sym, f'{sym}.UPF')
            pw.atomic_species.append((sym, mass, pseudo))

        pos = atoms.get_positions()
        for s, p in zip(atoms.get_chemical_symbols(), pos):
            pw.atomic_positions.append((s, float(p[0]), float(p[1]), float(p[2])))

        pw.pos_units = 'angstrom'
        return pw

    # ------------------------------------------------------------------
    def update_from_ase(self, atoms, pseudo_map=None):
        """Refresh structure-related fields from an ASE Atoms object."""
        syms_sorted = sorted(set(atoms.get_chemical_symbols()))
        self.system['nat'] = len(atoms)
        self.system['ntyp'] = len(syms_sorted)
        self.cell_parameters = atoms.get_cell().tolist()

        pm = pseudo_map or {}
        existing_pseudo = {s: p for s, _, p in self.atomic_species}
        self.atomic_species = []
        for sym in syms_sorted:
            mass = get_atomic_mass(sym)
            pseudo = pm.get(sym, existing_pseudo.get(sym, f'{sym}.UPF'))
            self.atomic_species.append((sym, mass, pseudo))

        pos = atoms.get_positions()
        self.atomic_positions = []
        for s, p in zip(atoms.get_chemical_symbols(), pos):
            self.atomic_positions.append((s, float(p[0]), float(p[1]), float(p[2])))
        self.pos_units = 'angstrom'

    # ------------------------------------------------------------------
    def save(self, filepath):
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, 'w') as f:
            f.write(self.to_string())

    # ------------------------------------------------------------------
    def to_dict(self):
        return {
            'control': dict(self.control),
            'system': dict(self.system),
            'electrons': dict(self.electrons),
            'ions': dict(self.ions),
            'cell': dict(self.cell),
            'atomic_species': list(self.atomic_species),
            'atomic_positions': list(self.atomic_positions),
            'pos_units': self.pos_units,
            'kpoints': dict(self.kpoints),
            'cell_parameters': self.cell_parameters,
        }

    @classmethod
    def from_dict(cls, d):
        pw = cls()
        pw.control.update(d.get('control', {}))
        pw.system.update(d.get('system', {}))
        pw.electrons.update(d.get('electrons', {}))
        pw.ions.update(d.get('ions', {}))
        pw.cell.update(d.get('cell', {}))
        pw.atomic_species = [tuple(x) for x in d.get('atomic_species', [])]
        pw.atomic_positions = [tuple(x) for x in d.get('atomic_positions', [])]
        pw.pos_units = d.get('pos_units', 'angstrom')
        pw.kpoints = d.get('kpoints', pw.kpoints)
        pw.cell_parameters = d.get('cell_parameters')
        return pw
