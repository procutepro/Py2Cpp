import script
import types
from consts import *

class Compiler:
    def __init__(self, filename):
        self.filename = filename
        self.bytecode = script.Script(filename)

        self.stack = []
        self.ir = []

        self.variable_types = {}
        self.variable_names = {}

        self.temp_counter = 0
        self.in_for_loop = False

    # ============================================================
    # COMPILER STATE
    # ============================================================

    def reset_function_state(self):
        self.stack = []
        self.ir = []

        self.variable_types = {}
        self.variable_names = {}

        self.temp_counter = 0
        self.in_for_loop = False

    def new_temp(self):
        name = f"temp{self.temp_counter}"
        self.temp_counter += 1
        return name

    # ============================================================
    # TYPE HELPERS
    # ============================================================

    def normalize_type(self, value_type):
        """
        Convert internal type representations into a predictable form.

        Examples:
            int              -> int
            "int"             -> "int"
            ("list", int)    -> ("list", int)
            ("list", "int")  -> ("list", "int")
        """

        if isinstance(value_type, tuple):
            if len(value_type) != 2:
                return value_type

            container_type, element_type = value_type

            if not isinstance(element_type, str):
                element_type = TRANSLATION.get(
                    element_type,
                    element_type,
                )

            return container_type, element_type

        if isinstance(value_type, str):
            return value_type

        return TRANSLATION.get(value_type, value_type)

    def get_list_element_type(self, value_type):
        """
        Extract the element type from a list-like internal type.
        """

        value_type = self.normalize_type(value_type)

        if isinstance(value_type, tuple):
            return value_type[1]

        return "valuable"

    def type_of_value(self, value):
        """
        Safely determine the internal type of a Python constant.
        """

        python_type = type(value)

        if python_type in TRANSLATION:
            return TRANSLATION[python_type]

        return "valuable"

    def cpp_type(
        self,
        python_type,
        first_arg=None,
        function_name=None,
        val_name=None,
    ):
        python_type = self.normalize_type(python_type)

        if isinstance(python_type, str):
            return python_type

        if (
            function_name == "main"
            and val_name == "argv"
            and python_type in CPP_MAIN_TYPE_CONVERSION
        ):
            return CPP_MAIN_TYPE_CONVERSION[python_type]

        replace_string = "%"

        if isinstance(first_arg, list) and first_arg:
            replace_string = self.type_of_value(first_arg[0])

        if python_type in CPP_TYPE_CONVERSION:
            return CPP_TYPE_CONVERSION[python_type].replace(
                "%",
                replace_string,
            )

        if python_type in CPP_OTHER_CONVERSION:
            return CPP_OTHER_CONVERSION[python_type].replace(
                "%",
                replace_string,
            )

        raise TypeError(
            f"No C++ type mapping for {python_type!r}"
        )

    # ============================================================
    # HALF PASS: BYTECODE -> FUNCTIONS
    # ============================================================

    def half_pass(self):
        stack = []
        functions = {}

        for instruction in self.bytecode.better_instructions.values():
            opname = instruction["opname"]
            arg = instruction["arg"]

            if opname in {"LOAD_NAME", "LOAD_CONST"}:
                stack.append(arg)

            elif opname == "BUILD_TUPLE":
                if arg:
                    values = stack[-arg:]

                    for _ in range(arg):
                        stack.pop()
                else:
                    values = []

                stack.append(values)

            elif opname == "MAKE_FUNCTION":
                function = stack.pop()

                annotations = stack.pop()

                if not isinstance(annotations, (list, tuple)):
                    annotations = []

                input_annotations = {}

                arg_names = list(
                    function.co_varnames[:function.co_argcount]
                )

                arg_names.append("return")

                annotation_map = dict(
                    zip(
                        annotations[::2],
                        annotations[1::2],
                    )
                )

                for argument_name in arg_names:
                    if argument_name not in annotation_map:
                        raise TypeError(
                            f"Missing annotation for "
                            f"{function.co_name}.{argument_name}"
                        )

                    input_annotations[argument_name] = (
                        annotation_map[argument_name]
                    )

                functions[function.co_name] = (
                    input_annotations,
                    function,
                )

        return functions

    # ============================================================
    # FIRST PASS: BYTECODE -> IR
    # ============================================================

    def first_pass(self, bytecode, functions):
        for instruction in bytecode.better_instructions.values():
            opname = instruction["opname"]
            arg = instruction["arg"]
            offset = instruction["offset"]
            is_jump = instruction["is_jump_instruction"]

            # ----------------------------------------------------
            # LABELS
            # ----------------------------------------------------

            if is_jump and not self.in_for_loop:
                self.emit_label(offset)

            # ----------------------------------------------------
            # CONSTANTS
            # ----------------------------------------------------

            if opname == "LOAD_CONST":
                self.stack.append({
                    "type": self.type_of_value(arg),
                    "data": arg,
                    "opname": opname,
                })

            # ----------------------------------------------------
            # VARIABLES
            # ----------------------------------------------------

            elif opname in {
                "LOAD_NAME",
                "LOAD_FAST",
                "LOAD_GLOBAL",
            }:
                variable_name = self.variable_names.get(
                    arg,
                    arg,
                )

                value_type = self.variable_types.get(
                    variable_name,
                    "valuable",
                )

                value_type = self.normalize_type(value_type)

                self.stack.append({
                    "type": value_type,
                    "data": variable_name,
                    "opname": opname,
                })

            # ----------------------------------------------------
            # LISTS
            # ----------------------------------------------------

            elif opname == "BUILD_LIST":
                self.stack.append({
                    "type": ("list", "valuable"),
                    "data": [],
                    "opname": opname,
                })

            elif opname == "LIST_EXTEND":
                if len(self.stack) < 2:
                    raise RuntimeError(
                        "LIST_EXTEND encountered with insufficient "
                        "values on compiler stack."
                    )

                thing = self.stack.pop()
                target = self.stack.pop()

                if not isinstance(target["data"], list):
                    raise TypeError(
                        "LIST_EXTEND target is not a list."
                    )

                if isinstance(thing["data"], list):
                    values = thing["data"]
                else:
                    values = [thing["data"]]

                target["data"].extend(values)

                if values:
                    element_type = self.type_of_value(values[0])

                    target_type = (
                        "list",
                        element_type,
                    )
                else:
                    target_type = (
                        "list",
                        "valuable",
                    )

                self.stack.append({
                    "type": target_type,
                    "data": target["data"],
                    "opname": opname,
                })

            elif opname == "LIST_APPEND":
                value = self.stack.pop()
                target = self.stack.pop()

                if not isinstance(target["data"], list):
                    raise TypeError(
                        "LIST_APPEND target is not a list."
                    )

                target["data"].append(value["data"])

                target["type"] = (
                    "list",
                    value["type"],
                )

                self.stack.append(target)

            elif opname in {
                "STORE_NAME",
                "STORE_FAST",
            }:
                if not self.stack:
                    raise RuntimeError(
                        f"{opname} encountered with an empty stack."
                    )

                value = self.stack.pop()
                variable_name = arg

                value_type = self.normalize_type(value["type"])

                # If we're storing a list, preserve its element type.
                if isinstance(value["data"], list):
                    if value["data"]:
                        value_type = (
                            "list",
                            self.type_of_value(value["data"][0]),
                        )
                    else:
                        value_type = ("list", "valuable")

                self.variable_types[variable_name] = value_type
                self.variable_names[variable_name] = variable_name

                self.ir.append({
                    "type": "valuable",
                    "data_type": value_type,
                    "data": value["data"],
                    "name": variable_name,
                })

            # ----------------------------------------------------
            # JUMPS
            # ----------------------------------------------------

            elif opname in {
                "JUMP_BACKWARD",
                "JUMP_FORWARD",
            }:
                if not self.in_for_loop:
                    self.ir.append({
                        "type": "moonwalk",
                        "jump": arg,
                    })

            elif opname == "POP_JUMP_IF_FALSE":
                if not self.stack:
                    raise RuntimeError(
                        "POP_JUMP_IF_FALSE encountered with empty stack."
                    )

                expression = self.stack.pop()

                self.ir.append({
                    "type": "if",
                    "data": expression,
                    "jump": arg,
                })

            # ----------------------------------------------------
            # FOR LOOP
            # ----------------------------------------------------

            elif opname == "FOR_ITER":
                if not self.stack:
                    raise RuntimeError(
                        "FOR_ITER encountered with empty stack."
                    )

                iterable = self.stack.pop()
                iterable_name = iterable["data"]

                iterable_type = self.variable_types.get(
                    iterable_name,
                    iterable["type"],
                )

                element_type = self.get_list_element_type(
                    iterable_type
                )

                iter_name = self.new_temp()

                self.ir.append({
                    "type": "FOR",
                    "valuable": iterable_name,
                    "iter_name": iter_name,
                    "element_type": element_type,
                })

                self.in_for_loop = True

                self.stack.append({
                    "type": element_type,
                    "data": iter_name,
                    "opname": "FOR_ITER",
                })

            elif opname == "END_FOR":
                self.ir.append({
                    "type": "END_FOR"
                })

                self.in_for_loop = False

            # ----------------------------------------------------
            # OPERATIONS
            # ----------------------------------------------------

            elif opname == "COMPARE_OP":
                right = self.stack.pop()
                left = self.stack.pop()

                self.stack.append({
                    "type": "bool",
                    "data": (
                        f"({left['data']} "
                        f"{arg} "
                        f"{right['data']})"
                    ),
                    "opname": opname,
                })

            elif opname == "BINARY_OP":
                self.compile_binary_op(arg)

            # ----------------------------------------------------
            # SUBSCRIPT
            # ----------------------------------------------------

            elif opname == "BINARY_SUBSCR":
                index = self.stack.pop()
                sequence = self.stack.pop()

                sequence_name = sequence["data"]

                sequence_type = self.variable_types.get(
                    sequence_name,
                    sequence["type"],
                )

                element_type = self.get_list_element_type(
                    sequence_type
                )

                self.stack.append({
                    "type": element_type,
                    "data": (
                        f"{sequence_name}"
                        f"[{index['data']}]"
                    ),
                    "opname": opname,
                })

            # ----------------------------------------------------
            # RETURNS
            # ----------------------------------------------------

            elif opname == "RETURN_CONST":
                self.ir.append({
                    "type": "return",
                    "value": {
                        "type": self.type_of_value(arg),
                        "data": arg,
                    },
                })

            elif opname == "RETURN_VALUE":
                if not self.stack:
                    raise RuntimeError(
                        "RETURN_VALUE encountered with empty stack."
                    )

                value = self.stack.pop()

                self.ir.append({
                    "type": "return",
                    "value": value,
                })

            # ----------------------------------------------------
            # FUNCTION CALL
            # ----------------------------------------------------

            elif opname == "CALL":
                self.compile_call(
                    arg,
                    functions,
                )

    # ============================================================
    # IR HELPERS
    # ============================================================

    def emit_label(self, offset):
        self.ir.append({
            "type": "label",
            "name": offset,
        })

    # ============================================================
    # BINARY OPERATIONS
    # ============================================================

    def compile_binary_op(self, opcode):
        if len(self.stack) < 2:
            raise RuntimeError(
                "BINARY_OP encountered with insufficient "
                "values on stack."
            )

        right = self.stack.pop()
        left = self.stack.pop()

        left_type = self.normalize_type(left["type"])
        right_type = self.normalize_type(right["type"])

        if (
            left_type == "float"
            or right_type == "float"
        ):
            result_type = "float"

        elif (
            left_type == "str"
            or right_type == "str"
        ):
            result_type = "str"

        else:
            result_type = "int"

        if opcode not in OPCODE_TRANSLATION:
            raise NotImplementedError(
                f"Unsupported BINARY_OP opcode: {opcode}"
            )

        self.stack.append({
            "type": result_type,
            "data": (
                f"({left['data']} "
                f"{OPCODE_TRANSLATION[opcode]} "
                f"{right['data']})"
            ),
            "opname": "BINARY_OP",
        })

    # ============================================================
    # FUNCTION CALLS
    # ============================================================

    def compile_call(self, argument_count, functions):
        required = argument_count + 1

        if len(self.stack) < required:
            raise RuntimeError(
                "CALL encountered with insufficient "
                "values on compiler stack."
            )

        values = self.stack[-required:]

        function = values[0]
        args = values[1:]

        for _ in range(required):
            self.stack.pop()

        function_name = function["data"]

        # --------------------------------------------------------
        # Built-in function
        # --------------------------------------------------------

        argument_type = self.normalize_type(
                        args[0]["type"]
                    )

        if function_name in BUILD_INS:
            if not args:
                raise TypeError(
                    f"Built-in function '{function_name}' "
                    f"requires an argument."
                )

            argument_type = self.normalize_type(
                args[0]["type"]
            )

            if isinstance(argument_type, tuple):
                argument_type = argument_type[0]

            try:
                cpp_function_name = BUILD_INS[
                    function_name
                ][argument_type]
            except KeyError:
                raise TypeError(
                    f"No built-in implementation for "
                    f"{function_name}({argument_type})"
                )

            return_type = BUILD_IN_RETURN_TYPES[
                function_name
            ]

            function_name = cpp_function_name

        # --------------------------------------------------------
        # User-defined function
        # --------------------------------------------------------

        elif function_name in functions:
            return_type = functions[
                function_name
            ][0]["return"]

        else:
            raise NameError(
                f"Unknown function: {function_name}"
            )

        return_type = self.normalize_type(return_type)

        temp_name = self.new_temp()

        self.ir.append({
            "type": "function_call",
            "return_type": return_type,
            "function_to_run": function_name,
            "args": args,
            "result": temp_name,
        })

        self.stack.append({
            "type": return_type,
            "data": temp_name,
            "opname": "CALL",
        })

    # ============================================================
    # C++ LITERAL HELPERS
    # ============================================================

    def cpp_string_literal(self, value):
        escaped = (
            str(value)
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )

        return f'"{escaped}"'

    def cpp_value(self, value, value_type=None):
        value_type = self.normalize_type(value_type)

        if value_type == "str":
            return self.cpp_string_literal(value)

        if isinstance(value, list):
            values = ", ".join(
                self.cpp_value(
                    item,
                    self.type_of_value(item),
                )
                for item in value
            )

            return f"{{{values}}}"

        if value is None:
            return "{}"

        if value is True:
            return "true"

        if value is False:
            return "false"

        return str(value)

    # ============================================================
    # SECOND PASS: IR -> C++
    # ============================================================

    def emit_cpp(
        self,
        input_annotations,
        function_name,
        args,
    ):
        declarations = []
        seen = set()

        # --------------------------------------------------------
        # Local variable declarations
        # --------------------------------------------------------

        for instruction in self.ir:
            if instruction["type"] != "valuable":
                continue

            variable_name = instruction["name"]

            if variable_name in seen:
                continue

            data_type = self.normalize_type(
                instruction["data_type"]
            )

            cpp_type = self.cpp_type(
                data_type,
                instruction["data"],
                function_name,
                variable_name,
            )

            if variable_name not in args:
                declarations.append(
                    f"{cpp_type} {variable_name};"
                )

            seen.add(variable_name)

        # --------------------------------------------------------
        # Function arguments
        # --------------------------------------------------------

        arguments = []

        for argument_name, argument_type in (
            list(input_annotations.items())[:-1]
        ):
            argument_type = self.normalize_type(
                argument_type
            )

            cpp_type = self.cpp_type(
                argument_type,
                None,
                function_name,
                argument_name,
            )

            arguments.append(
                f"{cpp_type} {argument_name}"
            )

        arg_formation = ", ".join(arguments)

        # --------------------------------------------------------
        # Return type
        # --------------------------------------------------------

        return_type = self.normalize_type(
            input_annotations["return"]
        )

        return_type = self.cpp_type(
            return_type,
            None,
            function_name,
            None,
        )

        function_definition = (
            f"{return_type} "
            f"{function_name}"
            f"({arg_formation}) {{"
        )

        generated_code = [
            function_definition,
            *declarations,
        ]

        # --------------------------------------------------------
        # Emit IR
        # --------------------------------------------------------

        for instruction in self.ir:
            instruction_type = instruction["type"]

            # ----------------------------------------------------
            # Label
            # ----------------------------------------------------

            if instruction_type == "label":
                generated_code.append(
                    f"T{function_name}"
                    f"{instruction['name']}:"
                )

            # ----------------------------------------------------
            # Return
            # ----------------------------------------------------

            elif instruction_type == "return":
                value = instruction["value"]

                generated_code.append(
                    f"return "
                    f"{self.cpp_value(value['data'], value['type'])};"
                )

            # ----------------------------------------------------
            # Backward / forward jump
            # ----------------------------------------------------

            elif instruction_type == "moonwalk":
                generated_code.append(
                    f"goto "
                    f"T{function_name}"
                    f"{instruction['jump']};"
                )

            # ----------------------------------------------------
            # Conditional jump
            # ----------------------------------------------------

            elif instruction_type == "if":
                expression = instruction["data"]["data"]

                generated_code.append(
                    f"if (!({expression})) {{"
                )

                generated_code.append(
                    f"    goto "
                    f"T{function_name}"
                    f"{instruction['jump']};"
                )

                generated_code.append("}")

            # ----------------------------------------------------
            # Variable assignment
            # ----------------------------------------------------

            elif instruction_type == "valuable":
                variable_name = instruction["name"]
                value = instruction["data"]
                value_type = instruction["data_type"]

                generated_code.append(
                    f"{variable_name} = "
                    f"{self.cpp_value(value, value_type)};"
                )

            # ----------------------------------------------------
            # FOR
            # ----------------------------------------------------

            elif instruction_type == "FOR":
                iterable_name = instruction["valuable"]
                iter_name = instruction["iter_name"]
                element_type = instruction["element_type"]

                element_type = self.cpp_type(
                    element_type,
                    None,
                    function_name,
                    None,
                )

                generated_code.append(
                    f"for ("
                    f"{element_type} "
                    f"{iter_name} : "
                    f"{iterable_name}"
                    f") {{"
                )

            elif instruction_type == "END_FOR":
                generated_code.append("}")

            # ----------------------------------------------------
            # Function call
            # ----------------------------------------------------

            elif instruction_type == "function_call":
                function = instruction["function_to_run"]
                args = instruction["args"]
                result = instruction["result"]

                arg_strings = []

                for argument in args:
                    value = argument["data"]
                    value_type = argument["type"]

                    arg_strings.append(
                        self.cpp_value(
                            value,
                            value_type,
                        )
                    )

                arguments = ", ".join(arg_strings)

                return_type = self.cpp_type(
                    instruction["return_type"],
                    None,
                    function_name,
                    None,
                )

                if return_type != "void":
                    generated_code.append(
                        f"{return_type} {result} = "
                        f"{function}({arguments});"
                    )
                else:
                    generated_code.append(
                        f"{function}({arguments});"
                    )

        generated_code.append("}")

        return generated_code

    # ============================================================
    # WRITE OUTPUT
    # ============================================================

    def compile(self, output_file):
        generated_code = [
            "#include <iostream>",
            "#include <string>",
            "#include <vector>",
        ]

        generated_code.extend(PYSTDLIB)

        functions = self.half_pass()

        for function_name, (
            annotations,
            function_code,
        ) in functions.items():

            function_code: types.CodeType

            print(
                f"\n===== COMPILING {function_name} ====="
            )

            self.reset_function_state()

            # Function arguments get their declared types
            # before bytecode processing starts.
            for arg_name, arg_type in list(
                annotations.items()
            )[:function_code.co_argcount]:

                self.variable_types[arg_name] = (
                    self.normalize_type(arg_type)
                )

                self.variable_names[arg_name] = arg_name

            args = list(
                self.variable_types.keys()
            )

            function_bytecode = script.Script(
                function_code
            )

            self.first_pass(
                function_bytecode,
                functions,
            )

            generated_function = self.emit_cpp(
                annotations,
                function_name,
                args,
            )

            generated_code.extend(
                generated_function
            )

            generated_code.append("")

        with open(
            output_file,
            "w",
            encoding="utf-8",
        ) as file:
            file.write(
                "\n".join(generated_code)
            )
            file.write("\n")