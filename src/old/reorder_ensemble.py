#!/bin/env python3
import numpy as np
from scipy.spatial.distance import cdist
from scipy.optimize import linear_sum_assignment
import argparse

def is_duplicate(atoms, ref_atoms):
    """
    Finds the best atom sort order based on RMSD between reference and target molecule.
    This routine does not change the functionality of the script.

    Parameters:
    molecule : The data of the target molecule.
    reference_molecule : The data of the reference molecule.
    data structure of a molecule: [elem, np.array(atom_coords) for all elems]

    Returns:
    tuple: The reordered atoms, the best sort order
    """

    moi = calculate_moments_of_inertia(atoms)
    ref_moi = calculate_moments_of_inertia(ref_atoms)

    #for energy, atoms in ensemble_molecules:

    ref_atoms_sorted, ref_sort_indices = reorder_by_centroid(ref_atoms)
    target_atoms_sorted, sort_indices = reorder_by_centroid(atoms)

    ref_coords_sorted = np.array([atom[1] for atom in ref_atoms_sorted])
    target_coords_sorted = np.array([atom[1] for atom in target_atoms_sorted])
    R = kabsch(ref_coords_sorted, target_coords_sorted)
    target_coords_aligned = np.dot(target_coords_sorted, R)

    reordered_atoms, hungarian_indices = reorder_atoms_hungarian(
        ref_atoms_sorted, [(atom[0], coord) for atom, coord in zip(target_atoms_sorted, target_coords_aligned)]
    )
    reordered_coords = np.array([atom[1] for atom in reordered_atoms])

    R_final = kabsch(ref_coords_sorted, reordered_coords)
    final_coords_aligned = np.dot(reordered_coords, R_final)

    rmsd = calculate_rmsd(ref_coords_sorted, final_coords_aligned)

    if rmsd < 0.2:
        #combined_order = sort_indices[hungarian_indices[invert_positions(ref_sort_indices)]]
        #return reordered_atoms, combined_order
        duplicate = True
    else:
        duplicate = False
    return duplicate


def find_best_sort_order_ensemble(ensemble_molecules, reference_molecules):
    """
    Finds the best atom sort order based on RMSD between reference and target ensembles.

    Parameters:
    ensemble_filename (str): The XYZ file of the target ensemble.
    reference_ensemble_filename (str): The XYZ file of the reference ensemble.

    Returns:
    tuple: The reordered atoms, the best sort order, reference energy, and target energy.
    """

    for ref_energy, ref_atoms in reference_molecules:
        ref_moi = calculate_moments_of_inertia(ref_atoms)

        for energy, atoms in ensemble_molecules:
            if abs(energy - ref_energy) > 2e-3:
                continue

            target_moi = calculate_moments_of_inertia(atoms)
            if np.linalg.norm(ref_moi - target_moi) > 1e2: #tested, and 1e2 catches some more ... unweighted moi
                continue

            ref_atoms_sorted, ref_sort_indices = reorder_by_centroid(ref_atoms)
            target_atoms_sorted, sort_indices = reorder_by_centroid(atoms)

            ref_coords_sorted = np.array([atom[1] for atom in ref_atoms_sorted])
            target_coords_sorted = np.array([atom[1] for atom in target_atoms_sorted])
            R = kabsch(ref_coords_sorted, target_coords_sorted)
            target_coords_aligned = np.dot(target_coords_sorted, R)

            reordered_atoms, hungarian_indices = reorder_atoms_hungarian(
                ref_atoms_sorted, [(atom[0], coord) for atom, coord in zip(target_atoms_sorted, target_coords_aligned)]
            )
            reordered_coords = np.array([atom[1] for atom in reordered_atoms])

            R_final = kabsch(ref_coords_sorted, reordered_coords)
            final_coords_aligned = np.dot(reordered_coords, R_final)

            rmsd = calculate_rmsd(ref_coords_sorted, final_coords_aligned)

            if rmsd < 0.2:
                combined_order = sort_indices[hungarian_indices[invert_positions(ref_sort_indices)]]
                return reordered_atoms, combined_order, ref_energy, energy

    return None, None, None, None


def main():
    """
    Main function that handles command-line arguments and executes the reordering process.
    """
    parser = argparse.ArgumentParser(description='Reorder molecular ensembles using RMSD matching.')
    parser.add_argument('ensemble_filename', type=str, help='XYZ file for the ensemble of target structures.')
    parser.add_argument('reference_ensemble_filename', type=str, help='XYZ file for the ensemble of reference structures.')
    parser.add_argument('output_filename', type=str, help='XYZ file to write the reordered structures.')

    args = parser.parse_args()

    ensemble_molecules = parse_xyz(args.ensemble_filename)
    reference_molecules = parse_xyz(args.reference_ensemble_filename)

    best_order_atoms, best_sort_order, ref_energy, target_energy = find_best_sort_order_ensemble(
        ensemble_molecules, reference_molecules
    )

    if best_sort_order is not None:
        print(f"Match found with RMSD < 0.1. Reference energy: {ref_energy}, Target energy: {target_energy}")
        ensemble_molecules = parse_xyz(args.ensemble_filename)
        reordered_ensemble = [reorder_molecule(molecule, best_sort_order) for molecule in ensemble_molecules]
        write_xyz(args.output_filename, reordered_ensemble)
        print(f"Reordered ensemble written to {args.output_filename}")
    else:
        print("No suitable order found in the reference ensemble.")


if __name__ == '__main__':
    main()

