# xtalkit

## clustalx

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
