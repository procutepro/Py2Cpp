import os
import sys

BUILD_INS = {
    "print": {
        "int": "int_py_print",
        "float": "float_py_print",
        "str": "str_py_print",
    }
}

TRANSLATION = {
    int: "int",
    str: "str",
}

# Return types for compiler/runtime built-ins.
BUILD_IN_RETURN_TYPES = {
    "int_py_print": "void",
    "float_py_print": "void",
    "str_py_print": "void",
}

OPCODE_TRANSLATION = {
    0: "+",
    5: "*",
    10: "-",
    11: "/",
}

CPP_OTHER_CONVERSION = {
    int: "int",
    float: "float",
    str: "std::string"
}

CPP_TYPE_CONVERSION = {
    "int": "int",
    "float": "float",
    "str": "std::string",
    "void": "void"
}

# Special C++ representation for main().
CPP_MAIN_TYPE_CONVERSION = {
    "int": "int",
    "float": "float",
    "str": "std::string",
    "list": "char**",
    "void": "void"
}

def resource_path(relative_path):
    """Get the absolute path to a resource, works for dev and PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

with open(resource_path("pystdlib.hpp"), "r") as f:
    PYSTDLIB = f.readlines()