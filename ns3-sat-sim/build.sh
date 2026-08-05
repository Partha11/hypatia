NS3_VERSION="ns-3.31"

if [ "$1" == "--help" ]; then
  echo "Usage: bash build.sh [--help, --debug_all, --debug_minimal, --optimized, --optimized_with_tests]"
  exit 0
fi

# Extract copy of ns-3
echo "Unzipping clean ns-3 (no overwrites)"
unzip ${NS3_VERSION}.zip || exit 1
cp -r ${NS3_VERSION}/* simulator/ || exit 1
rm -r ${NS3_VERSION} || exit 1

cd simulator || exit 1
./waf --help >/dev/null 2>&1 || true
cd .. || exit 1

# Patch waf-tools files that break on Python >= 3.13
# Also patch the extracted waflib/Context.py for Python >= 3.12
python3 - <<'PY' || exit 1
import pathlib
import glob

# 1. Patch clang_compilation_database.py
p1 = pathlib.Path("simulator/waf-tools/clang_compilation_database.py")
if p1.exists():
    s1 = p1.read_text()
    import_old = "import sys, os, json, shlex, pipes\n"
    import_new = "import sys, os, json, shlex\n"
    quote_old = (
        "if sys.hexversion >= 0x3030000:\n"
        "\tquote = shlex.quote\n"
        "else:\n"
        "\tquote = pipes.quote\n"
    )
    quote_new = "quote = shlex.quote\n"
    changed = False
    if import_old in s1:
        s1 = s1.replace(import_old, import_new)
        changed = True
    if quote_old in s1:
        s1 = s1.replace(quote_old, quote_new)
        changed = True
    if changed:
        p1.write_text(s1)
        print(f"patched: {p1}")
    else:
        print(f"already patched or unexpected content: {p1}")

# 2. Patch waflib/Context.py for Python 3.12+ compatibility
waf_dirs = glob.glob("simulator/.waf3-*")
if waf_dirs:
    waf_dir = pathlib.Path(waf_dirs[0])
    p2 = waf_dir / "waflib" / "Context.py"
    if p2.exists():
        s2 = p2.read_text()
        
        # Replace the import
        imp_old = "import os,re,imp,sys"
        imp_new = "import os,re,sys,types"
        
        # Replace the function call
        new_module_old = "imp.new_module(WSCRIPT_FILE)"
        new_module_new = "types.ModuleType(WSCRIPT_FILE)"
        
        changed = False
        if imp_old in s2:
            s2 = s2.replace(imp_old, imp_new)
            changed = True
        if new_module_old in s2:
            s2 = s2.replace(new_module_old, new_module_new)
            changed = True
            
        if changed:
            p2.write_text(s2)
            print(f"patched: {p2}")
        else:
            print(f"already patched or unexpected content: {p2}")
PY

cd simulator || exit 1

# Update the basic-sim module
echo "Updating git submodules"
git submodule update || exit 1

# Configure the build
if [ "$1" == "--debug_all" ]; then
  ./waf configure --build-profile=debug --enable-mpi --enable-examples --enable-tests --enable-gcov --out=build/debug_all || exit 1

elif [ "$1" == "--debug_minimal" ]; then
  ./waf configure --build-profile=debug --enable-mpi --out=build/debug_minimal || exit 1

elif [ "$1" == "--optimized" ]; then
  ./waf configure --build-profile=optimized --enable-mpi --out=build/optimized || exit 1

elif [ "$1" == "--optimized_with_tests" ]; then
  ./waf configure --build-profile=optimized --enable-mpi --enable-tests --out=build/optimized_with_tests || exit 1

elif [ "$1" == "" ]; then
  ./waf configure --build-profile=debug --enable-mpi --enable-examples --enable-tests --enable-gcov --out=build/debug_all || exit 1

else
  echo "Invalid build option: $1"
  echo "Usage: bash build.sh [--debug_all, --debug_minimal, --optimized, --optimized_with_tests]"
  exit 1
fi

# Perform the build
./waf -j4 || exit 1