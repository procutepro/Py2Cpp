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