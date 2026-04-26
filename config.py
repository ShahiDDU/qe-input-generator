import os

QE_BIN = "/opt/espresso/7.5"
PSEUDOPOT_DIR = "/opt/AdvanceSoft/NanoLabo/pseudopot"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.expanduser("~/qe_projects")

os.makedirs(PROJECTS_DIR, exist_ok=True)

CALC_TYPES = ["scf", "nscf", "bands", "relax", "vc-relax", "md", "vc-md"]

OCCUPATION_TYPES = ["smearing", "fixed", "tetrahedra", "tetrahedra_lin",
                    "tetrahedra_opt", "from_input"]

SMEARING_TYPES = ["gaussian", "methfessel-paxton", "marzari-vanderbilt",
                  "fermi-dirac", "cold"]

MIXING_MODES = ["plain", "TF", "local-TF"]

DIAG_TYPES = ["david", "cg", "ppcg", "rmm-davidson", "rmm-paro"]

ION_DYNAMICS = ["bfgs", "damp", "verlet", "langevin", "langevin-smc",
                "beeman", "fire"]

CELL_DYNAMICS = ["bfgs", "damp-pr", "damp-w", "none", "sd", "pr", "w"]

IBRAV_LABELS = {
    0: "0 - Free (CELL_PARAMETERS card)",
    1: "1 - Simple Cubic (sc)",
    2: "2 - Face-Centered Cubic (fcc)",
    3: "3 - Body-Centered Cubic (bcc)",
    4: "4 - Hexagonal",
    5: "5 - Trigonal (3-fold axis c)",
    6: "6 - Tetragonal P",
    7: "7 - Tetragonal I",
    8: "8 - Orthorhombic P",
    9: "9 - Orthorhombic C",
    10: "10 - Orthorhombic F",
    11: "11 - Orthorhombic I",
    12: "12 - Monoclinic P (c unique)",
    13: "13 - Monoclinic C",
    14: "14 - Triclinic",
}

ELEMENTS = [
    'H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
    'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca',
    'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn',
    'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr',
    'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn',
    'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd',
    'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb',
    'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg',
    'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn',
]

ATOMIC_MASSES = {
    'H': 1.008, 'He': 4.003, 'Li': 6.941, 'Be': 9.012, 'B': 10.811,
    'C': 12.011, 'N': 14.007, 'O': 15.999, 'F': 18.998, 'Ne': 20.180,
    'Na': 22.990, 'Mg': 24.305, 'Al': 26.982, 'Si': 28.086, 'P': 30.974,
    'S': 32.065, 'Cl': 35.453, 'Ar': 39.948, 'K': 39.098, 'Ca': 40.078,
    'Sc': 44.956, 'Ti': 47.867, 'V': 50.942, 'Cr': 51.996, 'Mn': 54.938,
    'Fe': 55.845, 'Co': 58.933, 'Ni': 58.693, 'Cu': 63.546, 'Zn': 65.38,
    'Ga': 69.723, 'Ge': 72.640, 'As': 74.922, 'Se': 78.960, 'Br': 79.904,
    'Kr': 83.798, 'Rb': 85.468, 'Sr': 87.620, 'Y': 88.906, 'Zr': 91.224,
    'Nb': 92.906, 'Mo': 95.960, 'Tc': 98.000, 'Ru': 101.07, 'Rh': 102.91,
    'Pd': 106.42, 'Ag': 107.87, 'Cd': 112.41, 'In': 114.82, 'Sn': 118.71,
    'Sb': 121.76, 'Te': 127.60, 'I': 126.90, 'Xe': 131.29, 'Cs': 132.91,
    'Ba': 137.33, 'La': 138.91, 'Ce': 140.12, 'Pr': 140.91, 'Nd': 144.24,
    'Pm': 145.00, 'Sm': 150.36, 'Eu': 151.96, 'Gd': 157.25, 'Tb': 158.93,
    'Dy': 162.50, 'Ho': 164.93, 'Er': 167.26, 'Tm': 168.93, 'Yb': 173.04,
    'Lu': 174.97, 'Hf': 178.49, 'Ta': 180.95, 'W': 183.84, 'Re': 186.21,
    'Os': 190.23, 'Ir': 192.22, 'Pt': 195.08, 'Au': 196.97, 'Hg': 200.59,
    'Tl': 204.38, 'Pb': 207.20, 'Bi': 208.98,
}

ELEMENT_COLORS = {
    'H': '#FFFFFF', 'He': '#D9FFFF', 'Li': '#CC80FF', 'Be': '#C2FF00',
    'B': '#FFB5B5', 'C': '#909090', 'N': '#3050F8', 'O': '#FF0D0D',
    'F': '#90E050', 'Ne': '#B3E3F5', 'Na': '#AB5CF2', 'Mg': '#8AFF00',
    'Al': '#BFA6A6', 'Si': '#F0C8A0', 'P': '#FF8000', 'S': '#FFFF30',
    'Cl': '#1FF01F', 'Ar': '#80D1E3', 'K': '#8F40D4', 'Ca': '#3DFF00',
    'Sc': '#E6E6E6', 'Ti': '#BFC2C7', 'V': '#A6A6AB', 'Cr': '#8A99C7',
    'Mn': '#9C7AC7', 'Fe': '#E06633', 'Co': '#F090A0', 'Ni': '#50D050',
    'Cu': '#C88033', 'Zn': '#7D80B0', 'Ga': '#C28F8F', 'Ge': '#668F8F',
    'As': '#BD80E3', 'Se': '#FFA100', 'Br': '#A62929', 'Kr': '#5CB8D1',
    'Rb': '#702EB0', 'Sr': '#00FF00', 'Y': '#94FFFF', 'Zr': '#94E0E0',
    'Nb': '#73C2C9', 'Mo': '#54B5B5', 'Tc': '#3B9E9E', 'Ru': '#248F8F',
    'Rh': '#0A7D8C', 'Pd': '#006985', 'Ag': '#C0C0C0', 'Cd': '#FFD98F',
    'In': '#A67573', 'Sn': '#668080', 'Sb': '#9E63B5', 'Te': '#D47A00',
    'I': '#940094', 'Xe': '#429EB0', 'Cs': '#57178F', 'Ba': '#00C900',
    'La': '#70D4FF', 'Ce': '#FFFFC7', 'Pr': '#D9FFC7', 'Nd': '#C7FFC7',
    'W': '#2194D6', 'Re': '#267DAB', 'Os': '#266696', 'Ir': '#175487',
    'Pt': '#D0D0E0', 'Au': '#FFD123', 'Hg': '#B8B8D0', 'Pb': '#575961',
    'Bi': '#9E4FB5', 'Fe': '#E06633',
}

COVALENT_RADII = {
    'H': 0.31, 'He': 0.28, 'Li': 1.28, 'Be': 0.96, 'B': 0.84,
    'C': 0.77, 'N': 0.71, 'O': 0.66, 'F': 0.57, 'Ne': 0.58,
    'Na': 1.66, 'Mg': 1.41, 'Al': 1.21, 'Si': 1.11, 'P': 1.07,
    'S': 1.05, 'Cl': 1.02, 'Ar': 1.06, 'K': 2.03, 'Ca': 1.76,
    'Sc': 1.70, 'Ti': 1.60, 'V': 1.53, 'Cr': 1.39, 'Mn': 1.50,
    'Fe': 1.42, 'Co': 1.38, 'Ni': 1.24, 'Cu': 1.32, 'Zn': 1.22,
    'Ga': 1.22, 'Ge': 1.20, 'As': 1.19, 'Se': 1.20, 'Br': 1.20,
    'Kr': 1.16, 'Rb': 2.20, 'Sr': 1.95, 'Y': 1.90, 'Zr': 1.75,
    'Nb': 1.64, 'Mo': 1.54, 'Tc': 1.47, 'Ru': 1.46, 'Rh': 1.42,
    'Pd': 1.39, 'Ag': 1.45, 'Cd': 1.44, 'In': 1.42, 'Sn': 1.39,
    'Sb': 1.39, 'Te': 1.38, 'I': 1.39, 'Xe': 1.40, 'Cs': 2.44,
    'Ba': 2.15, 'La': 2.07, 'W': 1.62, 'Re': 1.51, 'Os': 1.44,
    'Ir': 1.41, 'Pt': 1.36, 'Au': 1.36, 'Hg': 1.32, 'Pb': 1.46,
    'Bi': 1.48,
}


def get_element_color(symbol):
    return ELEMENT_COLORS.get(symbol, '#FF69B4')


def get_covalent_radius(symbol):
    return COVALENT_RADII.get(symbol, 1.0)


def get_atomic_mass(symbol):
    return ATOMIC_MASSES.get(symbol, 1.0)
