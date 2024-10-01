import numpy as np

# A dictionary of atomic masses for common elements
atomic_masses = {
    'H': 1.007841,
    'He': 4.002602,
    'Li': 6.94,
    'Be': 9.0121831,
    'B': 10.811,
    'C': 12.01074,
    'N': 14.006703,
    'O': 15.999405,
    'F': 18.998403163,
    'Ne': 20.1797,
    'Na': 22.98976928,
    'Mg': 24.3051,
    'Al': 26.9815385,
    'Si': 28.0855,
    'P': 30.973761998,
    'S': 32.0648,
    'Cl': 35.4529,
    'Ar': 39.948,
    'K': 39.0983,
    'Ca': 40.078,
    'Fe': 55.845,
    'Cu': 63.546,
    'Zn': 65.38,
    'Br': 79.9035,
    'I':126.90447,
    'Sm':150.36,
    # Add more elements as needed
    # https://github.com/cgohlke/molmass/blob/master/molmass/elements.py
}

class Molecule:
    def __init__(self, symbols, coordinates, energy=None, frequencies=None, gas_phase=None):
        """
        Initialize a Molecule object.
        """
        self.symbols = np.array(symbols)
        self.coordinates = np.array(coordinates, dtype=float)
        self.energy = energy
        self.frequencies = np.array(frequencies) if frequencies is not None else None
        self.gas_phase = gas_phase

        # Validate that the number of symbols matches the number of coordinate sets
        if len(self.symbols) != len(self.coordinates):
            raise ValueError("The number of symbols and coordinate sets must be the same.")

    @classmethod
    def from_xyz(cls, filename, energy=None, frequencies=None, gas_phase=None):
        """
        Create a Molecule instance from an XYZ-format file.

        Parameters:
        filename (str): Path to the XYZ file.
        energy (float, optional): Energy of the molecule.
        frequencies (list, optional): Vibrational frequencies.
        gas_phase (bool, optional): Indicates if the molecule is in the gas phase.

        Returns:
        Molecule: An instance of the Molecule class.
        """
        symbols = []
        coordinates = []
        with open(filename, 'r') as file:
            lines = file.readlines()
            if len(lines) < 3:
                raise ValueError("The XYZ file is incomplete or corrupted.")
            try:
                num_atoms = int(lines[0].strip())
            except ValueError:
                raise ValueError("The first line of the XYZ file should be the number of atoms.")
            atom_lines = lines[2:2+num_atoms]
            for line in atom_lines:
                parts = line.strip().split()
                if len(parts) < 4:
                    raise ValueError("Each atom line must have at least 4 entries: symbol, x, y, z.")
                symbol = parts[0]
                if symbol not in atomic_masses:
                    raise ValueError(f"Unknown element symbol: {symbol}")
                x, y, z = map(float, parts[1:4])
                symbols.append(symbol)
                coordinates.append([x, y, z])
        return cls(symbols, coordinates, energy, frequencies, gas_phase)

    def __repr__(self):
        """
        Return a string representation of the Molecule.
        """
        lines = []
        for symbol, coord in zip(self.symbols, self.coordinates):
            x, y, z = coord
            lines.append(f"{symbol} {x:.6f} {y:.6f} {z:.6f}")
        return '\n'.join(lines)

    def center_of_mass(self):
        """
        Calculate and return the center of mass of the molecule.
        """
        masses = np.array([atomic_masses[symbol] for symbol in self.symbols])
        total_mass = masses.sum()
        com = np.dot(masses, self.coordinates) / total_mass
        return com

    def molecular_mass(self):
        """
        Calculate the molecular mass in g/mol.

        Returns:
        float: Molecular mass.
        """
        masses = np.array([atomic_masses[symbol] for symbol in self.symbols])
        return masses.sum()

    def moments_of_inertia(self):
        """
        Calculate and return the principal moments of inertia of the molecule.
        """
        masses = np.array([atomic_masses[symbol] for symbol in self.symbols])
        # Center the coordinates around the center of mass
        coords = self.coordinates - self.center_of_mass()

        # Initialize the inertia tensor
        inertia_tensor = np.zeros((3, 3))
        for i in range(len(masses)):
            mass = masses[i]
            x, y, z = coords[i]
            inertia_tensor[0, 0] += mass * (y**2 + z**2)
            inertia_tensor[1, 1] += mass * (x**2 + z**2)
            inertia_tensor[2, 2] += mass * (x**2 + y**2)
            inertia_tensor[0, 1] -= mass * x * y
            inertia_tensor[0, 2] -= mass * x * z
            inertia_tensor[1, 2] -= mass * y * z

        # Complete the symmetric tensor
        inertia_tensor[1, 0] = inertia_tensor[0, 1]
        inertia_tensor[2, 0] = inertia_tensor[0, 2]
        inertia_tensor[2, 1] = inertia_tensor[1, 2]

        # Calculate eigenvalues (principal moments of inertia)
        moments, _ = np.linalg.eigh(inertia_tensor)
        return moments

    def is_linear(self, tolerance=1e-3):
        """
        Determine if the molecule is linear within a specified tolerance.

        Parameters:
        tolerance (float): The threshold below which a moment of inertia is considered zero.

        Returns:
        bool: True if the molecule is linear, False otherwise.
        """
        moments = self.moments_of_inertia()
        # Sort the moments to ensure consistent order
        moments = np.sort(moments)
        # For a linear molecule, two moments should be approximately zero
        zero_moments = moments < tolerance
        if np.sum(zero_moments) >= 1:
            return True
        else:
            return False

    def recenter(self):
        """
        Recenter the molecule so that its center of mass is at the origin.
        """
        com = self.center_of_mass()
        self.coordinates -= com

    def reorder_atoms(self, new_order):
        """
        Reorder the atoms in the molecule.

        Parameters:
        new_order (list): A list of indices representing the new order.
        """
        if sorted(new_order) != list(range(len(self.symbols))):
            raise ValueError("new_order must be a permutation of indices 0 to N-1.")
        self.symbols = self.symbols[new_order]
        self.coordinates = self.coordinates[new_order]

    def distance(self, atom_index1, atom_index2):
        """
        Calculate the distance between two atoms.

        Parameters:
        atom_index1 (int): Index of the first atom.
        atom_index2 (int): Index of the second atom.

        Returns:
        float: The Euclidean distance between the two atoms.
        """
        if atom_index1 >= len(self.symbols) or atom_index2 >= len(self.symbols):
            raise IndexError("Atom index out of range.")
        coord1 = self.coordinates[atom_index1]
        coord2 = self.coordinates[atom_index2]
        return np.linalg.norm(coord1 - coord2)

    def bond_angle(self, atom_index1, atom_index2, atom_index3):
        """
        Calculate the bond angle formed by three atoms.

        Parameters:
        atom_index1 (int): Index of the first atom.
        atom_index2 (int): Index of the central atom.
        atom_index3 (int): Index of the third atom.

        Returns:
        float: The bond angle in degrees.
        """
        if any(index >= len(self.symbols) for index in [atom_index1, atom_index2, atom_index3]):
            raise IndexError("Atom index out of range.")
        # Vectors from central atom to the two other atoms
        vec1 = self.coordinates[atom_index1] - self.coordinates[atom_index2]
        vec2 = self.coordinates[atom_index3] - self.coordinates[atom_index2]
        # Normalize vectors
        vec1_norm = vec1 / np.linalg.norm(vec1)
        vec2_norm = vec2 / np.linalg.norm(vec2)
        # Compute angle
        cos_theta = np.dot(vec1_norm, vec2_norm)
        # Clamp cos_theta to [-1, 1] to avoid numerical errors
        cos_theta = np.clip(cos_theta, -1.0, 1.0)
        angle = np.degrees(np.arccos(cos_theta))
        return angle

    def dihedral_angle(self, atom_index1, atom_index2, atom_index3, atom_index4):
        """
        Calculate the dihedral angle defined by four atoms.

        Parameters:
        atom_index1 (int): Index of the first atom.
        atom_index2 (int): Index of the second atom.
        atom_index3 (int): Index of the third atom.
        atom_index4 (int): Index of the fourth atom.

        Returns:
        float: The dihedral angle in degrees.
        """
        if any(index >= len(self.symbols) for index in [atom_index1, atom_index2, atom_index3, atom_index4]):
            raise IndexError("Atom index out of range.")

        p0 = self.coordinates[atom_index1]
        p1 = self.coordinates[atom_index2]
        p2 = self.coordinates[atom_index3]
        p3 = self.coordinates[atom_index4]

        b0 = -1.0 * (p1 - p0)
        b1 = p2 - p1
        b2 = p3 - p2

        # Normalize b1 so that it does not influence magnitude of vector products
        b1 /= np.linalg.norm(b1)

        # Compute vectors normal to the planes
        v = b0 - np.dot(b0, b1) * b1
        w = b2 - np.dot(b2, b1) * b1

        x = np.dot(v, w)
        y = np.dot(np.cross(b1, v), w)

        angle = np.degrees(np.arctan2(y, x))
        return angle

    def set_property(self, name, value):
        """
        Add or modify an optional property of the molecule.
        """
        setattr(self, name, value)

    def get_property(self, name):
        """
        Retrieve a property of the molecule.
        """
        return getattr(self, name, None)

