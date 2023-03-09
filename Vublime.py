# Vublime 1.0
# Author Vic P.

import os, tempfile, datetime, re, zipfile, json, yaml
import sublime, sublime_plugin, sublime_api
from sublime import View

VL_FILE_PATH = __file__
VL_FILE_NAME = os.path.basename(VL_FILE_PATH)
VL_FILE_NAME_NOEXT = os.path.splitext(VL_FILE_NAME)[0]
VL_FILE_DIR  = os.path.dirname(VL_FILE_PATH)
VL_FILE_SETTINGS   = VL_FILE_NAME_NOEXT + ".sublime-settings"

# Settings

settings = None
captions = None

# Extend built-in popup

VL_POPUP_TITLE = "<h1>Vublime</h1>"
VL_POPUP_STYLE = '''
<style>
    body {
        font-family: system;
    }
    h1 {
        font-size: 1.1rem;
        font-weight: bold;
        margin: 0 0 0.25em 0;
    }
    p {
        font-size: 1.05rem;
        margin: 0;
    }
</style>
'''

def _read_file_in_package(zip_file_path, file_name_inside_zip):
    if os.path.exists(zip_file_path) and zipfile.is_zipfile(zip_file_path):
        zip = zipfile.ZipFile(zip_file_path)
        with zip.open(file_name_inside_zip) as f:
            print(f, zip_file_path, file_name_inside_zip)
            return f.read()
    return None

def _get_executable_dir():
    return os.path.dirname(sublime.executable_path())

def _get_view_syntax(view):
    try :
        syntax_package_file_path = view.settings().get("syntax")
        if syntax_package_file_path.endswith(".sublime-syntax"):
            l = re.compile(r".*/(.*).sublime-syntax").findall(syntax_package_file_path)
            if len(l) == 1:
                sublime_syntax_file_name  = l[0] + ".sublime-syntax"
                sublime_package_file_path = l[0] + ".sublime-package"
                sublime_package_file_path = os.path.join(_get_executable_dir() + "/Packages", sublime_package_file_path)
                syntax_file_data = _read_file_in_package(sublime_package_file_path, sublime_syntax_file_name)
                if syntax_file_data:
                    syntax_file_yaml = yaml.load(syntax_file_data, Loader=yaml.loader.BaseLoader)
                    extensions = syntax_file_yaml["file_extensions"]
                    return (syntax_file_yaml["name"], syntax_file_yaml["file_extensions"][0])
        elif syntax_package_file_path.endswith(".tmLanguage"):
            print("not support tmLanguage")
    except Exception as e: print(e)
    return (None, None)

def _make_vl_popup_content(view, point) -> str:
    word = view.substr(view.word(point))
    return "Mouse is hovering on '" + word + "'"

def _make_vl_popup_body(view: View, point) -> str:
    result  = VL_POPUP_TITLE
    result += "<p>"
    result += _make_vl_popup_content(view, point)
    result += "</p>"
    return result

def _hooked_show_popup(self, content, flags=0, location=-1,
    max_width=320, max_height=240, on_navigate=None, on_hide=None):

    if content.find(VL_POPUP_TITLE) == -1:
        TAG_STYLE_CLOSED = "</style>"
        insert_position = content.find(TAG_STYLE_CLOSED) + len(TAG_STYLE_CLOSED) + 1

        new_content  = ""
        new_content += content[:insert_position]
        new_content += _make_vl_popup_body(self, location)
        new_content += "<br>"
        new_content += content[insert_position:]

        new_content = new_content.replace("<h1>Definition:</h1>", "<h1>Definition</h1>")
        new_content = new_content.replace("<h1>References:</h1>", "<h1>References</h1>")

        content = new_content

    sublime_api.view_show_popup(
        self.view_id, location, content, flags, max_width, max_height, on_navigate, on_hide)

# Listeners

class ViewTracking(sublime_plugin.ViewEventListener):
    def on_activated_async(self):
        pass # print(_get_view_syntax(self.view))

class HoverTextEventListener(sublime_plugin.EventListener):
  def on_hover(self, view, point, hover_zone):
    if not view.is_popup_visible():
        my_content  = ""
        my_content += "<body id=show-definitions>"
        my_content += VL_POPUP_STYLE
        my_content += _make_vl_popup_body(view, point)
        my_content += "</body>"
        view.show_popup(my_content, location=point)

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

# Report Logging

# https://regex101.com/

def RegEx(text, regex, flags = re.MULTILINE | re.IGNORECASE):
    result = re.findall(regex, text, flags)
    if len(result) == 1 and not type(result[0]) is tuple: result = [(result[0],)]
    return result

TYPES = {
    "str": str,
    "int": int,
    "float": float,
}

class VublimeReportLoggingInViewCommand(sublime_plugin.TextCommand):

    def run(self, edit):

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

            matches = RegEx(selected_text, pattern)
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

def plugin_loaded():

    global settings, captions
    settings = sublime.load_settings(VL_FILE_SETTINGS)
    captions = settings.get("captions")

    extend_popup = settings.get("extend_popup")
    if extend_popup: View.show_popup = _hooked_show_popup

    msg_ready = VL_FILE_NAME_NOEXT + " -> READY"
    sublime.status_message(msg_ready)
    print(msg_ready)
