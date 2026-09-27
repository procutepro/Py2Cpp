import dis

class Script:
    def __init__(self, file_path):
        self.bytecode_instructions:list[dis.Instruction] = []
        if type(file_path) == str:
            with open(file_path) as f:
                src = f.read()
            self.bytecode_instructions = list(dis.  get_instructions(src))
        else:
            self.bytecode_instructions = list(dis.  get_instructions(file_path))
        
        self.offsets = self.build_offset_map()
        self.convert_to_better_instr()
        self.smth = 0

    def build_offset_map(self):
        return {instr.offset: idx for idx, instr in enumerate(self.bytecode_instructions)}

    def __getitem__(self, key):
        instr:dis.Instruction = self.bytecode_instructions[key]
        return {
            "program_count": self.offsets[instr.offset],
            "opname": instr.opname,
            "arg": instr.argval,
        }

    def __iter__(self):
        self.smth = 0
        return self

    def __next__(self):
        if self.smth >= len(self.better_instructions):
            raise StopIteration
        value = self.better_instructions[self.smth]
        self.smth += 1
        print("heuys")
        return value

    def convert_to_better_instr(self):
        self.better_instructions = {}
        for instr in self.bytecode_instructions:
            thing = {
                "opname": instr.opname,
                "arg": instr.argval,
                "is_jump_instruction": instr.is_jump_target,
                "offset": instr.offset
            }
            self.better_instructions[self.offsets[instr.offset]] = thing

        return self.better_instructions