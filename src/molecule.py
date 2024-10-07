import numpy as np
from src.geometry import GeometryMixin
from src.reorder import ReorderMixin
from src.bonding import Bonding
from src.config import atomic_masses

class Molecule(GeometryMixin, ReorderMixin):
    def __init__(self, symbols, coordinates, energy=None, frequencies=None, gas_phase=None):
        """
        Initialize a Molecule object.
        """
        self.symbols = np.array(symbols)
        self.coordinates = np.array(coordinates, dtype=float)
        self.energy = energy
        self.frequencies = np.array(frequencies) if frequencies is not None else None
        self.gas_phase = gas_phase
        self.bonding = Bonding(self.symbols, self.coordinates)

        # Validate that the number of symbols matches the number of coordinate sets
        if len(self.symbols) != len(self.coordinates):
            raise ValueError("The number of symbols and coordinate sets must be the same.")

    def molecular_mass(self):
        """
        Calculate the molecular mass in g/mol.

        Returns:
        float: Molecular mass.
        """
        masses = np.array([atomic_masses[symbol] for symbol in self.symbols])
        return masses.sum()

    def center_of_mass(self):
        """
        Calculate and return the center of mass of the molecule.
        """
        masses = np.array([atomic_masses[symbol] for symbol in self.symbols])
        total_mass = masses.sum()
        com = np.dot(masses, self.coordinates) / total_mass
        return com

    def moments_of_inertia(self):
        """
        Calculate and return the principal moments of inertia of the molecule.
        """
        masses = np.array([atomic_masses[symbol] for symbol in self.symbols])
        coords = self.coordinates - self.center_of_mass()  # Centering around the center of mass
    
        # Initialize the inertia tensor as a 3x3 matrix
        inertia_tensor = np.zeros((3, 3))
    
        for mass, (x, y, z) in zip(masses, coords):
            inertia_tensor[0, 0] += mass * (y**2 + z**2)
            inertia_tensor[1, 1] += mass * (x**2 + z**2)
            inertia_tensor[2, 2] += mass * (x**2 + y**2)
            inertia_tensor[0, 1] -= mass * x * y
            inertia_tensor[0, 2] -= mass * x * z
            inertia_tensor[1, 2] -= mass * y * z
    
        # Complete the symmetric tensor by copying the values
        inertia_tensor[1, 0], inertia_tensor[2, 0], inertia_tensor[2, 1] = inertia_tensor[0, 1], inertia_tensor[0, 2], inertia_tensor[1, 2]
    
        # Calculate eigenvalues (principal moments of inertia)
        moments, _ = np.linalg.eigh(inertia_tensor)
    
        return moments

    def get_coordinates_by_symbol(self, element_symbol):
        """
        Return the coordinates of all atoms where the symbol matches the given element symbol.
    
        Parameters:
        element_symbol (str): The element symbol to search for (e.g., 'H', 'O', 'C').
    
        Returns:
        list of np.ndarray: A list of coordinates (np.array) for atoms matching the given symbol.
        """
        # Ensure the element symbol is properly formatted (e.g., 'C', 'O', etc.)
        element_symbol = element_symbol.capitalize()
    
        # Gather all coordinates where the atomic symbol matches the given element symbol
        matching_coords = [
            coord for symbol, coord in zip(self.symbols, self.coordinates) if symbol == element_symbol
        ]

        return matching_coords

    @staticmethod
    def extract_energy(comment_line):
        """
        Extracts the energy from the comment line using multiple regex patterns.

        Parameters:
        comment_line (str): The comment line from which to extract the energy.

        Returns:
        float or None: The extracted energy, or None if no energy is found.
        """
        # List of regex patterns to match different energy formats
        energy_patterns = [
            r"Energy\s*=\s*(-?\d+\.\d+)",   # Matches 'Energy = -1234.56789'
            r"dE\s*=\s*(-?\d+\.\d+)",       # Matches 'dE = -1234.56789'
            r"\s*(-?\d+\.\d+)"              # Matches floating-point number with optional spaces
        ]

        for pattern in energy_patterns:
            match = re.search(pattern, comment_line)
            if match:
                return float(match.group(1))

        return None

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

    def to_xyz(self, comment="Molecule"):
        """
        Convert the Molecule instance to an XYZ-formatted string.

        Parameters:
        - comment (str, optional): Comment or title for the XYZ file. Default is "Molecule".

        Returns:
        - xyz_str (str): The XYZ-formatted string representing the molecule.
        """
        num_atoms = len(self.symbols)
        xyz_lines = [f"{num_atoms}", comment]
        for symbol, coord in zip(self.symbols, self.coordinates):
            # Ensure coordinates are formatted to three decimal places
            line = f"{symbol}    {coord[0]:.3f}    {coord[1]:.3f}    {coord[2]:.3f}"
            xyz_lines.append(line)
        xyz_str = "\n".join(xyz_lines)
        return xyz_str

    def compare_energy_and_moments(self, other, precision=1.0):
        """
        Compare the energy and moments of inertia of two molecules.
        Raises an error if the molecules are not comparable.
    
        Parameters:
        other (Molecule): The other molecule to compare.
        precision (float): The allowable difference for moments of inertia comparison (default is 1.0).
    
        Returns:
        bool: True if both energy and moments of inertia match within the given precision, False otherwise.
        """
        # First check if molecules are comparable
        if not self.is_comparable(other):
            raise ValueError("Molecules are not comparable (different elements or quantities).")
            #return False
    
        # Compare energy
        if not np.isclose(self.energy, other.energy, atol=precision):
            return False
    
        # Compare moments of inertia
        return np.allclose(self.moments_of_inertia(), other.moments_of_inertia(), atol=precision)
        #return self.compare_moments_of_inertia(other, precision)
 
    def is_comparable(self, other):
        """
        Check if two molecules are comparable by having the same number of elements.
        
        Parameters:
        other (Molecule): The other molecule to compare with.
        
        Returns:
        bool: True if the molecules are comparable, False otherwise.
        """
        return sorted(self.symbols) == sorted(other.symbols)
 
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

    def __repr__(self):
        """
        Return a string representation of the Molecule.
        """
        lines = []
        for symbol, coord in zip(self.symbols, self.coordinates):
            x, y, z = coord
            lines.append(f"{symbol} {x:.6f} {y:.6f} {z:.6f}")
        return '\n'.join(lines)

    def copy(self):
        """
        Create a deep copy of the molecule.
    
        Returns:
        Molecule: A new Molecule instance that is a copy of the current molecule.
        """
        return Molecule(
            symbols=np.copy(self.symbols),
            coordinates=np.copy(self.coordinates),
            energy=self.energy,
            frequencies = np.copy(self.frequencies) if self.frequencies is not None else None,
            gas_phase=self.gas_phase,
        )


