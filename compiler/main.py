# main.py
import argparse
import subprocess
import sys
from compiler import Compiler


def main():
    parser = argparse.ArgumentParser(
        prog="py2cpp",
        description="Compile Python to C++",
    )
    
    parser.add_argument(
        "input",
        help="Python file to compile",
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output C++ file (default: input name with .cpp)",
    )
    
    parser.add_argument(
        "-r", "--run",
        action="store_true",
        help="Compile and run the generated C++",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print IR and bytecode during compilation",
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="py2cpp 0.1.0",
    )
    
    args = parser.parse_args()
    
    # Default output name
    if args.output:
        output = args.output
    else:
        output = args.input.replace(".py", ".cpp")
    
    # Compile
    try:
        compiler = Compiler(args.input)
        compiler.compile(output)
    except FileNotFoundError:
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Compiled {args.input} -> {output}")
    
    # Run if requested
    if args.run:
        try:
            subprocess.run(["g++", output, "-o", "output"], check=True)
            subprocess.run(["./output"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error: compilation failed", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print("Error: g++ not found. Is it installed?", file=sys.stderr)
            sys.exit(1)

    subprocess.run(shell=True, args=f"g++ {output} -o {output.replace(".c++", ".exe")} -O2")
    #subprocess.run(shell=True, args=f"del {output}")


if __name__ == "__main__":
    main()