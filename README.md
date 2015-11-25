gratia-probe-slurm
==================

Gratia probe for SLURM resource manager

The probe queries the SLURM sacct data, and parses records for
completed jobs, and submits the JobUsageRecords to Gratia.

Requirements
------------
* SLURM (tested with 14.03 and 15.08)
* Python (tested with 2.6)
* slurmdbd accounting storage configured

Installation
------------
1. Configure the ProbeConfig
2. Add the script to cron

Sample crontab entry:
<pre>
*/15 * * * * root /usr/bin/slurm_meter -s 900 -c
</pre>

Notes
-----
* The probe gets the installed SLURM version by running the sacct command.
  If your SLURM install is not on the path, specify it with the
  _SlurmLocation_ option.

ProbeConfig options
-------------------
<table>
	<tr>
		<th>Option</th>
		<th>Description</th>
	</tr>
		<td>SlurmCluster="mycluster"</td>
		<td>Name of SLURM cluster, available from 'sacctmgr list cluster'</td>
	</tr>
</table>

Running jobs ProbeConfig
------------------------
In addition to the settings above, there are additional options for the
running jobs probe.

<table>
	<tr>
		<th>Option</th>
		<th>Description</th>
	</tr>
	<tr>
		<td>SlurmCEName="cluster.example.edu"</td>
		<td>The FQDN of the cluster</td>
	</tr>
</table>

