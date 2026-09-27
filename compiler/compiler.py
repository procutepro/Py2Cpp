from consts import *
import script as script
import types

class Compiler:
    def __init__(self, filename):
        self.filename = filename
        self.bytecode = script.Script(filename)

        self.stack = []
        self.ir = []

        self.variable_types = {}
        self.variable_names = {}

        self.temp_counter = 0

    # COMPILER STATE
    def reset_function_state(self):
        self.stack = []
        self.ir = []

        self.variable_types = {}
        self.variable_names = {}

        self.temp_counter = 0

    def new_temp(self):
        name = f"temp{self.temp_counter}"
        self.temp_counter += 1
        return name

    # 0.5 PASS: BYTECODE -> FUNCTIONS

    def half_pass(self):
        stack = []
        functions = {}

        for instruction in self.bytecode.better_instructions.values():
            opname = instruction["opname"]
            arg = instruction["arg"]

            if opname in {"LOAD_NAME", "LOAD_CONST"}:
                stack.append(arg)

            elif opname == "BUILD_TUPLE":
                values = stack[-arg:]

                for _ in range(arg):
                    stack.pop()

                stack.append(values)

            elif opname == "MAKE_FUNCTION":
                function: types.CodeType = stack.pop()
                annotations = stack.pop()

                annotations = list(annotations)

                input_annotations = {}

                arg_names = list(
                    function.co_varnames[:function.co_argcount]
                )

                arg_names.append("return")

                # Python's annotation representation is:
                #
                # ("arg1", type1, "arg2", type2, ..., "return", type)
                #
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

    # FIRST PASS: BYTECODE -> IR

    def first_pass(self, bytecode, functions):
        for instruction in bytecode.better_instructions.values():
            opname = instruction["opname"]
            arg = instruction["arg"]
            offset = instruction["offset"]
            is_jump = instruction["is_jump_instruction"]

            if is_jump:
                self.emit_label(offset)

            # CONSTANTS

            if opname == "LOAD_CONST":
                self.stack.append({
                    "type": TRANSLATION[type(arg)],
                    "data": arg,
                    "opname": opname,
                })

            # VARIABLES

            elif opname in {
                "LOAD_NAME",
                "LOAD_FAST",
                "LOAD_GLOBAL",
            }:
                variable_name = self.variable_names.get(arg, arg)

                self.stack.append({
                    "type": self.variable_types.get(
                        variable_name,
                        "valuable",
                    ),
                    "data": variable_name,
                    "opname": opname,
                })

            elif opname in ["STORE_NAME", "STORE_FAST"]:
                value = self.stack.pop()

                variable_name = arg

                self.variable_types[variable_name] = value["type"]
                self.variable_names[variable_name] = variable_name

                self.ir.append({
                    "type": "valuable",
                    "data_type": value["type"],
                    "data": value["data"],
                    "name": variable_name,
                })

            # JUMPS

            elif opname in {
                "JUMP_BACKWARD",
                "JUMP_FORWARD",
            }:
                self.ir.append({
                    "type": "moonwalk",
                    "jump": arg,
                })

            elif opname == "POP_JUMP_IF_FALSE":
                expression = self.stack.pop()

                self.ir.append({
                    "type": "if",
                    "data": expression,
                    "jump": arg,
                })

            # OPERATIONS

            elif opname == "COMPARE_OP":
                right = self.stack.pop()
                left = self.stack.pop()

                self.stack.append({
                    "type": bool,
                    "data": (
                        f"({left['data']} "
                        f"{arg} "
                        f"{right['data']})"
                    ),
                })

            elif opname == "BINARY_OP":
                self.compile_binary_op(arg)

            # RETURNS

            elif opname == "RETURN_CONST":
                self.ir.append({
                    "type": "return",
                    "value": {
                        "type": "int",
                        "data": arg,
                    },
                })

            elif opname in ["RETURN_VALUE", "RETURN_CONST"]:
                value = self.stack.pop()

                self.ir.append({
                    "type": "return",
                    "value": value,
                })

            # FUNCTION CALL

            elif opname == "CALL":
                self.compile_call(
                    arg,
                    functions,
                )

    # IR HELPERS

    def emit_label(self, offset):
        self.ir.append({
            "type": "label",
            "name": offset,
        })

    # BINARY OPERATIONS

    def compile_binary_op(self, opcode):
        right = self.stack.pop()
        left = self.stack.pop()

        if left["type"] == float or right["type"] == float:
            result_type = float

        elif left["type"] == str or right["type"] == str:
            result_type = str

        else:
            result_type = int

        self.stack.append({
            "type": result_type,
            "data": (
                f"({left['data']} "
                f"{OPCODE_TRANSLATION[opcode]} "
                f"{right['data']})"
            ),
            "opname": "BINARY_OP",
        })

    # FUNCTION CALLS

    def compile_call(self, argument_count, functions):
        values = self.stack[-(argument_count + 1):]

        function = values[0]
        args = values[1:]

        for _ in range(argument_count + 1):
            self.stack.pop()

        function_name = function["data"]

        # Built-in function

        if function_name in list(BUILD_INS.keys()):
            if not args:
                raise TypeError(
                    f"Built-in function '{function_name}' "
                    f"requires an argument."
                )

            argument_type = args[0]["type"]

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
                cpp_function_name
            ]

            function_name = cpp_function_name

        # User-defined function

        elif function_name in functions:
            return_type = functions[
                function_name
            ][0]["return"]

        else:
            raise NameError(
                f"Unknown function: {function_name}"
            )

        # Generate unique temporary

        temp_name = self.new_temp()

        self.ir.append({
            "type": "function_call",
            "return_type": return_type,
            "function_to_run": function_name,
            "args": args,
            "result": temp_name,
        })

        # Function call leaves its result on the VM stack.
        self.stack.append({
            "type": return_type,
            "data": temp_name,
            "opname": "CALL",
        })

    # TYPE CONVERSION

    def cpp_type(self, python_type, function_name=None):
        if function_name == "main":
            if python_type in CPP_MAIN_TYPE_CONVERSION:
                return CPP_MAIN_TYPE_CONVERSION[python_type]

        if python_type in CPP_TYPE_CONVERSION:
            return CPP_TYPE_CONVERSION[python_type]
        else:
            return CPP_OTHER_CONVERSION[python_type]

        raise TypeError(
            f"No C++ type mapping for {python_type!r}"
        )

    # SECOND PASS: IR -> C++

    def emit_cpp(self, input_annotations, function_name, args):
        declarations = []
        seen = set()

        # Local variable declarations

        for instruction in self.ir:
            if instruction["type"] != "valuable":
                continue

            variable_name = instruction["name"]

            if variable_name in seen:
                continue

            cpp_type = self.cpp_type(
                instruction["data_type"],
                function_name,
            )

            print(args)

            if not variable_name in args:
                declarations.append(
                    f"{cpp_type} {variable_name};"
                )

            seen.add(variable_name)

        # Function arguments

        arguments = []

        for argument_name, argument_type in list(
            input_annotations.items()
        )[:-1]:
            cpp_type = self.cpp_type(
                argument_type,
                function_name,
            )

            arguments.append(
                f"{cpp_type} {argument_name}"
            )

        arg_formation = ", ".join(arguments)

        # Return type

        return_type = self.cpp_type(
            input_annotations["return"],
            function_name,
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

        # Emit IR

        for instruction in self.ir:
            instruction_type = instruction["type"]

            # Label

            if instruction_type == "label":
                generated_code.append(
                    f"T{function_name}{instruction['name']}:"
                )

            # Return

            elif instruction_type == "return":
                value = instruction["value"]["data"]

                generated_code.append(
                    f"return {value};"
                )

            # Backward/forward jump

            elif instruction_type == "moonwalk":
                generated_code.append(
                    f"goto T{function_name}{instruction['jump']};"
                )

            # Conditional jump

            elif instruction_type == "if":
                expression = instruction["data"]["data"]

                generated_code.append(
                    f"if (!({expression})) {{"
                )

                generated_code.append(
                    f"    goto T{function_name}{instruction['jump']};"
                )

                generated_code.append("}")

            # Variable assignment

            elif instruction_type == "valuable":
                variable_name = instruction["name"]
                value = instruction["data"]

                if instruction["data_type"] == str:
                    value = f'"{value}"'

                generated_code.append(
                    f"{variable_name} = {value};"
                )

            # Function call

            elif instruction_type == "function_call":
                function = instruction["function_to_run"]
                args = instruction["args"]
                result = instruction["result"]

                arg_strings = []

                for argument in args:
                    value = argument["data"]

                    if argument["type"] == str:
                        value = f'"{value}"'

                    arg_strings.append(str(value))

                arguments = ", ".join(arg_strings)

                return_type = self.cpp_type(
                    instruction["return_type"],
                    function_name,
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

    # WRITE OUTPUT

    def compile(self, output_file):
        generated_code = [
            "#include <iostream>",
            "#include <string>",
        ]

        generated_code.extend(PYSTDLIB)

        functions = self.half_pass()

        for function_name, (
            annotations,
            function_code,
        ) in functions.items():

            function_code:types.CodeType

            print(
                f"\n===== COMPILING {function_name} ====="
            )

            # Every function gets completely independent
            # compiler state.
            self.reset_function_state()

            for arg_name, arg_type in list(annotations.items())[:function_code.co_argcount]:
                if arg_name == "return":
                    continue
                self.variable_types[arg_name] = arg_type

            args = list(self.variable_types.keys())

            function_bytecode = script.Script(function_code)
            self.first_pass(function_bytecode, functions)

            function_bytecode = script.Script(
                function_code
            )

            generated_function = self.emit_cpp(
                annotations,
                function_name,
                args
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