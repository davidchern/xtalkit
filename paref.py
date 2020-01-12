#!/usr/bin/env python
# -*- coding: utf-8 -*-
#########################################
#
# function: run phenix.refine in parallel and more
# author: David Chen
# created: 2014/7/8
# updated: 2015/2/17
# updated: 2016/12/10
# updated: 2017/1/5
# updated: 2017/1/25
# updated: 2017/12/14
#
#########################################
import sys, os, signal, termios, fcntl, shutil, glob
import random, ast, re, time, datetime, getopt, yaml
import subprocess as subproc
import multiprocessing

debug = False


if not debug:
    def excepthandler(exception_type, exception, traceback):
        pass

    sys.excepthook = excepthandler


def seed():
    '''
    generate random seed
    '''
    l = random.randint(4, 8)
    s = "".join(random.sample([chr(i) for i in xrange(48, 58)], l)).lstrip('0')
    return s


def prep_ref(prm, n, jobs):
    '''
    prepare def file for refinement
    '''
    with open(prm) as fd:
        eff = fd.readlines()
        if not eff:
            return

    flag = False

    for (i, line) in enumerate(eff):
        # edit pdb file path
        if line.find('    pdb {') != -1:
            ln = eff[i + 1].split(' = ')
            pdb = os.path.abspath(ast.literal_eval(ln[1]))
            if os.path.exists(pdb):
                eff[i + 1] = '%s = \"%s\"\n' % (ln[0], pdb)
            else:
                raise IOError
            continue

        # edit mtz file name
        if line.find('    xray_data {') != -1:
            flag = True
            ln = eff[i + 1].split(' = ')
            mtz = os.path.abspath(ast.literal_eval(ln[1]))
            if os.path.exists(mtz):
                eff[i + 1] = '%s = \"%s\"\n' % (ln[0], mtz)
            else:
                raise IOError
            continue

        # edit cross-validation data file name
        if flag and (line.find('      r_free_flags {') != -1):
            ln = eff[i + 1].split(' = ')
            mtz = os.path.abspath(ast.literal_eval(ln[1]))
            if os.path.exists(mtz):
                eff[i + 1] = '%s = \"%s\"\n' % (ln[0], mtz)
            else:
                raise IOError
            continue

        # set random seed
        if line.find('    random_seed') != -1:
            # When n = 0, the random seed is kept unchanged by default (MAKE_ALL_SEEDS = 0).
            # When MAKE_ALL_SEEDS = 1, all random seeds will be changed/generated.
            if (n == 0) and (os.environ.get('MAKE_ALL_SEEDS', '0') == '0'):
                s = eff[i].split(' = ')[1].strip()
            else:
                s = seed()
                eff[i] = '    random_seed = %s\n' % (s)
            continue

        # set nproc to 1
        if line.find('    nproc') != -1:
            # number of CPUs
            ncpu = multiprocessing.cpu_count()
            # nproc for every job to use, set to 1 or unset
            nproc = int(os.environ.get('NPROC', 0))
            # automatically use maximal number of CPUs for all jobs
            if (not nproc) and (os.environ.get('USE_MAXCPU', '1') == '1'):
                nproc = ncpu // jobs or 1
            eff[i] = '    nproc = %i\n' % (nproc)
            break

    with open('.temp.def', 'w') as fd:
        fd.write(''.join(eff))

    return s


def worker(cwd, prm):
    '''
    worker for running a job
    '''
    os.chdir(cwd)
    # for redirecting output to /dev/null
    null = open('/dev/null', 'a')

    # --overwrite & --unused_ok to improve robustness &
    # compatibility between versions
    cmd = ['phenix.refine', prm, '--overwrite', '--unused_ok']
    proc = subproc.Popen(cmd, cwd=cwd, stdout=null)

    try:
        while proc.poll() is None:
            time.sleep(5)
    except (KeyboardInterrupt, IOError) as e:
        return


def dry_run(prm):
    '''
    check if the param file is OK
    '''
    null = open('/dev/null', 'a')
    cmd = ['phenix.refine', prm, '-n', '--overwrite', '--unused_ok']
    proc = subproc.Popen(cmd, stdout=null)
    return proc.wait()


def progress(elapse=0):
    rotor = ['―', '\\', '|', '/', '―', '\\', '|', '/', '―', '\\', '|', '/']

    sys.stdout.write('\n')
    while True:
        for i in xrange(12):
            elapse += 1
            mins = elapse // 60
            hours = mins // 60
            mins = mins % 60
            secs = elapse % 60
            sys.stdout.write("\rTime elapses:  %i:%02i:%02i  %s " \
                             % (hours, mins, secs, rotor[i]))
            sys.stdout.flush()
            time.sleep(1)


def statistic(prm):
    '''
    sort the refinement result, save the best,
    and modify def for next run
    '''
    rvals = []
    pfx = prm[:-4]
    cwd = os.getcwd()
    logs = glob.glob('%s/ref-*/%s.log' % (cwd, pfx))

    # write refinement log
    outf = open(pfx + '.out', 'a')
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    outf.write('# ' + now + '\n')
    outf.write('Refinement results:\n')

    print '\n\nRefinement results:\n'

    for log in logs:
        with open(log) as fd:
            # read the last line
            ln = fd.readlines()[-1]
            try:
                # extract Rfree factor
                rval = re.search('R-free = (.*)$', ln).group(1)
                # key = ref-?
                key = os.path.split(os.path.dirname(log))[-1]
                rvals.append((key, float(rval)))
                outf.write(key + ": " + ln)
                print '/'.join(log.split('/')[-2:]) + ':\n' + ln
            except:
                pass

    # the lowest Rfree factor is the best
    best = sorted(rvals, key=lambda x: x[1], reverse=False)[0][0]
    src = '%s/%s/' % (cwd, best)
    pth = '%s/%s_' % (cwd, pfx)

    # make target dir for the best result
    i = 1
    while True:
        dest = pth + str(i)
        if not os.path.exists(dest):
            os.mkdir(dest)
            break
        else:
            i += 1

    outf.write("Best result saved in `%s' \n" % (os.path.basename(dest)))
    outf.write('\n')
    outf.close()

    # copy files of the best result to target dir
    for ext in ['.mtz', '.pdb', '.log']:
        shutil.copy(src + pfx + ext, dest)
    for f in glob.glob(src + "*.def"):
        shutil.copy(f, dest)

    # modify the def file for next run
    defs = glob.glob(dest + '/*.def')
    if len(defs) == 2:
        defs.sort()
        next_def = defs[-1]
        with open(next_def, 'r+') as fd:
            # replace only 1 time
            cont = fd.read().replace(best.join(['/'] * 2),
                                     os.path.split(dest)[-1].join(['/'] * 2),
                                     1).replace('.pdb', '-coot-0.pdb', 1)
            fd.seek(0)
            fd.write(cont)

    return True


def conf_parser(argv):
    '''
    parse config data
    '''
    prm = ''
    jobs = 4
    status = 0

    # parse conf.yaml file first
    conf_pth = os.path.expanduser('~/.paref.yaml')
    try:
        # load config into environment variables
        if os.path.exists(conf_pth):
            with open(conf_pth) as f:
                conf = yaml.load(f)
            for key, value in conf.iteritems():
                os.environ[key] = str(value)
    except:
        print "\x1b[31m[ERROR]\x1b[m wrong in parsing `~/.paref.yaml'!"
        status = -2

    # then parse argument variables
    try:
        optlist, args = getopt.getopt(argv, 'j:ah',
                                      ['jobs=', 'make-all-seeds', 'help'])
        for (key, value) in optlist:
            if key in ('-j', '--jobs'):
                if value.isdigit():
                    # number of jobs
                    jobs = int(value)
                    if jobs < 1:
                        print "\x1b[31m[ERROR]\x1b[m number of jobs must > 0!"
                        status = 1
                else:
                    print "\x1b[31m[ERROR]\x1b[m wrong number of jobs given!"
                    status = 2
            if key in ('-a', '--make-all-seeds'):
                os.environ['MAKE_ALL_SEEDS'] = '1'
            if key in ('-h', '--help'):
                return None, None, -1
        if args:
            prm = args[0]
        if not (prm[-3:].lower() in ['def', 'eff'] and os.path.exists(prm)):
            print "\x1b[31m[ERROR]\x1b[m wrong/no parameter file given!"
            status = 1
    except getopt.GetoptError:
        status = -3

    return prm, jobs, status


def notify(jobname):
    '''
    Display notification
    '''
    if os.uname()[0] != 'Darwin':
        return

    notifier = '/Applications/terminal-notifier.app/Contents/MacOS/terminal-notifier'
    icon = '/Applications/terminal-notifier.app/Contents/Resources/phenix.icns'

    if os.path.exists(notifier):
        cmd = '''%s -title "PHENIX parallel refinement" \
             -message "Refinement jobs (%s) finished" \
             -sound "Glass" -contentImage "%s" &''' \
                 %(notifier, jobname, icon)
    else:
        cmd = '''osascript -e "display notification \
             \\"Refinement jobs (%s) finished\\" \
             with title \\"PHENIX parallel refinement\\"" &''' \
                 %(jobname)

    os.system(cmd)

    return


def usage():
    print "###################################################\n" \
          "  A toolkit for running phenix.refine in parallel\n" \
          "###################################################\n" \
          "Usage: paref.py [options] param.{def,eff}\n\n" \
          "Options:\n" \
          "  --jobs=          | -j : number of jobs, default is 4.\n" \
          "  --make-all-seeds | -a : make all seeds, default is to keep the first one.\n" \
          "  --help           | -h : show this help information.\n" \
          "  more options can be configured in `~/.paref.yaml'.\n"


def info():
    print "Type `paref.py -h' for help information."


def main():
    '''
    start parallel processes and count time
    '''
    # disable traceback upon keyboard interrupt
    signal.signal(signal.SIGINT, lambda x, y: sys.exit(1))

    prm, jobs, status = conf_parser(sys.argv[1:])
    if status != 0:
        return status

    if os.environ.get('CHECK_PRM_FILE', '1') == '1':
        print "Checking the parameter file...",
        sys.stdout.flush()

        if dry_run(prm) != 0:
            print "\n\x1b[31m[ERROR]\x1b[m There's something wrong with the parameter file!"
            return 0
        print "OK\n"

    print "Starting %i jobs of phenix.refine in parallel...\n" % (jobs)

    isOK = False
    procs = []
    pwd = os.getcwd()
    for n in xrange(jobs):
        # make dir and copy files
        cwd = "%s/ref-%i" % (pwd, n)
        if not os.path.exists(cwd):
            os.mkdir(cwd)
        # prepare def file
        s = prep_ref(prm, n, jobs)
        shutil.copy('.temp.def', cwd + '/' + prm)
        # start a process for refinement
        print "    ref-%i: seed = %s" % (n, s)
        proc = multiprocessing.Process(target=worker, args=(cwd, prm))
        proc.start()
        procs.append(proc)
        time.sleep(0.1)

    # start a process for monitoring progress of running
    prog = multiprocessing.Process(target=progress)
    prog.start()

    # disabling keyboard input
    fd = sys.stdin.fileno()
    oldterm = termios.tcgetattr(fd)
    newattr = termios.tcgetattr(fd)
    newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
    termios.tcsetattr(fd, termios.TCSANOW, newattr)
    oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

    # check the whole progress
    try:
        while True:
            for proc in procs:
                proc.join(1)  # wait for 1 second
                if not proc.is_alive():
                    procs.remove(proc)
            if not procs:
                try:
                    prog.terminate()
                    prog.join()
                except:
                    pass
                isOK = True
                break
    except KeyboardInterrupt:
        pass
    finally:
        # restore terminal properties
        termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
        print ""

    if isOK:
        try:
            rc = statistic(prm)
            if rc: notify(prm[:-4])
        except:
            return -9

    return 0


if __name__ == '__main__':

    if len(sys.argv) > 1:
        status = main()
        if status == -1:
            usage()
        elif status == -9:
            print "\nRefinement jobs failed."
        elif status != 0:
            info()
    else:
        usage()
