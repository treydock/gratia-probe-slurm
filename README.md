gratia-probe-slurm
==================

Gratia probe for SLURM resource manager

The probe connects to the SLURM accounting database, retrieves records for
completed jobs, and submits the JobUsageRecords to Gratia.

Requirements
------------
* SLURM (tested with 2.4)
* MySQL
* slurmdbd accounting storage configured and logging to MySQL

Installation
------------
1. Configure the ProbeConfig
2. Add the script to cron

Sample crontab entry:
<pre>
*/15 * * * * root /usr/bin/slurm_meter -s 900 -c
</pre>

ProbeConfig options
-------------------
<table>
	<tr>
		<th>Option</th>
		<th>Description</th>
	</tr>
	<tr>
		<td>SlurmDbHost="localhost"</td>
		<td>Database host</td>
	</tr><tr>
		<td>SlurmDbPort="3306"</td>
		<td>Database port</td>
	</tr><tr>
		<td>SlurmDbUser="slurm"</td>
		<td>Database username</td>
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

