gratia-probe-slurm
==================

Gratia probe for SLURM resource manager

The probe connects to the SLURM accounting database, retrieves records for
completed jobs, and submits the JobUsageRecords to Gratia.

Requirements
------------
* SLURM (tested with 2.4)
* MySQL
* Python (tested with 2.6)
* Python MySQLdb (in the standard MySQL-python package)
* slurmdbd accounting storage configured and logging to MySQL

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
* The probe gets the installed SLURM version by running the srun command.
  If your SLURM install is not on the path, specify it with the
  _SlurmLocation_ option.

ProbeConfig options
-------------------
<table>
	<tr>
		<th>Option</th>
		<th>Description</th>
	</tr>
	<tr>
		<td>SlurmDbHost="db.cluster.example.edu"</td>
		<td>Database host</td>
	</tr><tr>
		<td>SlurmDbPort="3306"</td>
		<td>Database port</td>
	</tr><tr>
		<td>SlurmDbUser="slurm"</td>
		<td>Database username with read/only access</td>
	</tr><tr>
		<td>SlurmDbPasswordFile="/etc/gratia/slurm/pwfile"</td>
		<td>File containing database password. Must only be readable to the probe. (chmod 600)</td>
	</tr><tr>
		<td>SlurmDbName="slurm_acct_db"</td>
		<td>Name of SLURM accounting database</td>
	</tr><tr>
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

