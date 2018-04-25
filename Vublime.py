# Vublime 1.0
# Author Vic P.

import os, tempfile, datetime, time, sys
import sublime, sublime_plugin

VL_FILE_PATH = __file__
VL_FILE_NAME = os.path.basename(VL_FILE_PATH)
VL_FILE_NAME_NOEXT = os.path.splitext(VL_FILE_NAME)[0]
VL_FILE_SETTINGS   = VL_FILE_NAME_NOEXT + ".sublime-settings"

# Settings

settings = None
captions = None

def plugin_loaded():

	global settings, captions
	settings = sublime.load_settings(VL_FILE_SETTINGS)
	captions = settings.get("captions")

	msg_ready = VL_FILE_NAME_NOEXT + " -> READY"
	sublime.status_message(msg_ready)
	print(msg_ready)

	return

# Commands

class VublimeAboutCommand(sublime_plugin.TextCommand) :

	def description(self) :
		return captions.get("about")

	def is_enabled(self) :
		return True

	def is_visible(self) :
		return True

	def run(self, edit) :
		sublime.message_dialog(captions.get("info"))
		return

class VublimeSaveAsTemporaryCommand(sublime_plugin.TextCommand) :

	def description(self) :
		return captions.get("save_as_temporary")

	def is_enabled(self) :
		return self.view.file_name() == None

	def is_visible(self) :
		return True

	def run(self, edit) :

		# temporary directory
		temporary_dir = settings.get("temporary_dir", "")
		if temporary_dir == None or temporary_dir == "" :
			temporary_dir = tempfile.gettempdir()
		pass

		# file name by tempfile
		file_name = next(tempfile._get_candidate_names())

		# file name by time
		file_name_time = settings.get("file_name_by_time", True)
		if file_name_time : file_name = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

		# create the file path
		file_path  = temporary_dir
		file_path += "\\"
		file_path += file_name

		# append dot character
		append_dot = settings.get("append_dot", False)
		if append_dot : file_path += "."
		print(file_path)

		# confirm the file path
		self.view.window().show_input_panel("Save As Temporary File :", file_path, self.save_as_temporary, None, None)

		return

	def save_as_temporary(self, file_path) :

		# save to temporary directory
		self.view.retarget(file_path)
		self.view.run_command("save")
		sublime.status_message("Saved as '%s'" % file_path)

		return