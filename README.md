# xtalkit

## clustalx.py

A convenient toolkit for directly coloring the output of `clustalw2` (.aln file) on console, so you don't have to use a website for visualizing the result of sequence alignment.

Run on Python 2.7 under Linux and Mac OS (Windows not supported), probably on Python 3.x also, yet not tested.

### Requirement

You need to have CCP4 installed, which includes a copy of `clustalw2`.

### Usage

Just put clustalx.py to a convenient path, e.g, `/usr/local/bin`, and run

```shell
chmod +x /usr/local/bin/clustalx.py
```

Then, prepare a fasta file for sequence alignment, and just run

```shell
clustalx.py [-k | --keep-aln-file] <fasta_file>
```

You will see the colored result of sequence alignment. Enjoy!

## paref.py - parallel model refinement using phenix.refine

A toolkit for running multiple jobs of `phenix.refine` in parallel, especially useful when doing simulated annealing. It can automatically pick up the best result amongst all the jobs (based on `R-free` values).

### Requirement

You need to have Phenix properly installed.

### Usage

First put `paref.py` into a convenient path, e.g. `/usr/local/bin`, then run

```shell
chmod +x /usr/local/bin/paref.py
```

Prepare a `param.def` file for the running of `phenix.refine`, and just run as following,

```shell
paref.py [options] param.{def,eff}

Options:
  --jobs=          | -j : number of jobs, default is 4.
  --make-all-seeds | -a : make all seeds, default is to keep the first one.
  --help           | -h : show this help information.
  more options can be configured in `~/.paref.yaml'.
```

You can specify number of jobs, whether or not to use all CPUs, whether or not to make all random seeds, etc.
