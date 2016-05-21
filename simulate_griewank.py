#!/usr/bin/env python

import os
import sys
import time


WORK_DIR = "/home/users/s/aolszak/parampl"
LOG_SUBDIR = "g_logs"

AMPL_FILE = "griewank"



def sim(n, xmax, p, dim, ex, bsize):

	os.environ['griewank_n'] = str(n);
	os.environ['griewank_xmax'] = str(xmax);
	os.environ['griewank_p'] = str(p);
	os.environ['griewank_dim_p'] = str(dim);
	os.environ['griewank_ex'] = str(ex);
	os.environ['griewank_bsize'] = str(bsize);

	sys.stdout.write("n: " + str(n) + ", xmax: " + str(xmax) + ", p: " + str(p) + ", dim: " + str(dim) + ", ex: " + str(ex) + ", bsize: " + str(bsize) +"...\n");
	sys.stdout.flush();
	
	cmd = WORK_DIR + "/ampl " + WORK_DIR + "/" + AMPL_FILE + " > " + WORK_DIR + "/" + LOG_SUBDIR + "/griewank_" + str(n) + "_" + str(xmax) + "_" + str(p) + "_" + str(dim) + "_" + str(ex) + "_" + str(bsize) +"_log.txt";
	
	t1 = time.time();
	os.system(cmd);
	t2 = time.time();
	
	sys.stdout.write("Execution time: " + str(t2 - t1) + "s.\n\n");
	sys.stdout.flush();

	

if __name__=="__main__":	
	

	
	sim(4000, 600, 4, 1, 1, 4);
	sim(4000, 600, 4, 1, 2, 4);
	sim(4000, 600, 4, 1, 3, 4);
	
