import matplotlib.pyplot as plt
import numpy as np

# Data
acids = {
    'Ar-OH': 19046, 'CO2H': 15962, 'N-H': 901, 'N-OH': 210, 
    'Csp3-NO2': 179, 'OH': 77, '1,3-Dicarb': 70, 'SH': 63, 'Ar-SH': 37
}

bases = {
    'Amine': 18254, 'Ar-N': 15672, '(Ar)N': 7781, 'Ar-N,(Ar)N': 497, 
    'Amidine': 94, 'Amide': 94, 'Guanidine': 68, 'Enamine': 47, 'Imine': 23
}

amphoterics = {
    'CO2H': 1547, 'NH': 49
}

# Calculate ratios based on the number of bars
ratios = [len(acids), len(bases), len(amphoterics)] 

# Setup Figure with proportional widths
fig, (ax1, ax2, ax3) = plt.subplots(
    1, 3, 
    figsize=(18, 5), 
    sharey=True,
    gridspec_kw={'width_ratios': ratios} # ensures the physical width of the plot matches the data count
)

# Plot 1: Acids (Red)
keys_a = list(acids.keys())
vals_a = list(acids.values())
ax1.bar(keys_a, vals_a, color='#d62728', alpha=0.8, edgecolor='black', width=0.8)
ax1.set_title('Acids (pKa)', fontsize=12, fontweight='bold')
ax1.set_ylabel('Count (Log Scale)', fontsize=10)
ax1.set_yscale('log') 
ax1.tick_params(axis='x', rotation=45, labelsize=9)
ax1.grid(axis='y', linestyle='--', alpha=0.3)

# Plot 2: Bases (Blue)
keys_b = list(bases.keys())
vals_b = list(bases.values())
ax2.bar(keys_b, vals_b, color='#1f77b4', alpha=0.8, edgecolor='black', width=0.8)
ax2.set_title('Bases (pKaH)', fontsize=12, fontweight='bold')
ax2.set_yscale('log')
ax2.tick_params(axis='x', rotation=45, labelsize=9)
ax2.grid(axis='y', linestyle='--', alpha=0.3)

# Plot 3: Amphoterics (Green)
keys_c = list(amphoterics.keys())
vals_c = list(amphoterics.values())
ax3.bar(keys_c, vals_c, color='#2ca02c', alpha=0.8, edgecolor='black', width=0.8)
ax3.set_title('Amphoterics', fontsize=12, fontweight='bold')
ax3.set_yscale('log')
ax3.tick_params(axis='x', rotation=45, labelsize=9)
ax3.grid(axis='y', linestyle='--', alpha=0.3)

# Adjust layout to prevent overlap
plt.tight_layout()
plt.savefig('fg_distribution.pdf', bbox_inches='tight')