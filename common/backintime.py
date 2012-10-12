#    Back In Time
#    Copyright (C) 2008-2009 Oprea Dan, Bart de Koning, Richard Bailey
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import os
import os.path
import stat
import sys
import gettext

import config
import logger
import snapshots
import tools
import sshtools
import mount

_=gettext.gettext


def take_snapshot_now_async( cfg ):
	profile=''
	if '1' != cfg.get_current_profile():
		profile = "--profile-id %s" % cfg.get_current_profile()

	cmd = "backintime %s --backup &" % profile
	if cfg.is_run_ionice_from_user_enabled():
		cmd = 'ionice -c2 -n7 ' + cmd

	os.system( cmd )


def take_snapshot( cfg, force = True ):
	logger.openlog()
	_mount(cfg)
	snapshots.Snapshots( cfg ).take_snapshot( force )
	_umount(cfg)
	logger.closelog()

def _mount(cfg):
	try:
		hash_id = mount.Mount(cfg = cfg).mount()
	except mount.MountException as ex:
		logger.error(str(ex))
		sys.exit(1)
	else:
		cfg.set_current_hash_id(hash_id)

def _umount(cfg):
	try:
		mount.Mount(cfg = cfg).umount(cfg.current_hash_id)
	except mount.MountException as ex:
		logger.error(str(ex))


def print_version( cfg, app_name ):
	print ''
	print 'Back In Time'
	print 'Version: ' + cfg.VERSION
	print ''
	print 'Back In Time comes with ABSOLUTELY NO WARRANTY.'
	print 'This is free software, and you are welcome to redistribute it'
	print "under certain conditions; type `%s --license\' for details." % app_name
	print ''


def print_help( cfg ):
	print 'Options'
	print '--profile <profile name>'
	print '\tSelect profile (use it before other options)'
	print '--profile-id <profile id>'
	print '\tSelect profile by id (use it before other options)'
	print '-b | --backup'
	print '\tTake a snapshot (and exit)'
	print '--backup-job'
	print '\tUsed for cron job: take a snapshot (and exit)'
	print '--snapshots-path'
	print '\tShow the path where is saves the snapshots (and exit)'
	print '--snapshots-list'
	print '\tShow the list of snapshots IDs (and exit)'
	print '--snapshots-list-path'
	print '\tShow the paths to snapshots (and exit)'
	print '--last-snapshot'
	print '\tShow the ID of the last snapshot (and exit)'
	print '--last-snapshot-path'
	print '\tShow the path to the last snapshot (and exit)'
	print '--benchmark-cipher [file-size]'
	print '\tShow a benchmark of all ciphers for ssh transfer (and exit)'
	print '-v | --version'
	print '\tShow version (and exit)'
	print '--license'
	print '\tShow license (and exit)'
	print '-h | --help'
	print '\tShow this help (and exit)'
	print ''


def start_app( app_name = 'backintime', extra_args = [] ):
	cfg = config.Config()
	print_version( cfg, app_name )

	skip = False
	index = 0
	
	for arg in sys.argv[ 1 : ]:
		index = index + 1

		if skip:
			skip = False
			continue

		if arg == '--profile':
			if not cfg.set_current_profile_by_name( sys.argv[index + 1] ):
				print "Profile not found: %s" % sys.argv[index + 1]
				sys.exit(0)
			skip = True
			continue

		if arg == '--profile-id':
			if not cfg.set_current_profile( sys.argv[index + 1] ):
				print "Profile id not found: %s" % sys.argv[index + 1]
				sys.exit(0)
			skip = True
			continue

		if arg == '--backup' or arg == '-b':
			take_snapshot( cfg, True )
			sys.exit(0)

		if arg == '--backup-job':
			take_snapshot( cfg, False )
			sys.exit(0)

		if arg == '--version' or arg == '-v':
			sys.exit(0)

		if arg == '--license':
			print cfg.get_license()
			sys.exit(0)

		if arg == '--help' or arg == '-h':
			print_help( cfg )
			sys.exit(0)

		if arg == '--snapshots-path':
			if not cfg.is_configured():
				print "The application is not configured !"
			else:
				print "SnapshotsPath: %s" % cfg.get_snapshots_full_path()
			sys.exit(0)

		if arg == '--snapshots-list':
			if not cfg.is_configured():
				print "The application is not configured !"
			else:
				_mount()
				list = snapshots.Snapshots( cfg ).get_snapshots_list()
				if len( list ) <= 0:
					print "There are no snapshots"
				else:
					for snapshot_id in list:
						print "SnapshotID: %s" % snapshot_id
				_umount()
			sys.exit(0)

		if arg == '--snapshots-list-path':
			if not cfg.is_configured():
				print "The application is not configured !"
			else:
				_mount()
				s = snapshots.Snapshots( cfg )
				list = s.get_snapshots_list()
				if len( list ) <= 0:
					print "There are no snapshots"
				else:
					for snapshot_id in list:
						print "SnapshotPath: %s" % s.get_snapshot_path( snapshot_id )
				_umount()
			sys.exit(0)

		if arg == '--last-snapshot':
			if not cfg.is_configured():
				print "The application is not configured !"
			else:
				_mount()
				list = snapshots.Snapshots( cfg ).get_snapshots_list()
				if len( list ) <= 0:
					print "There are no snapshots"
				else:
					print "SnapshotID: %s" % list[0]
				_umount()
			sys.exit(0)

		if arg == '--last-snapshot-path':
			if not cfg.is_configured():
				print "The application is not configured !"
			else:
				_mount()
				s = snapshots.Snapshots( cfg )
				list = s.get_snapshots_list()
				if len( list ) <= 0:
					print "There are no snapshots"
				else:
					print "SnapshotPath: %s" % s.get_snapshot_path( list[0] )
				_umount()
			sys.exit(0)

		if arg == '--benchmark-cipher':
			if not cfg.is_configured():
				print "The application is not configured !"
			else:
				try:
					size = sys.argv[index + 1]
				except IndexError:
					size = '40'
				ssh = sshtools.SSH(cfg=cfg) #TODO: change to new mount_framework
				if ssh.ssh:
					ssh.benchmark_cipher(size)
				else:
					print('ssh is not configured !')
			sys.exit(0)

		if arg == '--snapshots' or arg == '-s':
			continue

		if arg == '--gnome' or arg == '--kde4' or arg == '--kde3':
			continue

		if arg[0] == '-':
			if not arg[0] in extra_args:
				print "Ignore option: %s" % arg
			continue

	return cfg


if __name__ == '__main__':
	start_app()

