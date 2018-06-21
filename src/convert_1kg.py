"""
Example script for importing 1000 Genomes data.
"""
import argparse
import subprocess
import os
import shutil
import sys
import mmap

import numpy as np
import msprime
import tsinfer
import attr
import cyvcf2
import tqdm

def get_num_lines(file_path):
    fp = open(file_path, "r+")
    buf = mmap.mmap(fp.fileno(), 0)
    lines = 0
    while buf.readline():
        lines += 1
    return lines
    
    
@attr.s()
class Site(object):
    position = attr.ib(None)
    alleles = attr.ib(None)
    genotypes = attr.ib(None)
    metadata = attr.ib({})

def add_populations(sample_data):
    """
    Adds the 1000 genomes populations to the sample_data and return the mapping
    of names (e.g. CHB) to IDs (e.g., 0).
    """
    # Based on
    # http://www.internationalgenome.org/faq/which-populations-are-part-your-study/
    populations = [
        ["CHB", "Han Chinese in Beijing, China", "EAS"],
        ["JPT", "Japanese in Tokyo, Japan", "EAS"],
        ["CHS", "Southern Han Chinese", "EAS"],
        ["CDX", "Chinese Dai in Xishuangbanna, China", "EAS"],
        ["KHV", "Kinh in Ho Chi Minh City, Vietnam", "EAS"],
        ["CEU", "Utah Residents (CEPH) with Northern and Western European Ancestry",
            "EUR"],
        ["TSI", "Toscani in Italia", "EUR"],
        ["FIN", "Finnish in Finland", "EUR"],
        ["GBR", "British in England and Scotland", "EUR"],
        ["IBS", "Iberian Population in Spain", "EUR"],
        ["YRI", "Yoruba in Ibadan, Nigeria", "AFR"],
        ["LWK", "Luhya in Webuye, Kenya", "AFR"],
        ["GWD", "Gambian in Western Divisions in the Gambia", "AFR"],
        ["MSL", "Mende in Sierra Leone", "AFR"],
        ["ESN", "Esan in Nigeria", "AFR"],
        ["ASW", "Americans of African Ancestry in SW USA", "AFR"],
        ["ACB", "African Caribbeans in Barbados", "AFR"],
        ["MXL", "Mexican Ancestry from Los Angeles USA", "AMR"],
        ["PUR", "Puerto Ricans from Puerto Rico", "AMR"],
        ["CLM", "Colombians from Medellin, Colombia", "AMR"],
        ["PEL", "Peruvians from Lima, Peru", "AMR"],
        ["GIH", "Gujarati Indian from Houston, Texas", "SAS"],
        ["PJL", "Punjabi from Lahore, Pakistan", "SAS"],
        ["BEB", "Bengali from Bangladesh", "SAS"],
        ["STU", "Sri Lankan Tamil from the UK", "SAS"],
        ["ITU", "Indian Telugu from the UK", "SAS"],
    ]
    id_map = {}
    for pop in populations:
        pop_id = sample_data.add_population(
            dict(zip(["name", "description", "super_population"], pop)))
        id_map[pop[0]] = pop_id
    return id_map

def filter_duplicates(vcf):
    """
    Returns the list of variants from this specified VCF with duplicate sites filtered
    out. If any site appears more than once, throw all variants away.
    """
    # TODO this has not been tested properly.
    row = next(vcf, None)
    bad_pos = -1
    for next_row in vcf:
        if bad_pos == -1 and next_row.POS != row.POS:
            yield row
        else:
            if bad_pos == -1:
                bad_pos = row.POS
            elif bad_pos != next_row.POS:
                bad_pos = -1
        row = next_row
    if row is not None and bad_pos != -1:
        yield row

def vcf_num_rows(vcf_path):
    """A quick way to get the number of sites in a vcf"""
    if not os.path.exists(vcf_path + ".csi"):
        subprocess.call(["bcftools", "index", vcf_path])
    output = subprocess.check_output(["bcftools", "index", "--nrecords", vcf_path])
    return int(output)


def variants(vcf_path, show_progress=False, ancestral_states=None):
    """
    Yield a tuple of position, alleles, genotypes, metadata
    If ancestral_states is given, it should be a dictionary mapping name to state
    """
    tot_sites = vcf_num_rows(vcf_path)
    progress = tqdm.tqdm(total=tot_sites, desc="Read sites", disable=not show_progress)

    vcf = cyvcf2.VCF(vcf_path)

    sites_used = non_biallelic = non_diploid = no_ancestral_state = missing_data = 0
    num_diploids = len(vcf.samples)
    num_samples = 2 * num_diploids
    j = 0
    for row in filter_duplicates(vcf):
        progress.update()
        skip = False
        ancestral_state = None
        try:
            if ancestral_states is not None:
                aa = ancestral_states[row.ID]
            else:
                aa = row.INFO["AA"]
            # Format: for indels = AA|REF|ALT|IndelType; for SNPs = AA
            splits = aa.split("|")
            if len(splits[0]) == 1:
                base = splits[0].upper()
                if base in "ACTG":
                    ancestral_state = base
        except KeyError:
            pass
        #only use biallelic sites with data for all samples, where ancestral state is known
        if len(row.ALT)!=1:
            non_biallelic += 1
            skip = True
        if ancestral_state is None:
            no_ancestral_state += 1
            skip = True
        if row.num_called != num_diploids:
            missing_data += 1
            skip = True
        if not skip:
            a = np.zeros(num_samples, dtype=np.uint8)
            all_alleles = set([ancestral_state])
            # Fill in a with genotypes.
            bases = np.array(row.gt_bases)
            for j in range(num_diploids):
                alleles = bases[j].split("|")
                for allele in alleles:
                    all_alleles.add(allele)
                a[2 * j] = alleles[0] != ancestral_state
                a[2 * j + 1] = alleles[1] != ancestral_state
            if len(all_alleles) != 2:
                non_diploid += 1
            else:
                all_alleles.remove(ancestral_state)
                alleles = [ancestral_state, all_alleles.pop()]
                metadata = {"ID": row.ID, "INFO": dict(row.INFO)}
                sites_used += 1
                yield Site(
                    position=row.POS, alleles=alleles, genotypes=a, metadata=metadata)
    vcf.close()
    print("Used {} out of {} sites. {} non biallelic, {} without ancestors, {} with missing data, and {} not diploid".format(
        sites_used, tot_sites, non_biallelic, no_ancestral_state, missing_data, non_diploid))

def add_samples(ped_file, population_id_map, individual_names, sample_data, show_progress=False):
    """
    Reads the specified PED file to get information about the samples.
    Assumes that the population IDs have already been allocated and
    the individuals are to be added in the order in the specified list.
    """
    columns = next(ped_file).split("\t")
    sane_names = [col.replace(" ", "_").lower().strip() for col in columns]
    rows = {}
    for line in tqdm.tqdm(ped_file, total=get_num_lines(ped_file.name), 
        desc="Read population data", disable=not show_progress):
        metadata = dict(zip(sane_names, line.strip().split("\t")))
        metadata["population"] = population_id_map[metadata["population"]]
        name = metadata["individual_id"]
        # The value '0' seems to be used to encode missing, so insert None
        # instead to be more useful.
        nulled = {}
        for key, value in metadata.items():
            if value == "0":
                value = None
            nulled[key] = value
        rows[name] = nulled

    # Add in the metadata rows in the order of the VCF.
    for name in tqdm.tqdm(individual_names, desc="Adding sites", disable=not show_progress):
        metadata = rows[name]
        sample_data.add_individual(metadata=metadata, ploidy=2)    

def convert(vcf_file, pedigree_file, output_file, 
    max_variants=None, show_progress=False, ancestor_file=None):

    if max_variants is None:
        max_variants = 2**32  # Arbitrary, but > defined max for VCF

    sample_data = tsinfer.SampleData(path=output_file, num_flush_threads=2)
    pop_id_map = add_populations(sample_data)
    
    vcf = cyvcf2.VCF(vcf_file)
    individual_names = list(vcf.samples)
    vcf.close()

    with open(pedigree_file, "r") as ped_file:
        add_samples(ped_file, pop_id_map, individual_names, sample_data, show_progress)

    if ancestor_file is not None:
        ancestors = {}
        sites=vcf_num_rows(ancestor_file)
        vcf = cyvcf2.VCF(ancestor_file)
        for site in tqdm.tqdm(
            vcf, total=sites, desc="Getting ancestors", disable=not show_progress):
            if site.ID:
                try:
                    ancestors[site.ID] = site.INFO["AA"]
                except KeyError:
                    pass
        vcf.close()
        if show_progress:
            print("Read {} ancestral alleles out of {} sites from {}".format(
                len(ancestors), sites, ancestor_file))
    else:
        ancestors = None

    for index, site in enumerate(variants(vcf_file, show_progress, ancestors)):
        sample_data.add_site(site.position, site.genotypes, site.alleles, site.metadata)
        if index == max_variants:
            break
    sample_data.finalise(command=sys.argv[0], parameters=sys.argv[1:])


def main():
    parser = argparse.ArgumentParser(
        description="Script to convert VCF files into tsinfer input.")
    parser.add_argument(
        "vcf_file",
        help="The input VCF file. E.g. from http://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/supporting/GRCh38_positions/")
    parser.add_argument(
        "pedigree_file",
        help="The pedigree file containing population and sample data, e.g. ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/technical/working/20130606_sample_info/20130606_g1k.ped")
    parser.add_argument(
        "output_file",
        help="The tsinfer output file")
    parser.add_argument(
        "-a", "--ancestors_file", default=None, 
        help="A vcf file containing ancestral allele states. This will override ancestral alleles from the main vcf. E.g. ftp://ftp.ensembl.org/pub/release-92/variation/vcf/homo_sapiens/homo_sapiens.vcf.gz. To save time, you may want to restrict this to ")
    parser.add_argument(
        "-n", "--max-variants", default=None, type=int,
        help="Keep only the first n variants")
    parser.add_argument(
        "-p", "--progress", action="store_true")

    args = parser.parse_args()

    if not os.path.exists(args.vcf_file):
        raise ValueError("{} does not exist".format(args.vcf_file))
    if not os.path.exists(args.pedigree_file):
        raise ValueError("{} does not exist".format(args.pedigree_file))


    convert(
        args.vcf_file, args.pedigree_file, args.output_file, args.max_variants, 
        show_progress=args.progress, ancestor_file = args.ancestors_file)


if __name__ == "__main__":
    main()