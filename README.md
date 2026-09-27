# Py2Cpp

A compiler that translates a subset of Python to C++.

## Features

- **Types**: `int`, `float`, `str`, `bool`
- **Math**: `+`, `-`, `*`, `/`
- **Control flow**: `if`/`else`, `while`
- **Functions**: with type annotations, return values
- **`main()`**: maps to C++ `main` with `argc`/`argv`
- **Built-ins** like **print()**

## How it works

1. It takes the Python src and translates it into Python bytecode using dis
2. It converts it to a IR for it to be more cleaner(is that a word, probably)
3. And finally it translates to C++ and compiles using g++(you will need this in your path to work)

## Now i will stop yapping and show how to use it

```bash
python main.py tests/test_code.py -o tests/main.c++
g++ tests/main.c++ -o a.exe
./a.exe
```

yep, thats it :3