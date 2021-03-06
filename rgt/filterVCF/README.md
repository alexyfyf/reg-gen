README for rgt-filterVCF

rgt-filterVCF is designed to filter variants described by VCF files.

# Installation

Type the following commands:

```
svn checkout http://reg-gen.googlecode.com/svn/trunk/ reg-gen-read-only
cd reg-gen-read-only
sudo apt-get install python-numpy python-scipy zlib1g-dev python-setuptools; 
sudo python setup.py install --rgt-tool=filterVCF
```

# Usage

Create a space delimited config file with sample's name and samples's VCF file:

Something like:

```
p01 /home/manuel/data/humangenetics/01_S1_L001_R1_001.filtered.vcf
p11 /home/manuel/data/humangenetics/11_S2_L001_R1_001.filtered.vcf
p12 /home/manuel/data/humangenetics/12_S3_L001_R1_001.filtered.vcf
p18 /home/manuel/data/humangenetics/18_S4_L001_R1_001.filtered.vcf
p25 /home/manuel/data/humangenetics/25_S5_L001_R1_001.filtered.vcf
```

If desired, create a config file for wildtypes.

Type

```
rgt-filterVCF -h
```

to get an overview of the parameters you can set and their default values.

Type 

```
rgt-filterVCF file.config
```

to run the filter-pipeline on the samples described in file.config.

Type for example

```
rgt-filterVCF file.config --t-mq 30 --t-dp 40 --dbSNP --list-WT file_wt.config --bed motifs.bed --max-density
```

to run the pipeline with the following configuration:

- filter out all variants with mapping quality (MQ) < 30
- filter out all variants with combined depth (DP) < 40
- filter out all variants that occur in dbSNP
- subtract all samples' variants with variants described in file file_wt.config
- filter out all variants that do now lay in regions defined by file motifs.bed
- search for max. density regions of homozygous SNPs

# Output

rgt-filterVCF saves VCF files:
- for each sample a VCF file is created that contains the filtered variants
- for each possible intersection of samples' subsets one VCF file is created (see Pipeline for details)

rgt-filter writes to stderr (i.e. to the terminal) information of the pipeline's progress. 
It furthermore gives out the resulting number of variants for each sample after each pipeline step.

To forward the stderr output to a file, use

```
rgt-filterVCF file.config > pipeline.output 2>&1
```

By using the expression `2>&1`, the stderr will be stored in file pipeline.output.

# Pipeline

The pipeline to filter the samples' variants consists of several pre-determined steps:

1. filter by MQ
2. filter by DP
3. filter by dbSNP (optional, set parameter --dbSNP)
4. if wildtypes are available:
  1. pool all wildtypes' variants
  2. filter wildtypes by MQ, DP and dbSNP (optional)
  3. for each sample: subtract sample's variants from wildtypes' variants
5. perform max. density search on samples's variants (optional)
6. filter by BED file (optional), keep variants that lay in regions given by BED file
7. compute every (non trivial) possible subsets of samples and give VCF file of common variants,
    e.g.: for given samples p1, p2, p3, compute the intersection of variants of 
    <p1, p2>, <p2, p3> and <p1, p2, p3>. 
    Output the size of the intersection (=shared variants), and save corresponding VCF file
	
	Typically, we hope that 1 variant is found in the intersection of <p1, p2, p3> (i.g. all samples).
	