#!/usr/bin/python
# author: David Chern
# date: 2017/4/29
import sys, os, subprocess, re, getopt


COLOR_SCHEME = {
    '.': '\x1b[0;30;44m%s\x1b[m',  # blue
    ':': '\x1b[0;30;42m%s\x1b[m',  # green
    '*': '\x1b[0;30;41m%s\x1b[m',  # red
    ' ': 0
}


def clustalw_color(aln_file=''):
    if not os.path.exists(aln_file):
        return -1

    with open(aln_file) as fd:
        aln_content = fd.readlines()
        if not 'CLUSTAL 2.1' in aln_content[0]:  # check version
            return -2
        content = ''.join(aln_content[3:])  # skip first three lines

    lines = [seg.strip().splitline() for seg in re.split("\n\n", content)]

    colored_aln = []
    for (n, seg) in enumerate(lines):
        nwidth = max([ln.find(ln.split(' ')[-1]) for ln in seg[:-1]])
        prev_seg = lines[n - 1][0].rstrip() if n > 0 else lines[0][0].rstrip()
        numbered_ln = " " * nwidth + \
                      "".join(["%10s" %(10 * i + n * len(prev_seg[nwidth:]))
                               for i in range(1, len(seg[0][nwidth:])//10 + 1)])

        if seg[-1].startswith(' '):
            seg[-1] = seg[-1] + ' ' * (len(seg[0]) - len(seg[-1]))
            aln_info = seg[-1]

            colored_seg = [numbered_ln]
            for ln in seg:
                colored_seq = ln[:nwidth]
                for i in range(nwidth, len(ln)):
                    color = COLOR_SCHEME.get(aln_info[i])
                    colored_seq += color % (ln[i]) if color else ln[i]
                colored_seg.append(colored_seq)

            colored_aln.append('\n'.join(colored_seg))
        else:
            colored_aln.append('\n'.join([numbered_ln] + seg))

    print "\n\n".join(colored_aln)

    return 0


def run_clustalw(fasta=''):
    if not fasta:
        return -1

    clustalw = os.path.join(os.environ.get('CCP4', ''), '/libexec/clustalw2')
    if not os.path.isfile(clustalw):
        return 1

    proc = subprocess.Popen([clustalw, fasta], stdout=open('/dev/null'))

    return proc.wait()


def main(fasta, keep_aln_file=False):
    aln = fasta[:-3] + "aln"
    dnd = fasta[:-3] + "dnd"

    if not os.path.exists(aln):
        rc = run_clustalw(fasta)
        if rc != 0: return rc

    clustalw_color(aln)

    if keep_aln_file:
        os.rename(aln, aln[:-3] + 'clustalw')
    else:
        os.remove(aln)
    os.remove(dnd)

    return 0


if __name__ == '__main__':
    fasta_file = ''
    keep_aln_file = False

    try:
        optlist, args = getopt.getopt(sys.argv[1:], 'k', ['keep-aln-file'])
        for (key, value) in optlist:
            if key in ('-k', '--keep-aln-file'):
                keep_aln_file = True
        if args:
            fasta_file = args[0]
        else:
            raise
    except:
        print "Usage: clustalx.py [-k | --keep-aln-file] <fasta_file>"

    main(fasta_file, keep_aln_file)
