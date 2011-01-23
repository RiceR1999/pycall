"""A simple wrapper for Asterisk call files."""


from shutil import move
from time import mktime
from pwd import getpwnam
from tempfile import mkstemp
from os import path, chown, utime, fdopen

from path import path

from .call import Call
from .actions import Application, Context
from .errors import *


class CallFile(object):
	"""Stores and manipulates Asterisk call files."""

	#: The default spooling directory (should be OK for most systems).
	DEFAULT_SPOOL_DIR = '/var/spool/asterisk/outgoing'

	def __init__(self, call, action, set_var=None, archive=None, user=None,
			tmpdir=None, file_name=None, spool_dir=None):
		"""Create a new `CallFile` obeject.

		:param obj call: A `pycall.Call` instance.
		:param obj action: Either a `pycall.actions.Application` instance
			or a `pycall.actions.Context` instance.
		:param dict set_var: Variables to pass to Asterisk upon answer.
		:param bool archive: Should Asterisk archive the call file?
		:param str user: Username to spool the call file as.
		:param str tmpdir: Directory to store the temporary call file.
		:param str file_name: Call file name.
		:param str spool_dir: Directory to spool the call file to.
		:rtype: `CallFile` object.
		"""
		self.call = call
		self.action = action
		self.set_var = set_var
		self.archive = archive
		self.user = user
		self.tmpdir = tmpdir
		self.file_name = file_name
		self.spool_dir = spool_dir or DEFAULT_SPOOL_DIR

	def _is_valid(self):
		"""
		Checks class attributes to ensure they are valid.

		:raises: `NoChannelDefinedError` if no `channel` attribute has been
			specified.
		:raises: `NoActionDefinedError` if no action has been specified.
		:rtype: Boolean.
		"""
		return True

	def _buildfile(self):
		"""
		Use the class attributes to build a call file string.

		:raises: `UnknownError` if there were problems validating the call
			file.
		:returns: A list consisting of all call file directives.
		:rtype: List of strings.
		"""
		if not self._is_valid():
			raise UnknownError

		cf = []
		cf.append('Channel: '+self.channel)

		if self.application:
			cf.append('Application: '+self.application)
			cf.append('Data: '+self.data)
		elif self.context and self.extension and self.priority:
			cf.append('Context: '+self.context)
			cf.append('Extension: '+self.extension)
			cf.append('Priority: '+self.priority)
		else:
			raise UnknownError

		if self.set_var:
			for var, value in self.set_var.items():
				cf.append('Set: %s=%s' % (var, value))

		if self.callerid:
			cf.append('Callerid: %s' % self.callerid)

		if self.wait_time:
			cf.append('WaitTime: %s' % self.wait_time)

		if self.max_retries:
			cf.append('Maxretries: %s' % self.max_retries)

		if self.retry_time:
			cf.append('RetryTime: %s' % self.retry_time)

		if self.account:
			cf.append('Account: %s' % self.account)

		if self.archive:
			cf.append('Archive: yes')

		return cf

	@property
	def contents(self):
		"""
		Get the contents of this call file.

		:returns: Call file contents.
		:rtype: String.
		"""
		return '\n'.join(self._buildfile())

	def _writefile(self, cf):
		"""
		Write a temporary call file.

		:param cf: List of call file directives.
		:returns: Absolute path name of the temporary call file.
		:rtype: String.
		"""
		if self.tmpdir:
			file, fname = mkstemp(suffix='.call', dir=self.tmpdir)
		else:
			file, fname = mkstemp('.call')

		with fdopen(file, 'w') as f:
			for line in cf:
				f.write(line+'\n')

		return fname

	def spool(self):
		"""Spool the call file with Asterisk."""

		raise NoActionDefinedError

	def run(self, time=None):
		"""
		Uses the class attributes to submit this `CallFile` to the Asterisk
		spooling directory.

		:param datetime time: [optional] The date and time to spool this call
			file.
		:rtype: Boolean.
		"""
		fname = self._writefile(self._buildfile())

		if self.user:
			try:
				pwd = getpwnam(self.user)
				uid = pwd[2]
				gid = pwd[3]

				try:
					chown(fname, uid, gid)
				except:
					raise NoUserPermissionError
			except:
				raise NoUserError

		# Change the modification and access time on the file so that Asterisk
		# knows when to place the call. If time is not specified, then we place
		# the call immediately.
		try:
			time = mktime(time.timetuple())
			utime(fname, (time, time))
		except:
			pass

		try:
			move(fname, self.spool_dir+path.basename(fname))
		except:
			raise NoSpoolPermissionError

		return True
