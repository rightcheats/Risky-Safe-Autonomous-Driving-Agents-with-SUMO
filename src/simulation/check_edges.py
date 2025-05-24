import os
from sumolib import net

#TODO: check if this is obsolete - 

net_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "osm_data", "osm.net.xml.gz")
)

# load network and build set of valid ids
print(f"Loading network from {net_file}…")
net = net.readNet(net_file)
valid_edge_ids = {edge.getID() for edge in net.getEdges()}
print(f"Network contains {len(valid_edge_ids)} edges.\n")

# same routes from agent_manager.py
valid_routes = [
    ("-100306119", "-102745233"),
    ("-100306144", "-1040796649#1"),
    ("-1051388674#0", "-1052870930"),
    ("-1052870931", "-1054937080#1"),
    ("-1055385139#1", "-1065099801#1"),
    ("-1065099802#1", "-1065201821#0"),
    ("-493711858#1", "23120854#2"),
    ("-49797451#0", "2483868#0"),
    ("584351060", "-5067431#0"),
    ("-5067431#1", "-510234237#1"),
]

# check pairs
all_good = True
for start, end in valid_routes:
    ok_start = start in valid_edge_ids
    ok_end   = end   in valid_edge_ids

    if ok_start and ok_end:
        print(f"OK:   {start} → {end}")
    else:
        all_good = False
        missing = []
        if not ok_start: missing.append(start)
        if not ok_end:   missing.append(end)
        print(f"MISSING: {', '.join(missing)}")

if all_good:
    print("\nAll route edges are present in the network!")
else:
    print("\nSome edges from valid_routes were not found. Double‑check those IDs.")