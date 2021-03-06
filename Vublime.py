# Vublime 1.0
# Author Vic P.

import os, tempfile, datetime, re, zipfile
import sublime, sublime_plugin
# import pandas as pd

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
        file_path += os.sep if file_path[-1] != os.sep else ""
        file_path += file_name

        # auto append the extension by the current syntax
        auto_extension = settings.get("auto_extension", False)
        extension = ""
        if auto_extension :
            extension = self.get_extension_by_current_syntax()
            if len(extension) > 0 :
                file_path += "."
                file_path += extension
            pass
        pass

        # confirm the file path
        confirm_file_path = settings.get("confirm_file_path", True)
        if auto_extension and len(extension) == 0 : confirm_file_path = True
        if confirm_file_path :
            self.view.window().show_input_panel(
                "Save As Temporary File :",
                file_path,
                self.save_as_temporary,
                None,
                None
            )
        else : self.save_as_temporary(file_path)

        return

    def save_as_temporary(self, file_path) :

        # save to temporary directory
        self.view.retarget(file_path)
        self.view.run_command("save")
        sublime.status_message("Saved as '%s'" % file_path)

        return

    def read_file_in_package(self, zip_file_path, file_name_inside_zip) :

        data = ""

        try :

            if not os.path.exists(zip_file_path) : return data

            if not zipfile.is_zipfile(zip_file_path) : return data

            zip = zipfile.ZipFile(zip_file_path)

            # file_names = map(str.lower, zip.namelist())
            # if not (file_name_inside_zip in file_names) : return data

            f = zip.open(file_name_inside_zip)
            data = f.read()
            f.close()

        except Exception as e : data = ""

        return data.decode("utf-8") if type(data).__name__ == "bytes" else str(data)

    def get_executable_dir(self) :
        return os.path.dirname(sublime.executable_path())

    def get_extension_by_current_syntax(self) : # in the section `file_extensions:`

        result = ""

        try :

            syntax_package_file_path = (self.view.settings().get("syntax"))

            package_folder = package_name = syntax_name = ""

            l = re.compile(r"(.*)/(.*)/(.*).sublime-syntax").findall(syntax_package_file_path)
            if len(l) == 1 :
                package_folder, package_name, syntax_name = l[0]
                package_name += ".sublime-package"
                syntax_name  += ".sublime-syntax"
            pass

            if len(package_name) != 0 and len(syntax_name) != 0:

                syntax_file_data = ""

                fmt = "%s"; fmt += os.sep; fmt += "%s"; fmt += os.sep; fmt += "%s";
                package_path = fmt % (self.get_executable_dir(), package_folder, package_name)
                syntax_file_data = self.read_file_in_package(package_path, syntax_name)

                if len(syntax_file_data) > 0 :
                    matches = re.finditer(r"(?<=^\s\s-\s)([^\s]*)(?=[\s.*\n])", syntax_file_data, re.MULTILINE)
                    extensions = [match.group() for i, match in enumerate(matches)]
                    if len(extensions) > 0 : result = extensions[0]
                pass

            pass

        except Exception as e : result = ""

        return result

# Open File in View

class VublimeOpenFileInViewCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        for region in self.view.sel(): # single line or multiple lines that selected by multiple-cursors

            # extract selected line
            text = self.view.substr(self.view.line(region))
            pos_at_beg_line = self.view.line(region).begin()
            pos_at_sel_line = region.begin()
            col = pos_at_sel_line - pos_at_beg_line

            # extract string on selected line
            parts, sep = text.split('"'), '"'
            if len(parts) < 2: parts, sep = text.split('\''), '\''
            if len(parts) < 2:
                sublime.message_dialog("Not found any file")
                return

            # extract a relative file nam from the extracted string
            file_name = parts[text[:col].count(sep)]
            file_name = self.normalize_path(file_name)

            # extract directory from the current viewing file
            file_dir = os.path.dirname(self.view.file_name())
            file_dir = self.normalize_path(file_dir)

            file_path = file_name

            # file_dir_parts = file_dir.split(os.path.sep)
            # file_path, tmp_file_dir = "", ""
            # for file_dir_part in file_dir_parts:
            #     tmp_file_dir += file_dir_part + os.path.sep
            #     if os.path.isfile(tmp_file_dir + file_name):
            #         file_path = tmp_file_dir + file_name
            #         break

            # join the file name with the directory of the current viewing file
            if not os.path.isfile(file_path):
                file_dir  = os.path.dirname(self.view.file_name())
                file_dir  = self.normalize_path(file_dir)
                file_path = os.path.join(file_dir, file_name)

            # display a report message if the file is not found
            if not os.path.isfile(file_path):
                sublime.message_dialog("Not found file `%s`" % file_name)
                return

            print("Vublime -> Open `%s`" % file_path)

            # open the file on view
            self.view.window().open_file(file_path)
        pass
    pass

    def description(self) :
        return captions.get("open_file_in_view")

    def is_enabled(self) :
        return True

    def is_visible(self) :
        return True

    def normalize_path(self, path):
        return path.replace("\\\\", os.path.sep).replace("\\", os.path.sep).replace("/", os.path.sep)

# Report Logging

# https://regex101.com/

def RegEx(text, regex, flags = re.MULTILINE | re.IGNORECASE):
    result = re.findall(regex, text, flags)
    if len(result) == 1 and not type(result[0]) is tuple: result = [(result[0],)]
    return result

groups = [] # load from anywhere

groups = [
    {
        "name": "drag_enter",
        "pattern": r".*DragEnter -> ([\.\d]+)s",
        "type": "str",
    },
    {
        "name": "get_drag_window",
        "pattern": r".*GetDragWindow -> ([\.\d]+)s",
        "type": "int",
    },
    {
        "name": "update_drop_description",
        "pattern": r".*UpdateDropDescription -> ([\.\d]+)s",
        "type": "float",
    },
]

TYPES = {
    "str": str,
    "int": int,
    "float": float,
}

class VublimeReportLoggingInViewCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        # matches = self.view.find_all(r".*")

        selected_text = self.view.substr(self.view.line(self.view.sel()[0]))
        selected_text = selected_text.strip()
        # print(selected_text)

        result = {}

        for group in groups:
            name, pattern, dtype = group["name"], group["pattern"], group["type"]

            matches = RegEx(selected_text, pattern)
            # print(matches)

            numbers = list(map(lambda v:\
                TYPES[dtype](float(v))\
                if v.replace('.', '').isdigit()\
                else TYPES[dtype](0.), matches))

            total = 0 if TYPES[dtype] is str else sum(numbers)

            # print(name, numbers, total)
            if name in result.keys(): result[name] += total
            else: result[name] = total

        # df = pd.DataFrame(result)
        # print(df)

        total = sum(result.values())
        if total == 0:
            for k, v in result.items(): print(k, ":", v)
        else:
            for k, v in result.items(): print(k, ":", v, "(%.2f%%)" % (100 * float(v) / total))

        return

    def description(self) :
        return captions.get("report_logging_in_view")

    def is_enabled(self) :
        return True

    def is_visible(self) :
        return True