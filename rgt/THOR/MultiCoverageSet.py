"""
THOR detects differential peaks in multiple ChIP-seq profiles between
two distinct biological conditions.

Copyright (C) 2014-2016 Manuel Allhof (allhoff@aices.rwth-aachen.de)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Manuel Allhoff
"""

from __future__ import print_function
import sys
import gc
from random import sample
import numpy as np
from normalize import get_normalization_factor
from DualCoverageSet import DualCoverageSet
from norm_genelevel import norm_gene_level
from rgt.CoverageSet import CoverageSet, get_gc_context
import configuration


class MultiCoverageSet(DualCoverageSet):

    def _help_init(self, signal_statics, inputs_statics, region_giver, norm_regionset, rmdup, binsize, stepsize, strand_cov):
        """Return self.covs and self.inputs as CoverageSet
        self._help_init(signal_statics, inputs_statics,region_giver, norm_regionset, rmdup, binsize, stepsize, strand_cov = strand_cov)
        But before we need to do statistics about the file, get information, how much read for this regions are in this fields..
        Better we need to do is get all info of all fields, and extract data from it to combine the training fields.
        Later we use the paras to estimate peaks.. Maybe according to regions
        mask_file is used to filter data before we do other operations.
        """
        # here we make covs into 2-D list
        self.covs = []
        self.covs_avg = []
        """
        for i, c in enumerate(self.covs):
            # c.get_statistics(path_bamfiles[i]) do statistics on the data in one bamfile, and return it
            # according to statistics, we decide if we continue later process
            # e.g. only one chromosome in data, then we process it directly, get samples from it and do peak-calling in it
            # if there are many chromosomes, we get samples according to these data and do peak-calling later.
            # c.statistics = c.get_statistics(path_bamfiles[i])
            # to make sure mask_file or mask_regions
            c.coverage_from_bam(bam_file=path_bamfiles[i], extension_size=exts[i], rmdup=rmdup, binsize=binsize,\
                                stepsize=stepsize, mask_file=region_giver.mask_file, get_strand_info = strand_cov)
        self.covs_avg = [CoverageSet('cov_avg' + str(i), region_giver.regionset) for i in range(2)]
        """
        for i in range(signal_statics['dim'][0]):
            self.covs.append([])
            self.covs_avg.append(CoverageSet('cov_avg' + str(i), region_giver.valid_regionset))
            for j in range(signal_statics['dim'][1]):
                self.covs[i].append(CoverageSet('file_' + str(i)+'_'+str(j), region_giver.valid_regionset))
                self.covs[i][j].coverage_from_bam(bam_file=signal_statics['data'][i][j]['fname'], extension_size=signal_statics['data'][i][j]['extension_size'], rmdup=rmdup, binsize=binsize,\
                                stepsize=stepsize, mask_file=region_giver.mask_file, get_strand_info = strand_cov)

        if inputs_statics:
            self.inputs_covs = []
            self.inputs_covs_avg = []

            for i in range(inputs_statics['dim'][0]):
                self.inputs_covs.append([])
                self.inputs_covs_avg.append(CoverageSet('inputs_cov_avg' + str(i), region_giver.valid_regionset))
                for j in range(inputs_statics['dim'][1]):
                    self.inputs_covs[i].append(CoverageSet('file_' + str(i) + '_' + str(j), region_giver.valid_regionset))
                    self.inputs_covs[i][j].coverage_from_bam(bam_file=inputs_statics['data'][i][j]['fname'],extension_size=inputs_statics['data'][i][j]['extension_size'],
                                                      rmdup=rmdup, binsize=binsize, stepsize=stepsize, mask_file=region_giver.mask_file, get_strand_info=strand_cov)
        else:
            self.inputs_covs = []
        """
        if norm_regionset:
            self.norm_regions = [CoverageSet('norm_region' + str(i), norm_regionset) for i in range(dim)]
            for i, c in enumerate(self.norm_regions):
                c.coverage_from_bam(bam_file=path_bamfiles[i], extension_size=exts[i], rmdup=rmdup, binsize=binsize,\
                                    stepsize=stepsize, mask_file=region_giver.mask_file, get_strand_info = strand_cov)
            self.input_avg = [CoverageSet('input_avg'  + str(i), region_giver.regionset) for i in range(2)]
        else:
            self.norm_regions = None
        """

    def _get_covs(self, DCS, i):
        """For a multivariant Coverageset, return coverage cov1 and cov2 at position i"""
        cov1 = int(np.mean(DCS.overall_coverage[0][:,DCS.indices_of_interest[i]]))
        cov2 = int(np.mean(DCS.overall_coverage[1][:,DCS.indices_of_interest[i]]))
    
        return cov1, cov2
    
    def _compute_gc_content(self, no_gc_content, inputs_statics, stepsize, binsize, genome_path, name, region_giver):
        """Compute GC-content, please pay attension to dimension changes!!!"""
        if not no_gc_content and inputs_statics and self.gc_content_cov is None:
            print("Compute GC-content", file=sys.stderr)
            for i, cov in enumerate(self.covs):
                inputs_cov = self.inputs_covs[i] #1 to 1 mapping between input and cov
                self.gc_content_cov, self.avg_gc_content, self.gc_hist = get_gc_context(stepsize, binsize, genome_path, inputs_cov.coverage, region_giver.get_chrom_dict())
                self._norm_gc_content(cov.coverage, self.gc_content_cov, self.avg_gc_content)
                self._norm_gc_content(inputs_cov.coverage, self.gc_content_cov, self.avg_gc_content)
            
                #if VERBOSE:
                #    self.print_gc_hist(name + '-s%s-rep%s-' %(sig, rep), gc_hist)
                #    cov.write_bigwig(name + '-s%s-rep%s-gc.bw' %(sig, rep), chrom_sizes)
        
    
    def _output_input_bw(self, name, chrom_sizes, save_wig):
        """print inputs bw"""
        for i in range(len(self.covs)):
            rep = i if i < self.dim_1 else i-self.dim_1
            sig = 1 if i < self.dim_1 else 2
            if self.inputs_covs:
                self.inputs_covs[i].write_bigwig(name + '-' + str(self.counter) + '-input-s%s-rep%s.bw' %(sig, rep), chrom_sizes, save_wig=save_wig, end=self.end)
    
    def _output_bw(self, name, chrom_sizes, save_wig, save_input):
        """Output bigwig files"""
        for i in range(len(self.covs)):
            rep = i if i < self.dim_1 else i-self.dim_1
            sig = 1 if i < self.dim_1 else 2
            
            self.covs[i].write_bigwig(name + '-' + str(self.counter) + '-s%s-rep%s.bw' %(sig, rep), chrom_sizes, save_wig=save_wig, end=self.end)
        
        #ra = [self.covs_avg, self.input_avg] if self.inputs else [self.covs_avg]
        #for k, d in enumerate(ra):
        #    g = self.covs if k == 0 else self.inputs
        #    for j in range(2):
        #        d[j] = deepcopy(g[0]) if j == 0 else deepcopy(g[self.dim_1])
        #        r = range(1, self.dim_1) if j == 0 else range(self.dim_1 + 1, self.dim_1 + self.dim_2)
        #        f = 1./self.dim_1 if j == 0 else 1./self.dim_2
        #        for i in r:
        #            d[j].add(g[i])
        #        d[j].scale(f)
        #        n = name + '-s%s.bw' %(j+1) if k == 0 else name + '-s%s-input.bw' %(j+1)
        #        d[j].write_bigwig(n, chrom_sizes, save_wig=save_wig, end=self.end)
        
        self.covs_avg = None
        self.input_avg = None
        if self.inputs_covs:
            for i in range(len(self.covs)):
                self.inputs_covs[i] = None #last time that we need this information, delete it
        gc.collect()
        
    
    def _help_get_data(self, i, type):
        if type != 'normregion':
            for j in range(len(self.covs[i].genomicRegions)):
                if type == 'cov':
                    yield self.covs[i].coverage[j]
                elif type == 'strand':
                    yield self.covs[i].cov_strand_all[j]
        elif type == 'normregion':
            for j in range(len(self.norm_regions[i].genomicRegions)):
                yield self.norm_regions[i].coverage[j]
    
    def _help_init_overall_coverage(self, cov_strand=True):
        """Convert coverage data (and optionally strand data) to matrix list"""
        
        tmp = [[], []]
        tmp2 = [[[], []], [[], []]]
        
        for k in range(2):
            it = range(self.dim_1) if k == 0 else range(self.dim_1, self.dim_1 + self.dim_2)
            for i in it:
                if cov_strand:
                    tmp_el = reduce(lambda x,y: np.concatenate((x,y)), self._help_get_data(i, 'cov'))
                    ## tmp_el is data for one bamfiles, then combine into all for one condition.
                    tmp[k].append(tmp_el)
                 
                    tmp_el = map(lambda x: (x[0], x[1]), reduce(lambda x,y: np.concatenate((x,y)), self._help_get_data(i, 'strand')))
                    tmp2[k][0].append(map(lambda x: x[0], tmp_el))
                    tmp2[k][1].append(map(lambda x: x[1], tmp_el))
                else:
                    tmp_el = reduce(lambda x,y: np.concatenate((x,y)), self._help_get_data(i, 'normregion'))
                    tmp[k].append(tmp_el)

        if cov_strand:
            #1. or 2. signal -> pos/neg strand -> matrix with rep x bins
            overall_coverage_strand = [[np.matrix(tmp2[0][0]), np.matrix(tmp2[0][1])], [np.matrix(tmp2[1][0]), np.matrix(tmp2[0][1])]]
            #list of matrices: #replicates (row) x #bins (columns)
            overall_coverage = [np.matrix(tmp[0]), np.matrix(tmp[1])]
            # overall_coverage combines two conditions together.
            return overall_coverage, overall_coverage_strand
        else:
            return [np.matrix(tmp[0]), np.matrix(tmp[1])]
    
    def count_positive_signal(self):
        return np.sum([self.covs[i][j].coverage for j in range(self.dim[1]) for i in range(self.dim[0])])
    
    def __init__(self, name, region_giver, genome_path, binsize, stepsize, norm_regionset, \
                 verbose, debug, no_gc_content, rmdup, signal_statics, inputs_statics, \
                 factors_inputs, scaling_factors_ip, save_wig, strand_cov, housekeeping_genes,\
                 tracker, end, counter, gc_content_cov=None, avg_gc_content=None, gc_hist=None, output_bw=True,\
                 folder_report=None, report=None, save_input=False, m_threshold=80, a_threshold=95, ignored_regions=None):
        """Compute CoverageSets, GC-content and normalize input-DNA and IP-channel"""
        # one improvement is to make the left one key_word parameter and we parse it, not like this, all in a list
        """    
        regionset = region_giver.regionset
        chrom_sizes = region_giver.chrom_sizes_file
        chrom_sizes_dict = region_giver.get_chrom_dict()
        """
        self.region_giver = region_giver
        self.binsize = binsize
        self.stepsize = stepsize
        self.name = name
        self.dim = signal_statics['dim']
        self.gc_content_cov = gc_content_cov
        self.avg_gc_content = avg_gc_content
        self.gc_hist = gc_hist
        self.scaling_factors_ip = scaling_factors_ip
        self.factors_inputs = factors_inputs
        self.end = end
        self.counter = counter # use of counter ???
        self.no_data = False
        self.FOLDER_REPORT = folder_report

        configuration.DEBUG = debug
        configuration.VERBOSE = verbose
        
        #make data nice
        self._help_init(signal_statics, inputs_statics,region_giver, norm_regionset, rmdup, binsize, stepsize, strand_cov = strand_cov)
        if self.count_positive_signal() < 1:
            self.no_data = True
            return None
        self._compute_gc_content(no_gc_content, inputs_statics, stepsize, binsize, genome_path, name, region_giver)
        self._normalization_by_input(signal_statics, inputs_statics, name, factors_inputs, save_input)
        if save_input:
            self._output_input_bw(name, region_giver.chrom, save_wig)
            
        self.overall_coverage, self.overall_coverage_strand = self._help_init_overall_coverage(cov_strand=True)

        # much complex, so we decay to change it
        #self._normalization_by_signal(name, scaling_factors_ip, path_bamfiles, housekeeping_genes, tracker, norm_regionset, report,
        #                              m_threshold, a_threshold)
        ## After this step, we have already normalized data, so we could output normalization data

        if output_bw:
            self._output_bw(name, region_giver.chrom_sizes_file, save_wig, save_input)
        
        self.scores = np.zeros(len(self.overall_coverage[0]))
        self.indices_of_interest = []
    
    def get_max_colsum(self):
        """Sum over all columns and add maximum"""
        return self.overall_coverage[0].sum(axis=0).max() + self.overall_coverage[1].sum(axis=0).max()
    
    def output_overall_coverage(self, path):
        for j in range(2):
            f = open(path + str(j), 'w')
            for i in range(self.overall_coverage[j].shape[1]):
                print(self.overall_coverage[j][:,i].T, file=f)
    
    def _normalization_by_input(self, signal_statics, inputs_statics, name, factors_inputs, save_input):
        """Normalize input-DNA. Use predefined factors or follow Diaz et al, 2012"""
        
        if configuration.VERBOSE:
            print("Normalize input-DNA", file=sys.stderr)
        
        if factors_inputs:
            if configuration.VERBOSE:
                print("Use with predefined factors", file=sys.stderr)
            for i in range(signal_statics['dim'][0]):
                for j in range(signal_statics['dim'][1]):
                    self.inputs_covs[i][j].scale(factors_inputs[i][i])
                    self.covs[i][j].subtract(self.inputs_covs[i][j])
        elif inputs_statics:
            factors_inputs = []
            print("Compute factors", file=sys.stderr)

            """  
            for i in range(len(path_bamfiles)):
                rep = i if i < self.dim_1 else i-self.dim_1
                sig = 0 if i < self.dim_1 else 1
                j = 0 if i < self.dim_1 else 1
                _, n = get_normalization_factor(path_bamfiles[i], path_inputs[i], step_width=1000, zero_counts=0, \
                                                filename=name + '-norm' + str(i), debug=configuration.DEBUG, chrom_sizes_dict=self.chrom_sizes_dict, two_sample=False, stop=True)
                if n is not None:
                    print("Normalize input of Signal %s, Rep %s with factor %s"\
                           %(sig, rep, round(n, configuration.ROUND_PRECISION)) , file=sys.stderr)
                    self.inputs_covs[i].scale(n)
                    ## this is where we should look into the codes.... If after doing inputs, all data turn into zeros...
                    self.covs[i].subtract(self.inputs_covs[i])
                    factors_inputs.append(n)
            """
            for i in range(signal_statics['dim'][0]):
                factors_inputs.append([])
                for j in range(signal_statics['dim'][1]):
                    _, n = get_normalization_factor(signal_statics['data'][i][j]['fname'], inputs_statics['data'][i][j]['fname'], step_width=1000, zero_counts=0, \
                                                    filename=name + '-norm' + str(i), debug=configuration.DEBUG,
                                                    chrom_sizes_dict=self.region_giver.get_chrom_dict(), two_sample=False, stop=True)
                if n:
                    print("Normalize input of Signal %s, Rep %s with factor %s" \
                          % (i, j, round(n, configuration.ROUND_PRECISION)), file=sys.stderr)
                    self.inputs_covs[i][j].scale(n)
                    ## this is where we should look into the codes.... If after doing inputs, all data turn into zeros...
                    self.covs[i][j].subtract(self.inputs_covs[i][j])
                    factors_inputs[i].append(n)

        self.factors_inputs = factors_inputs
        
                    
    def _trim4TMM(self, m_values, a_values, m_threshold=80, a_threshold=95):
        """q=20 or q=5"""
        assert len(m_values) == len(a_values)
        # np.isinf return an array to test if infinite, only two columns are not infinite we return False, after not x, we get True
        # mask = np.asarray([not x for x in np.isinf(m_values) + np.isinf(a_values)])
        # but after last step, we have make sure that there is no zeros, and no infinity, then we don't need the step to filter it.
        # m_values = m_values[mask]
        # a_values = a_values[mask]
        
        perc_m_l = np.percentile(m_values, 100-m_threshold)
        perc_m_h = np.percentile(m_values, m_threshold)
        perc_a_l = np.percentile(a_values, 100-a_threshold)
        perc_a_h = np.percentile(a_values, a_threshold)
        
        try:
            res = filter(lambda x: not(x[0]>perc_m_h or x[0]<perc_m_l),\
                     filter(lambda x: not(x[1]>perc_a_h or x[1]<perc_a_l), zip(list(m_values.squeeze()),list(a_values.squeeze()))))
        except:
            print('something wrong %s %s' %(len(m_values), len(a_values)), file=sys.stderr)
            return np.asarray(m_values), np.asarray(a_values)
        
        if res:
            return np.asarray(map(lambda x: x[0], res)), np.asarray(map(lambda x: x[1], res))
        else:
            print('TMM normalization: nothing trimmed...', file=sys.stderr)
            return np.asarray(m_values), np.asarray(a_values)
    
    def _norm_TMM(self, overall_coverage, m_threshold, a_threshold):
        """Normalize with TMM approach, based on PePr
          ref, we use the mean of two samples and compare to it
          data_rep present the data.. But a
        """
        scaling_factors_ip = []
        # mask_ref filter out columns with zero at least for two samples..
        mask_ref = np.all(np.all(np.asarray(overall_coverage) > 0, axis=0), axis=0)
        ref = np.squeeze(np.asarray(np.sum(overall_coverage[0][:,mask_ref], axis=0) + np.sum(overall_coverage[1][:,mask_ref], axis=0)) / float(self.dim_1 + self.dim_2))

        # ref = np.squeeze(np.asarray(np.sum(overall_coverage[j][:, mask_ref], axis=0) / float(cond_max)))
        for j, cond_max in enumerate([self.dim_1, self.dim_2]):

            for i in range(cond_max): #normalize all replicates
                # get the data for each sample under each condition
                data_rep = np.squeeze(np.asarray(overall_coverage[j][i,mask_ref]))
                tmp_idx = sample(range(len(data_rep)), min(len(data_rep), 10000)) # sampling data
                tmp_ref = ref[tmp_idx]  # use index to make ref and data correspond
                data_rep = data_rep[tmp_idx]
                # calculate m_values and a_values
                m_values = np.log(tmp_ref / data_rep)
                a_values = 0.5 * np.log(data_rep * tmp_ref)
                try: # assume they have a relations and then plot them to get scale factor.
                    m_values, a_values = self._trim4TMM(m_values, a_values, m_threshold, a_threshold)
                    f = 2 ** (np.sum(m_values * a_values) / np.sum(a_values))
                    scaling_factors_ip.append(f)
                except:
                    print('TMM normalization not successfully performed, do not normalize data', file=sys.stderr)
                    scaling_factors_ip.append(1)
                
        return scaling_factors_ip
    
    def _normalization_by_signal(self, name, scaling_factors_ip, bamfiles, housekeeping_genes, tracker, norm_regionset, report,
                                 m_threshold, a_threshold):
        """Normalize signal. comparing data to data"""
        
        if configuration.VERBOSE:
            print('Normalize ChIP-seq profiles', file=sys.stderr)
        
        if not scaling_factors_ip and housekeeping_genes:
            print('Use housekeeping gene approach', file=sys.stderr)
            scaling_factors_ip, _ = norm_gene_level(bamfiles, housekeeping_genes, name, verbose=True, folder = self.FOLDER_REPORT, report=report)
        elif not scaling_factors_ip:
            if norm_regionset:
                print('Use TMM approach based on peaks', file=sys.stderr)
                norm_regionset_coverage = self._help_init_overall_coverage(cov_strand=False) #TMM approach based on peaks
                scaling_factors_ip = self._norm_TMM(norm_regionset_coverage,m_threshold, a_threshold)
            else:
                print('Use global TMM approach ', file=sys.stderr)
                scaling_factors_ip = self._norm_TMM(self.overall_coverage, m_threshold, a_threshold) #TMM approach
        
        for i in range(len(scaling_factors_ip)):
            self.covs[i].scale(scaling_factors_ip[i]) 
        
        if scaling_factors_ip:
            for j, cond in enumerate([self.dim[0], self.dim[1]]):
                for i in range(cond): #normalize all replicates
                    k = i if j == 0 else i+self.dim[0]
                    self.overall_coverage[j][i,:] *= scaling_factors_ip[k]
                    if configuration.DEBUG:
                        print('Use scaling factor %s' %round(scaling_factors_ip[k], configuration.ROUND_PRECISION), file=sys.stderr)
        
        self.scaling_factors_ip = scaling_factors_ip
        
        
        
                
    def _index2coordinates(self, index):
        """Translate index within coverage array to genomic coordinates."""
        iter = self.genomicRegions.__iter__()
        r = iter.next()
        sum = r.final
        last = 0
        i = 0
        while sum <= index * self.stepsize:
            last += len(self.covs[0].coverage[i])
            try:
                r = iter.next()
            except StopIteration:
                sum += r.final
                i += 1
                break
            sum += r.final
            i += 1
        
        return r.chrom, (index-last) * self.stepsize, \
            min((index-last) * self.stepsize + self.stepsize, r.final)
                              
    def __len__(self):
        """Return number of observations."""
        return len(self.indices_of_interest)
    
    def get_observation(self, mask=np.array([])):
        """Return indices of observations. Do not consider indices contained in <mask> array"""
        mask = np.asarray(mask)
        if not mask.size:
            mask = np.array([True]*self._get_bin_number())
        return np.asarray(np.concatenate((self.overall_coverage[0][:,mask].T, self.overall_coverage[1][:,mask].T), axis=1))
    
    def _compute_score(self):
        """Compute score for each observation (based on Xu et al.)"""
        # after np.squeeze, we remove single-dimensional entry.. What does it make ??? seems nothing about process
        # interest_region is column scores are greater than one values...
        # self.scores = np.sum(np.asarray([np.squeeze(np.asarray(self.overall_coverage[i][j])) /float(np.sum(self.overall_coverage[i][j])) for j in xrange(self.dim_2) for i in range(self.dim_1)]), axis=0)/self.dim_2
        # old methods to count interest regions
        self.scores = sum([np.squeeze(np.asarray(np.mean(self.overall_coverage[i], axis=0))) / float(np.mean(self.overall_coverage[i])) for i in range(2)])

    def _get_bin_number(self):
        """Return number of bins"""
        return self.overall_coverage[0].shape[1]
    
    def compute_putative_region_index(self, l=5):
        """Compute putative differential peak regions as follows: 
        - score must be > 0, i.e. everthing
        - overall coverage in library 1 and 2 must be > 3"""
        
        try:
            self._compute_score()
            # threshold = 2.0 / (self.scores.shape[0])  # before it's considered if it's zero, now add some thresholds.
            threshold = 0.0
            self.indices_of_interest = np.where(self.scores > threshold)[0] #2/(m*n) thres = 2 /(self.scores.shape[0])
            tmp = np.where(np.squeeze(np.asarray(np.mean(self.overall_coverage[0], axis=0))) + np.squeeze(np.asarray(np.mean(self.overall_coverage[1], axis=0))) > 10)[0]
            tmp2 = np.intersect1d(self.indices_of_interest, tmp)
            self.indices_of_interest = tmp2
        except:
            self.indices_of_interest = None


    def write_test_samples(self, name, l):
        f = open(name, 'w')
        
        for el1, el2 in l:
            print(el1, el2, sep='\t', file=f)
        f.close()
    
    def output_training_set(self, name, training_set, s0_v, s1_v, s2_v):
        """Output debug info for training_set computation."""
        f=open(name + '-trainingset.bed', 'w')
        for l in training_set:
            chrom, s, e = self._index2coordinates(l)
            print(chrom, s, e, sep ='\t', file=f)
        f.close()
        
        self.write_test_samples(name + '-s0', s0_v)
        self.write_test_samples(name + '-s1', s1_v)
        self.write_test_samples(name + '-s2', s2_v)
    
    def get_training_set(self, test, exp_data, name, foldchange, min_t, y=1000, ex=2):
        """Return HMM's training set (max <y> positions). Enlarge each contained bin by <ex>.
           If first sample can't represent data, we need to resample it from population, self.indices_of_interest..
           Other way, we could build the samples for training, but then it will cause other troubles, maybe...
           we need to filter data, make diff_cov firstly non zeros and then get half part from it..s
        """
        threshold = foldchange
        diff_cov = int(np.percentile(filter(lambda x: x>0, np.abs(np.squeeze(np.asarray(np.mean(self.overall_coverage[0], axis=0))) - \
                                            np.squeeze(np.asarray(np.mean(self.overall_coverage[1], axis=0))))), min_t))

        if test:
            diff_cov, threshold = 2, 1.5
        
        if configuration.DEBUG:
            print('Training set parameters: threshold: %s, diff_cov: %s' %(threshold, diff_cov), file=sys.stderr)
        
        s0, s1, s2 , tmp = [], [], [], []
        
        # compute training set parameters, re-compute training set if criteria do not hold
        print('The length of indices_of_interest')
        print(len(self.indices_of_interest))
        rep=True
        while rep:

            if diff_cov == 1 and threshold == 1.1:
                print("No differential peaks detected", file=sys.stderr)
                sys.exit()
            steps = 0
            for i in sample(range(len(self.indices_of_interest)), len(self.indices_of_interest)):
                cov1, cov2 = self._get_covs(exp_data, i)
                steps += 1
                #apply criteria for initial peak calling
                if ((cov1 +1 ) / (float(cov2) + 1) > threshold and cov1+cov2 > diff_cov/2) or cov1-cov2 > diff_cov:
                    s1.append((self.indices_of_interest[i], cov1, cov2))
                elif ((cov1 + 1) / (float(cov2) + 1) < 1/threshold and cov1+cov2 > diff_cov/2) or cov2-cov1 > diff_cov:
                    s2.append((self.indices_of_interest[i], cov1, cov2))
                else:
                    s0.append((self.indices_of_interest[i], cov1, cov2))
            
                if steps % 500 == 0 and len(s0) > y and len(s1) > y and len(s2) > y:
                    tmp = []
                    for el in [s0, s1, s2]:
                        el = np.asarray(el)
                        if not test:
                            el = el[
                                np.logical_and(
                                    el[:, 1] < np.percentile(el[:, 1], 97.5) * (el[:, 1] > np.percentile(el[:, 1], 2.5)),
                                    el[:, 2] < np.percentile(el[:, 2], 97.5) * (el[:, 2] > np.percentile(el[:, 2], 2.5))),:]

                        tmp.append(el)

                    l = np.min([len(tmp[0]), len(tmp[1]), len(tmp[2])])
                    if l >= y:
                        break
            
            if len(s1) < 100/2 and len(s2) > 2*100:
                s1 = map(lambda x: (x[0], x[2], x[1]), s2)
            if len(s2) < 100/2 and len(s1) > 2*100:
                s2 = map(lambda x: (x[0], x[2], x[1]), s1)
            
            if len(s1) < 100 or len(s2) < 100:
                diff_cov -= 15
                threshold -= 0.1
                diff_cov = max(diff_cov, 1)
                threshold = max(threshold, 1.1)
            else:
                rep = False
        
        if configuration.DEBUG:
            print('Final training set parameters: threshold: %s, diff_cov: %s' %(threshold, diff_cov), file=sys.stderr)
        
        #optimize training set, extend each bin
        # here we need to combine data to sample all data, if they are not meet our requirements, we need to sample from all population data
        # and the population data are directly from interest_of_points..
        if tmp == [] :
            for el in [s0, s1, s2]:
                el = np.asarray(el)
                if not test:
                    el = el[np.where(
                        np.logical_and(el[:, 1] < np.percentile(el[:, 1], 97.5) * (el[:, 1] > np.percentile(el[:, 1], 2.5)),
                                       el[:, 2] < np.percentile(el[:, 2], 97.5) * (el[:, 2] > np.percentile(el[:, 2], 2.5))))]

                tmp.append(el)

            l = np.min([len(tmp[0]), len(tmp[1]), len(tmp[2]), y])

        print('the smallest length l is %d between %d, %d, %d, %d'%(l,y, len(tmp[0]),len(tmp[1]),len(tmp[2])))
        s0 = sample(tmp[0], l)
        s1 = sample(tmp[1], l)
        s2 = sample(tmp[2], l)

        tmp2 = []
        for i, ss in enumerate([s0, s1, s2]):
            while np.any(np.sum(ss, axis=0) < len(ss)):
                print('resample because data is not spatial')
                ss = sample(tmp[i], l)
            tmp2.append(ss)

        s0_v = map(lambda x: (x[1], x[2]), tmp2[0])
        s1_v = map(lambda x: (x[1], x[2]), tmp2[1])
        s2_v = map(lambda x: (x[1], x[2]), tmp2[2])

        
        extension_set = set()
        for i, _, _ in s0 + s1 + s2:
            for j in range(max(0, i - ex), i + ex + 1): #extend bins
                extension_set.add(j)
         
        tmp = s0 + s1 + s2
        training_set = map(lambda x: x[0], tmp) + list(extension_set)
         
        training_set = list(training_set)
        training_set.sort()
        
        if configuration.DEBUG:
            self.output_training_set(name, training_set, s0_v, s1_v, s2_v)
        
        return training_set, s0_v, s1_v, s2_v
