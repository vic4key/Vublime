# Vublime 1.0
# Author Vic P.

import os, tempfile, datetime, re, zipfile, json, plistlib, webbrowser, base64
import sublime, sublime_plugin, sublime_api
from sublime import View

from . import yaml
from .make_var import *
from .pyperclip import copy as pyperclip_copy
from .sublime_text_popup_extended import *

_view_funcators = {}
_view_funcator  = None

VL_FILE_PATH = __file__
VL_FILE_NAME = os.path.basename(VL_FILE_PATH)
VL_FILE_NAME_NOEXT = os.path.splitext(VL_FILE_NAME)[0]
VL_FILE_DIR  = os.path.dirname(VL_FILE_PATH)
VL_FILE_SETTINGS   = VL_FILE_NAME_NOEXT + ".sublime-settings"

# Settings

settings = None
captions = None
extend_popup = None

def _reg_ex(text, regex, flags = re.MULTILINE | re.IGNORECASE): # https://regex101.com/
    result = re.findall(regex, text, flags)
    if len(result) == 1 and not type(result[0]) is tuple: result = [(result[0],)]
    return result

def _read_file_in_package(zip_file_path, file_name):
    if os.path.exists(zip_file_path) and zipfile.is_zipfile(zip_file_path):
        zip = zipfile.ZipFile(zip_file_path)
        with zip.open(file_name) as f: return f.read()
    return None

def _get_executable_dir():
    return os.path.dirname(sublime.executable_path())

def _get_view_syntax(view):
    regex_result = []
    package_folder = ""
    syntax_extension = ""
    syntax_package_file_path = view.settings().get("syntax")
    if syntax_package_file_path.endswith(".sublime-syntax"):
        syntax_extension = ".sublime-syntax"
        regex_result = re.compile(r".*/(.*)/(.*)" + syntax_extension).findall(syntax_package_file_path)[0]
    elif syntax_package_file_path.endswith(".tmLanguage"):
        syntax_extension = ".tmLanguage"
        regex_result = re.compile(r".*/(.*)/(.*)" + syntax_extension).findall(syntax_package_file_path)[0]
    package_file_name, syntax_file_name = regex_result[0], regex_result[1]
    sublime_package_file_path = None
    for package_folder in ["/Packages", "/Data/Installed Packages"]:
        tmp = os.path.join(_get_executable_dir() + package_folder, package_file_name + ".sublime-package")
        if os.path.exists(tmp):
            sublime_package_file_path = tmp
            break
    if sublime_package_file_path:
        sublime_syntax_file_name = syntax_file_name + syntax_extension
        syntax_file_content = _read_file_in_package(sublime_package_file_path, sublime_syntax_file_name)
        try: # yaml file from .sublime-syntax
            syntax_file = yaml.load(syntax_file_content, Loader=yaml.loader.BaseLoader)
            return (syntax_file["name"], syntax_file["file_extensions"][0])
        except: pass
        try: # plist file from .tmLanguage
            syntax_file = plistlib.readPlistFromBytes(syntax_file_content)
            return (syntax_file["name"], syntax_file["fileTypes"][0])
        except: pass
    return (None, None)

class Funcator():
    evaluator  = None
    translator = None
    def __init__(self, evaluator, translator):
        self.evaluator  = evaluator
        self.translator = translator

def _parser_Makefile(file_path):
    backup_cdir = os.getcwd()
    cdir = os.path.dirname(file_path)
    os.chdir(cdir)
    result = make_vars(origin=["makefile"])
    os.chdir(backup_cdir)
    return result

def _translator_Makefile(text):
    result = ""
    var = "$(%s)" % text
    var_expanded = make_expand(_view_funcator.evaluator, var)
    if var != var_expanded:
        result = var_expanded # "'$(%s)' => '%s'" % (text, var_expanded)
    return result

_mapping_funcators = {
    "Makefile": (_parser_Makefile, _translator_Makefile),
}

def my_popup_content(view, point) -> list:
    result = []
    word = view.substr(view.word(point))
    # Additional Information
    text = "No additional information for '%s'" % word
    global _view_funcator
    if _view_funcator:
        temp = _view_funcator.translator(word)
        if len(temp) > 0:
            # Display Additional Information
            text = "'$(%s)' => '%s'" % (word, temp)
            result.append(text)
            # Copy Additional Information to Clipboard
            temp = temp.encode("utf-8")
            temp = base64.b64encode(temp)
            temp = temp.decode("utf-8")
            text = "<a href='%s:%s'>Copy Additional Information to Clipboard</a>" % (VL_FILE_NAME_NOEXT, temp)
            result.append(text)
        else:
            result.append(text)
    # Google
    text = "<a href='http://www.google.com/search?q=%s'>Search Google for '%s'</a>" % (word, word)
    result.append(text)
    # Bing
    text = "<a href='https://www.bing.com/search?q=%s'>Search Bing for '%s'</a>" % (word, word)
    result.append(text)
    # Wikipedia
    text = "<a href='https://en.wikipedia.org/wiki/Special:Search?search=%s'>Search Wikipedia for '%s'</a>" % (word, word)
    result.append(text)
    # Others
    # your code here
    return result

def my_on_navigate(href) -> None:
    if href.startswith("http"):
        webbrowser.open(url=href)
    elif href.startswith(VL_FILE_NAME_NOEXT):
        temp = href[len(VL_FILE_NAME_NOEXT)+1:] # +1 for ":"
        temp = base64.b64decode(temp)
        temp = temp.decode("utf-8")
        pyperclip_copy(temp)

# Listener - View Tracking

class VublimeViewTracking(sublime_plugin.ViewEventListener):
    def on_activated_async(self):
        global extend_popup
        if extend_popup:
            file_path = self.view.file_name()
            if type(file_path) is bytes: file_path = file_path.decode("utf-8")
            file_path = str(file_path)
            file_name = os.path.basename(file_path)
            file_type, _ = _get_view_syntax(self.view)
            key = "%s_%s" % (file_type, file_name)
            global _view_funcators
            if not key in _view_funcators.keys():
                funcator = _mapping_funcators.get(file_type)
                if funcator:
                    _view_funcators[key] = Funcator(funcator[0](file_path), funcator[1])
                    print(VL_FILE_NAME_NOEXT + " -> '%s' -> Ready" % key)
            global _view_funcator
            _view_funcator = _view_funcators.get(key)

# Command - About

class VublimeAboutCommand(sublime_plugin.TextCommand) :

    def description(self) :
        return captions.get("about")

    def is_enabled(self) :
        return True

    def is_visible(self) :
        return True

    def run(self, edit) :
        sublime.message_dialog(captions.get("info"))

# Command - Save Unsaved View as Temporary

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
            _, extension = _get_view_syntax(self.view)
            if len(extension) > 0 :
                file_path += "."
                file_path += extension

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

    def save_as_temporary(self, file_path) :
        # save to temporary directory
        self.view.retarget(file_path)
        self.view.run_command("save")
        sublime.status_message("Saved as '%s'" % file_path)

# Command - Open File in View

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
            if file_path.startswith(("\\", "/")):
                file_path = file_name[1:]

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

    def description(self) :
        return captions.get("open_file_in_view")

    def is_enabled(self) :
        return True

    def is_visible(self) :
        return True

    def normalize_path(self, path):
        return path.replace("\\\\", os.path.sep).replace("\\", os.path.sep).replace("/", os.path.sep)

# Command - Report Logging

class VublimeReportLoggingInViewCommand(sublime_plugin.TextCommand):

    def run(self, edit):

        TYPES = {
            "str": str,
            "int": int,
            "float": float,
        }

        # load patterns from json file
        groups = []
        Vublime_json = "Vublime.json"
        try:
            file_path = os.path.join(VL_FILE_DIR, Vublime_json)
            with open(file_path, "r", encoding="utf8") as f:
                groups = json.load(f)["groups"]
        except Exception as e:
            print("Failed to load file '%s'" % Vublime_json, e)
            return
        # print(groups)

        # matches = self.view.find_all(r".*")
        # print(matches)

        selected_text = self.view.substr(self.view.line(self.view.sel()[0]))
        selected_text = selected_text.strip()
        # print(selected_text)

        result = {}

        for group in groups:
            name, pattern, dtype = group["name"], group["pattern"], group["type"]

            matches = _regex(selected_text, pattern)
            # print(matches)

            try:
                numbers = list(map(lambda v:\
                    TYPES[dtype](float(v))\
                    if v.replace('.', '').isdigit()\
                    else TYPES[dtype](0.), matches))
            except Exception as e:
                print("ERROR: An error has occurred in `%s` (%s)" % (name, str(e)))

            total = 0
            try:
                total = 0 if TYPES[dtype] is str else sum(numbers)
            except KeyError as e:
                print("ERROR: Not yet defined groups in `Vublime.json`")
                return
            except Exception as e:
                print(e)
                return

            # print(name, numbers, total)
            if name in result.keys(): result[name] += total
            else: result[name] = total

        # df = pd.DataFrame(result)
        # print(df)

        print(" [REPORT] ".center(80, "-"))

        total = sum(result.values())

        for group in groups:
            name, _, __ = group["name"], group["pattern"], group["type"]
            if name in result.keys():
                k, v = name, result[name]
                if total == 0:
                    print("%s : %.3f" % (k, float(v)))
                else:
                    print("%s : %.3f" % (k, float(v)))
                    # print("%s : %.3f (%.2f%%)" % (k, float(v), (100 * float(v) / total)))

    def description(self) :
        return captions.get("report_logging_in_view")

    def is_enabled(self) :
        return True

    def is_visible(self) :
        return True

class NewInputItemHandler(sublime_plugin.ListInputHandler):
    # https://github.com/sublimehq/sublime_text/issues/3882

    def list_items(self):
        items = []
        active_view = sublime.active_window().active_view()
        for window in sublime.windows():
            for view in window.views():
                if view == active_view: continue
                group_id, _ = window.get_view_index(view)
                view_id = view.id()
                view_name = view.name() or view.file_name().split("\\")[-1]
                item = sublime.ListInputItem(
                    text = f"Group {group_id}: {view_name}",
                    value = view_id,
                    details = "" if not view.is_dirty() else "*Modified*",
                    annotation = "" if view.file_name() else "*Untitled*",
                    kind = (sublime.KIND_ID_SNIPPET, "T", "Text Command")
                )
                items.append(item)
        return items

    def placeholder(self):
        active_view = sublime.active_window().active_view()
        return f"The base view is '{active_view.name()}' ..."

    def confirm(self, selected_item):
        pass # print(selected_item)

    def is_enabled(self, dirs=None):
        return True

    def is_visible(self, dirs=None):
        return True

class VublimeReportLinesMatchingCommand(sublime_plugin.WindowCommand):

    def run(self, new_input_item_handler):
        print("\n")

        selected_view_id = new_input_item_handler
        selected_view = sublime.View(selected_view_id)
        if not (selected_text_in_selected_view := selected_view.substr(selected_view.line(selected_view.sel()[0])).strip()):
            print("Not selected text in the selected view.")
            return

        active_window = sublime.active_window()
        active_view   = active_window.active_view()
        if not (selected_text_in_active_view := active_view.substr(active_view.line(active_view.sel()[0])).strip()):
            print("Not selected text in the active view.")
            return

        d = {
            "included": [],
            "excluded": [],
        }

        normed_selected_lines_in_selected_view = [line.strip().lower() for line in selected_text_in_selected_view.split("\n")]

        for line in selected_text_in_active_view.split("\n"):
            if normed_line := line.strip().lower():
                if normed_line in normed_selected_lines_in_selected_view:
                    d["included"].append(line)
                else:
                    d["excluded"].append(line)

        print(f"List MATCHED items of the active view '{active_view.name()}' in the selected view '{selected_view.name()}' are following:")
        if d["included"]:
            for line in d["included"]: print("\t" + line)
        else: print("\t<N/A>")

        print(f"List NOT MATCHED items of the active view '{active_view.name()}' in the selected view '{selected_view.name()}' are following:")
        if d["excluded"]:
            for line in d["excluded"]: print("\t" + line)
        else: print("<N/A>")

        active_window.run_command("show_panel", {"panel": "console"})

    def input(self, args):
        if args is not None: return NewInputItemHandler()

    def description(self) :
        return captions.get("report_lines_matching")

class VublimeEvaluateExpressionLines(sublime_plugin.TextCommand):

    def run(self, edit):
        print("\n")

        active_window = sublime.active_window()
        active_view   = active_window.active_view()
        if not (selected_text_in_active_view := active_view.substr(active_view.line(active_view.sel()[0])).strip()):
            print("Not selected text in the active view.")
            return

        print(f"The results of the selected expressions in the active view '{active_view.name()}' are following:")
        for line in selected_text_in_active_view.split("\n"):
            if normed_line := line.strip().lower():
                try:
                    result = eval(normed_line)
                    if type(result) is float: result = result
                    print(f"{normed_line} = {result}")
                except:
                    print(f"{normed_line} = <ERROR: EVALUTATION FAILED>")

        active_window.run_command("show_panel", {"panel": "console"})

    def description(self) :
        return captions.get("evaluate_expression_lines")

    def is_enabled(self) :
        return True

    def is_visible(self) :
        return True

# Plugin Entry Point

def plugin_loaded():

    global settings, captions
    settings = sublime.load_settings(VL_FILE_SETTINGS)
    captions = settings.get("captions")

    global extend_popup
    extend_popup = settings.get("extend_popup")
    if extend_popup:
        sublime_text_popup_extended.setup(
            heading_text=VL_FILE_NAME_NOEXT,
            fn_popup_content=my_popup_content,
            fn_on_navigate=my_on_navigate)

    msg_ready = VL_FILE_NAME_NOEXT + " -> READY"
    sublime.status_message(msg_ready)
    print(msg_ready)
