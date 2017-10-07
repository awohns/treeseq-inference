#!/usr/bin/env python3
"""
Take an msprime simulation and output

a) The number & proportion of nodes with a mutation above them
b) The number 

"""
import sys
import os

from collections import defaultdict

script_path = __file__ if "__file__" in locals() else "./dummy.py"
sys.path.insert(1,os.path.join(os.path.dirname(os.path.abspath(script_path)),'..','msprime')) # use the local copy of msprime in preference to the global one
import msprime

for l in range(50000, 1500000, 50000):
    ts = msprime.simulate(
        2000, Ne=50000, length=l, recombination_rate=1e-8, mutation_rate=1e-8, random_seed=6)
        
        
    # Count number of nodes with mutations above them
    nodes_with_mutations = {m.node:True for m in ts.mutations()}
    
    # but some of these mutations will not be inherited by all genealogical descendants
    # as they may be recombined away. So we want to count all the uniquely distributed variants
    nodes_with_informative_mutations=defaultdict(list)
    for t in ts.variants(as_bytes=True):
        nodes_with_informative_mutations[t.genotypes].append(t.position)
    
    for 
    
    #iterate over the breakpoints with ts.breakpoints()
    
    nodes_with_recombinations = {}
    diff_iterator = ts.diffs()
    next(diff_iterator) #skip first diff
    for l_rec, o_rec, i_rec in diff_iterator:
        if len(o_rec)==len(i_rec) and len(o_rec)<4:
            oo_rec = {r[0]:r[1] for r in o_rec} #format is parent:(child1, child2)
            ii_rec = {r[0]:r[1] for r in i_rec}
            childen_of_unshared_out = [oo_rec[r] for r in set(oo_rec.keys()) - set(ii_rec.keys())]
            childen_of_unshared_in  = [ii_rec[r] for r in set(ii_rec.keys()) - set(oo_rec.keys())]
            assert len(childen_of_unshared_out)==len(childen_of_unshared_in)==1
            node = set(childen_of_unshared_in[0]) & set(childen_of_unshared_out[0])
            if len(o_rec) == 3:
                #should check  
            if len(node) == 1:
                #this is an informative mutation - we know which branch it is on
                #print("recombination unambiguously above node {} (cr length {})".format(node, len(o_rec)))
                nodes_with_recombinations[node.pop()] = True
            else 
                print("recombination position ambigous" + \
                    " could be above nodes {}".format(node))
        else:
            print("Not sure what's going on here: diff is {}, {} ,{}".format(
                l,o_rec,i_rec))
    print("For {:.3f}Mb {} nodes, {} ({:.2f}%) have mutations, {} ({:.2f}%) have recombinations, and {} ({:.2f}%) have neither".format(
        l/1e6, ts.get_num_nodes(), 
        len(nodes_with_mutations), len(nodes_with_mutations)/ts.get_num_nodes()*100,
        len(nodes_with_recombinations), len(nodes_with_recombinations)/ts.get_num_nodes()*100,
        ts.get_num_nodes()-len({**nodes_with_mutations, **nodes_with_recombinations}), 100-(len({**nodes_with_mutations, **nodes_with_recombinations})/ts.get_num_nodes()*100)))
    
    
    
