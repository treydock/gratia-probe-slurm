#!/usr/bin/python
# /* vim: set expandtab tabstop=4 shiftwidth=4 softtabstop=4: */

###########################################################################
# slurm_meter
#
# Python-based probe for SLURM accounting database
# 
# John Thiltges, 2012-Jun-19
# Based on condor_meter by Brian Bockelman
# 
# Copyright 2012 University of Nebraska-Lincoln. Released under GPL v2.
###########################################################################

import sys, os, stat
import time, random
import datetime, dateutil.parser
import subprocess
import re
from decimal import Decimal

from gratia.common.Gratia import DebugPrint
import gratia.common.GratiaWrapper as GratiaWrapper
import gratia.common.Gratia as Gratia

prog_version = "%%%RPMVERSION%%%"
prog_revision = '$Revision$'

class SlurmProbe:

    opts       = None
    args       = None
    checkpoint = None
    cluster    = None
    sacct      = None

    def __init__(self):
        try:
            self.opts, self.args = self.parse_opts()
        except Exception, e:
            print >> sys.stderr, str(e)
            sys.exit(1)

        # Initialize Gratia
        if not self.opts.gratia_config or not os.path.exists(self.opts.gratia_config):
            raise Exception("Gratia config, %s, does not exist." %
                    self.opts.gratia_config)
        Gratia.Initialize(self.opts.gratia_config)

        if self.opts.verbose:
            Gratia.Config.set_DebugLevel(5)

        # Sanity checks for the probe's runtime environment.
        GratiaWrapper.CheckPreconditions()

        if self.opts.sleep:
            rnd = random.randint(1, int(self.opts.sleep))
            DebugPrint(2, "Sleeping for %d seconds before proceeding." % rnd)
            time.sleep(rnd)

        # Make sure we have an exclusive lock for this probe.
        GratiaWrapper.ExclusiveLock()

        # Get sacct path
        self.sacct_path = self.get_sacct_path()

        self.register_gratia("slurm_meter")

        # Find the checkpoint filename (if enabled)
        if self.opts.checkpoint:	
            checkpoint_file = os.path.join(
                Gratia.Config.get_WorkingFolder(), "checkpoint")
        else:
            checkpoint_file = None

        # Open the checkpoint file
        self.checkpoint = SlurmCheckpoint(checkpoint_file)

        # Only process DataFileExpiration days of history
        # (unless we're resuming from a checkpoint file)
        if self.checkpoint.val is None:
            self.checkpoint.val = int(time.time() - (Gratia.Config.get_DataFileExpiration() * 86400))

        self.cluster = Gratia.Config.getConfigAttribute('SlurmCluster')
        self.end = self.opts.end
        self.sacct = SlurmAcct(self.sacct_path, self.cluster, self.end)

    def parse_opts(self):
        """Hook to parse command-line options"""
        return

    def get_server_id(self):
        """Return database server ID: SLURM/cluster"""
        #TODO
        return "SLURM/%s" % self.cluster

    def get_sacct_path(self):
        prog = "sacct"
        path = Gratia.Config.getConfigAttribute("SlurmLocation")

        # Look for the program on the $PATH
        cmd = prog

        # Unless there is a specific path configured
        if path:
            c = os.path.join(path, "bin", prog)
            if os.path.exists(c):
                cmd = c
        return cmd

    def get_slurm_version(self):
        prog = "%s --version" % self.sacct_path

        fd = os.popen(prog)
        output = fd.read()
        if fd.close():
            raise Exception("Unable to invoke %s" % prog)

        name, version = output.split()
        return version

    def register_gratia(self, name):
        Gratia.RegisterReporter(name, "%s (tag %s)" % \
            (prog_revision, prog_version))

        try:
            slurm_version = self.get_slurm_version()
        except Exception, e:
            DebugPrint(0, "Unable to get SLURM version: %s" % str(e))
            raise

        Gratia.RegisterService("SLURM", slurm_version)
        Gratia.setProbeBatchManager("slurm")

class SlurmCheckpoint(object):
    """Read and write a checkpoint file
    If class is instantiated without a filename, class works as expected but
    data is not stored to disk
    """

    _val = None
    _fp  = None

    def __init__(self, target=None):
        """
        Create a checkpoint file
        target - checkpoint filename (optionally null)
        """
        if target:
            try:
                fd        = os.open(target, os.O_RDWR | os.O_CREAT)
                self._fp  = os.fdopen(fd, 'r+')
                self._val = long(self._fp.readline())
                DebugPrint(1, "Resuming from checkpoint in %s" % target)
            except IOError:
                raise IOError("Could not open checkpoint file %s" % target)
            except ValueError:
                DebugPrint(1, "Failed to read checkpoint file %s" % target)

    def get_val(self):
        """Get checkpoint value"""
        return self._val

    def set_val(self, val):
        """Set checkpoint value"""
        self._val = long(val)
        if (self._fp):
            self._fp.seek(0)
            self._fp.write(str(self._val) + "\n")
            self._fp.truncate()

    val = property(get_val, set_val)

class SlurmAcct(object):
    def __init__(self, sacct_path, cluster, end):
        self._sacct_path = sacct_path

        cluster = re.sub('\W+', '', cluster)
        self._cluster = cluster
        self._end = end

    def completed_jobs(self, ts):
        """Completed jobs, ordered by completion time"""

        states = 'CANCELLED,COMPLETED,FAILED,NODE_FAIL,PREEMPTED,TIMEOUT'
        start = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(ts))
        return self._get_jobs(states=states, start=start)

    def running_jobs(self):
        states = 'RUNNING'
        return self._get_jobs(states=states, start=None)

    def running_users(self, ts=None):
        """Running jobs, grouped by user, ordered by completion time"""
        states = 'RUNNING,PENDING,SUSPENDED'
        if ts:
            start = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(ts))
        else:
            start = None
        return self._get_users(states=states, start=start)

    def _get_jobs(self, states, start):
        cmd = [
            self._sacct_path, '--allusers', '--parsable2', '--noheader',
            '--clusters', self._cluster,
            '--state', states,
            '--format',
            'account,cluster,systemcpu,usercpu,alloccpus,exitcode,jobid,jobname,maxrss,partition,state,end,start,suspended,user,elapsed',
        ]
        if start is not None:
            cmd += ['--start', start]
            cmd += ['--end', self._end]
        DebugPrint(0, "Executing SLURM command: %s" % " ".join(cmd))
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        exit_code = process.returncode
        if exit_code != 0:
            raise Exception("Error executing sacct: %S" % err)

        _jobs = {}
        for line in out.split(os.linesep):
            _line = line.strip()
            if not _line:
                continue
            _data = _line.split('|')

            # Process JobID first and modify behavior if this is a job step
            # The parent jobID will contain sum of values such as SystemCPU and UserCPU
            # MaxRSS is invalid for parent job, so must collect from job steps
            _job_id_s = _data[6].split('.')
            _job_id = _job_id_s[0]
            if len(_job_id_s) > 1:
                _job_step = _job_id_s[1]
            else:
                _job_step = None
            _job = _jobs.get(_job_id, {})

            # Get MaxRSS from steps associated with parent job
            if 'max_rss' not in _job:
                _job['max_rss'] = 0
            if _job_step:
                _job['max_rss'] += self._to_kb(_data[8])
                continue

            _job['id_job'] = _job_id
            _job['acct'] = _data[0]
            _job['cluster'] = _data[1]
            _job['cpu_sys'] = self._duration_to_sec(_data[2])
            _job['cpu_user'] = self._duration_to_sec(_data[3])
            _job['cpus_alloc'] = _data[4]
            _job['exit_code'] = _data[5].split(':')[0]
            _job['job_name'] = _data[7]
            _job['partition'] = _data[9]
            _job['state'] = _data[10]
            _job['time_end'] = self._time_to_epoch(_data[11])
            _job['time_start'] = self._time_to_epoch(_data[12])
            _job['time_suspended'] = self._duration_to_sec(_data[13])
            _job['user'] = _data[14]
            _job['wall_time'] = self._duration_to_sec(_data[15])
            _jobs[_job_id] = _job

        # Sort values by time_end
        _jobs = sorted(_jobs.values(), key=lambda k: k['time_end'])
        return _jobs

    def _get_users(self, states, start):
        cmd = [
            self._sacct_path, '--allusers', '--parsable2', '--noheader', '--allocations',
            '--clusters', self._cluster,
            '--state', states,
            '--format',
            'user,cluster,alloccpus,state,end',
        ]
        if start is not None:
            cmd += ['--start', start]
            cmd += ['--end', self._end]
        DebugPrint(0, "Executing SLURM command: %s" % " ".join(cmd))
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        out, err = process.communicate()
        exit_code = process.returncode
        if exit_code != 0:
            raise Exception("Error executing sacct: %S" % err)

        _users = {}
        for line in out.split(os.linesep):
            _line = line.strip()
            if not _line:
                continue
            _data = _line.split('|')

            _username = _data[0]
            if _data[4] == 'Unknown':
                _time_end = 0
            else:
                _time_end = self._time_to_epoch(_data[4])
            _user = _users.get(_username, {})
            if _username not in _users:
                _user = {}
                _user['user'] = _username
                _user['cluster'] = _data[1]
                _user['cpus_pending'] = 0
                _user['cpus_running'] = 0
                _user['time_end'] = _time_end
            else:
                if _time_end > _user['time_end']:
                    _user['time_end'] = _time_end
            _state = _data[3]
            _cpus = int(_data[2])
            if _state in ['PENDING', 'SUSPENDED']:
                _user['cpus_pending'] += _cpus
            else:
                _user['cpus_running'] += _cpus
            _users[_username] = _user

        # Sort values by time_end
        _users = sorted(_users.values(), key=lambda k: k['time_end'])
        return _users

    def _duration_to_sec(self, t):
        # Format can be DD-HH:MM:SS or HH:MM:SS or MM:SS
        m = re.search(r"(([\d]+)?-)?([\d]+)?:?([\d]{2})\:([\d\.]+)", t)
        sec = Decimal('0.0')
        if not m:
            return sec
        #DebugPrint(0, "SLURM duration -> sec: %s -> %s" % (t, m.groups()))
        # Days - optional
        if m.group(2):
            sec += Decimal('86400.0') * Decimal(m.group(2))
        # Hours - optional
        if m.group(3):
            sec += Decimal('3600.0') * Decimal(m.group(3))
        # Minutes
        sec += Decimal('60.0') * Decimal(m.group(4))
        # Seconds
        sec += Decimal(m.group(5))

        return sec

    def _time_to_epoch(self, t):
        _epoch = dateutil.parser.parse(t).strftime("%s")
        return int(_epoch)

    def _to_kb(self, s):
        m = re.search(r"([\d]+)([\D])", s)
        #DebugPrint(0, "SLURM to kb: %s -> %s" % (s, m.groups()))
        _val = int(m.group(1))
        _suf = m.group(2)
        if _suf == 'K':
            _power = 0
        elif _suf == 'M':
            _power = 1
        elif _suf == 'G':
            _power = 2
        elif _suf == 'T':
            _power = 3
        else:
            return 0

        _kb = _val * 1024**_power
        return _kb
