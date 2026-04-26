"""Parse Quantum ESPRESSO pw.x output files."""

import re
import os


def parse_scf_output(filepath):
    """
    Parse a pw.x output file and return a dict with:
      - iterations: list of (iter, energy_Ry) tuples
      - total_energy: final total energy in eV
      - fermi_energy: Fermi energy in eV (if found)
      - forces: list of (symbol, fx, fy, fz) in Ry/au
      - converged: bool
      - warnings: list of warning strings
    """
    result = {
        'iterations': [],
        'total_energy': None,
        'fermi_energy': None,
        'forces': [],
        'stress': None,
        'converged': False,
        'warnings': [],
        'nstep_relax': [],
    }

    if not os.path.isfile(filepath):
        return result

    RY_TO_EV = 13.605698066

    with open(filepath, 'r', errors='replace') as f:
        lines = f.readlines()

    iter_re = re.compile(
        r'^\s*iteration\s*#\s*(\d+).*total energy\s*=\s*([-\d.]+)\s*Ry'
    )
    energy_re = re.compile(
        r'^\s*!\s*total energy\s*=\s*([-\d.Ee+]+)\s*Ry'
    )
    fermi_re = re.compile(
        r'the Fermi energy is\s+([-\d.Ee+]+)\s*ev', re.IGNORECASE
    )
    conv_re = re.compile(r'convergence has been achieved', re.IGNORECASE)
    warn_re = re.compile(r'^\s*Warning', re.IGNORECASE)
    force_header_re = re.compile(r'Forces acting on atoms', re.IGNORECASE)
    force_line_re = re.compile(
        r'atom\s+\d+\s+type\s+\d+\s+force\s*=\s*([-\d.Ee+]+)\s+([-\d.Ee+]+)\s+([-\d.Ee+]+)'
    )
    stress_re = re.compile(r'total\s+stress.*kbar', re.IGNORECASE)
    relax_step_re = re.compile(
        r'^\s*BFGS.*step\s+(\d+)', re.IGNORECASE
    )
    enthalpy_re = re.compile(
        r'^\s*!\s*total enthalpy\s*=\s*([-\d.Ee+]+)\s*Ry'
    )

    in_forces = False
    for i, line in enumerate(lines):
        m = iter_re.search(line)
        if m:
            result['iterations'].append((int(m.group(1)), float(m.group(2)) * RY_TO_EV))

        m = energy_re.search(line)
        if m:
            result['total_energy'] = float(m.group(1)) * RY_TO_EV

        m = enthalpy_re.search(line)
        if m and result['total_energy'] is None:
            result['total_energy'] = float(m.group(1)) * RY_TO_EV

        m = fermi_re.search(line)
        if m:
            result['fermi_energy'] = float(m.group(1))

        if conv_re.search(line):
            result['converged'] = True

        if warn_re.search(line):
            result['warnings'].append(line.strip())

        if force_header_re.search(line):
            in_forces = True
            result['forces'] = []
            continue

        if in_forces:
            m = force_line_re.search(line)
            if m:
                fx, fy, fz = float(m.group(1)), float(m.group(2)), float(m.group(3))
                result['forces'].append((fx, fy, fz))
            elif line.strip() == '':
                in_forces = False

    return result


def parse_bands_dat(filepath):
    """
    Parse bands.x output (bands.dat or prefix.dat) and return
    dict with 'kpath' (list of floats) and 'bands' (list of lists of eV values).
    """
    result = {'kpath': [], 'bands': []}
    if not os.path.isfile(filepath):
        return result

    with open(filepath, 'r') as f:
        content = f.read()

    # Try to parse standard bands.dat format
    # First line: nbnd, nks
    lines = [l for l in content.splitlines() if l.strip()]
    if not lines:
        return result

    try:
        header = lines[0].split()
        nbnd = int(header[0])
        nks = int(header[1])
    except (IndexError, ValueError):
        return result

    kpath = []
    bands_data = [[] for _ in range(nbnd)]

    idx = 1
    for ik in range(nks):
        if idx >= len(lines):
            break
        # k-point line: kx ky kz  kpath_coord
        kline = lines[idx].split()
        idx += 1
        try:
            k_coord = float(kline[3]) if len(kline) >= 4 else float(ik)
            kpath.append(k_coord)
        except (IndexError, ValueError):
            kpath.append(float(ik))

        # Read nbnd energies (may span multiple lines)
        energies = []
        while len(energies) < nbnd and idx < len(lines):
            energies.extend([float(x) for x in lines[idx].split()])
            idx += 1

        for ib, e in enumerate(energies[:nbnd]):
            bands_data[ib].append(e)

    result['kpath'] = kpath
    result['bands'] = bands_data
    return result


def parse_dos(filepath):
    """
    Parse dos.x output file (prefix.dos).
    Returns dict with 'energy' and 'dos' lists (eV units).
    """
    result = {'energy': [], 'dos': [], 'integrated': []}
    if not os.path.isfile(filepath):
        return result

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    result['energy'].append(float(parts[0]))
                    result['dos'].append(float(parts[1]))
                    if len(parts) >= 3:
                        result['integrated'].append(float(parts[2]))
                except ValueError:
                    pass
    return result


def find_output_files(calc_dir, prefix='pwscf'):
    """Return a dict of known output file paths for a calculation directory."""
    files = {}
    out = os.path.join(calc_dir, f'{prefix}.out')
    if os.path.isfile(out):
        files['scf_out'] = out
    bands_dat = os.path.join(calc_dir, f'{prefix}.dat')
    if os.path.isfile(bands_dat):
        files['bands_dat'] = bands_dat
    dos_file = os.path.join(calc_dir, f'{prefix}.dos')
    if os.path.isfile(dos_file):
        files['dos'] = dos_file
    return files
