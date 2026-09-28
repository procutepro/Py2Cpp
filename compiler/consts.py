import os
import sys

BUILD_INS = {
    "print": {
        "int": "int_py_print",
        "float": "float_py_print",
        "str": "str_py_print",
        "list": "list_py_print"
    },
    "len": {
        "list": "list_py_len",
        "str": "str_py_len",
    },
    "range": {
        "int": "_py_range",
    }
}

TRANSLATION = {
    int: "int",
    float: "float",
    str: "str",
    list: "list",
    tuple: "list",
}

# Return types for compiler/runtime built-ins.
BUILD_IN_RETURN_TYPES = {
    "print": "void",

    "len": "int",

    "range": ("list", "int"),
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
    str: "std::string",
    list: "std::vector<%>"
}

CPP_TYPE_CONVERSION = {
    "int": "int",
    "float": "float",
    "str": "std::string",
    "void": "void",
    ("list", "int"): "std::vector<int>",
    ("list", "str"): "std::vector<str>",
    ("list", "float"): "std::vector<float>",
}

# Special C++ representation for main().
CPP_MAIN_TYPE_CONVERSION = {
    "in": "int",
    "float": "float",
    "str": "std::string",
    "list": "char**",
    "void": "void"
}

def resource_path(relative_path):
    return os.path.join(os.path.abspath("."), relative_path)

with open(resource_path("compiler\\pystdlib.hpp"), "r") as f:
    PYSTDLIB = f.readlines()