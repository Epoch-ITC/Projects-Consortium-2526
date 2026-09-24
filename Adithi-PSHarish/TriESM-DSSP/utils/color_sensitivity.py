from pymol import cmd # load values 
sens = {} 
with open("sensitivity.txt") as f: 
    for line in f: 
        resi, val = line.split() 
        sens[int(resi)] = float(val) 
max_val = max(sens.values()) 
for resi, val in sens.items(): 
    color = val / max_val 
    cmd.set_color(f"col_{resi}", [color, 0, 1-color]) 
    cmd.color(f"col_{resi}", f"resi {resi}")