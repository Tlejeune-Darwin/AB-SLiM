import tskit
import msprime
import shutil
import random
import pyslim
import numpy as np
import pandas as pd
import os
import subprocess
import matplotlib.pyplot as plt
from IPython.display import display, SVG

# -------------------- Directory ------------------------

import os

# Define a base file where everything will be run
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Path of the currently running Python script

# Construct of the related paths
SLIM_SCRIPT = os.path.join(BASE_DIR, "Models", "Model_nWF_10.slim")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_trees")
TREE_FILE = os.path.join(OUTPUT_DIR, "simulation.trees")
RECAP_FILE = os.path.join(OUTPUT_DIR, "simulation_recap.trees")

print(f"📂 Dossier de base : {BASE_DIR}")
print(f"📄 Script SLiM : {SLIM_SCRIPT}")
print(f"📁 Dossier de sortie : {OUTPUT_DIR}")

# -------------------- Configuration --------------------

SLIM_SCRIPT = "Model_nWF_10.slim"  # SLiM script name
OUTPUT_DIR = "output_trees/"  # Directory where .trees files are stored
TREE_FILE = os.path.join(OUTPUT_DIR, "simulation.trees")  # File generated by SLiM
RECAP_FILE = os.path.join(OUTPUT_DIR, "simulation_recap.trees")  # File after recapitation
RECAP_Ne = 100  # Effective population size for recapitation
RECOMB_RATE = 0.5  # Recombination rate
MUT_RATE = 1e-2  # Mutation rate
HI = 100
LO = 5


# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -------------------- Run SLiM --------------------

# Automatically find SLiM on the computer
slim_path = shutil.which("slim")
if slim_path is None:
    raise FileNotFoundError("SLiM not found. Please define SLiM_PATH.")

# Make the dynamic command
log_file = os.path.join(OUTPUT_DIR, "simulation.log")
command = f'"{slim_path}" "{SLIM_SCRIPT}" > "{log_file}" 2>&1'

print(f"Launching SLiM : {command}")

if not os.path.exists(SLIM_SCRIPT):
    raise FileNotFoundError(f"Error : SLiM script {SLIM_SCRIPT} doesn't exist !")
else:
    print(f"SLiM script detected : {SLIM_SCRIPT}")

def run_slim():
    """ Run SLiM with generic path """
    log_file = os.path.join(OUTPUT_DIR, "simulation.log")
    command = f'"{slim_path}" "{SLIM_SCRIPT}" > "{log_file}" 2>&1'

    print(f"Run SLiM simulation : {command}")

    try:
        subprocess.run(command, shell=True, check=True)
        print(f"Simulation over, log saved to {log_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error while executing SLiM : {e}")

if __name__ == "__main__":
    run_slim()

# -------------------- Recapitation --------------------

def recapitate_tree():
    """ Performs recapitation on the .trees file """
    if not os.path.exists(TREE_FILE):
        print(f"Error: File {TREE_FILE} does not exist. Check SLiM execution.")
        exit(1)

    print(f"Loading file for recapitation: {TREE_FILE}")

    ts = tskit.load(TREE_FILE)

    print(f"Number of trees before recapitation: {ts.num_trees}")
    print(f"Number of sites before recapitation: {ts.num_sites}")
    print(f"Number of mutations before recapitation: {ts.num_mutations}")

    # Save a tree before recapitation
    save_tree_svg(ts, "tree_before_recap.svg")

    # Recapitate with msprime
    recap = pyslim.recapitate(ts, ancestral_Ne=RECAP_Ne, recombination_rate=RECOMB_RATE, random_seed=1)
    recap.dump(RECAP_FILE)

    print(f"Recapitation completed, file saved: {RECAP_FILE}")

    # Save a tree after recapitation
    save_tree_svg(recap, "tree_after_recap.svg")

    extract_mrca_info(recap)

    return recap

# -------------------- MRCA Extraction --------------------

def extract_mrca_info(ts):
    """ Extracts and prints the MRCA (Most Recent Common Ancestor) for each tree """
    print("\n Extracting MRCA for each tree...")

    for i, tree in enumerate(ts.trees()):
        # Get all sampled individuals (current population)
        samples = ts.samples()
        
        # Find the MRCA of all sampled individuals
        mrca = tree.mrca(*samples)
        
        # Get the time of the MRCA
        mrca_time = tree.time(mrca)
        
        print(f"Tree {i+1}: MRCA Node = {mrca}, Time = {mrca_time}")

    print("\n MRCA extraction completed.")


# -------------------- Add Mutations --------------------

def add_mutations(ts):
    """ Adds mutations after recapitation """
    print("Adding post-recapitation mutations...")

    mut_model = msprime.SMM(lo=LO, hi=HI)  # Stepwise Mutation Model with shifted values
    mut_ts = msprime.sim_mutations(ts, rate=MUT_RATE, model=mut_model, random_seed=42)

    print(f"Total number of mutations after msprime: {mut_ts.num_mutations}")

    for variant in mut_ts.variants():
        print(f"Site position: {variant.site.position}")
        print(f"Alleles: {variant.alleles}")
        print(f"Genotypes: {variant.genotypes}")

    mut_ts.dump(RECAP_FILE)  # Save mutations

    # Save a tree after mutation addition
    save_tree_svg(mut_ts, "tree_after_mutations.svg")

    return mut_ts

# -------------------- Save Trees --------------------

def save_tree_svg(ts, filename):
    """ Saves a tree in SVG format for visualization """
    tree = ts.first()
    svg_path = os.path.join(OUTPUT_DIR, filename)
    
    with open(svg_path, "w") as f:
        f.write(tree.draw_svg(size=(10000, 10000)))

    print(f"Tree saved: {svg_path}")

# -------------------- Main --------------------

if __name__ == "__main__":
    run_slim() # Run the SLiM script
    recap_ts = recapitate_tree()  # Recapitate the tree
    mut_ts = add_mutations(recap_ts)  # Add mutations
