NS3_VERSION="ns-3.31"

# Usage help
if [ "$1" == "--help" ]; then
  echo "Usage: bash build.sh [--help, --debug_all, --debug_minimal, --optimized, --optimized_with_tests]"
  exit 0
fi

# Extract copy of ns-3
echo "Unzipping clean ns-3 (no overwrites)"
unzip ${NS3_VERSION}.zip || exit 1
cp -r ${NS3_VERSION}/* simulator/ || exit 1
rm -r ${NS3_VERSION} || exit 1

# Patch waf-tools files that break on Python >= 3.13 (pipes module removed).
# These edits get clobbered each time ns-3 is unzipped above, so they must
# be re-applied here.
python3 - <<'PY' || exit 1
import pathlib
p = pathlib.Path("simulator/waf-tools/clang_compilation_database.py")
s = p.read_text()
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
if import_old in s:
    s = s.replace(import_old, import_new)
    changed = True
if quote_old in s:
    s = s.replace(quote_old, quote_new)
    changed = True
if changed:
    p.write_text(s)
    print(f"patched: {p}")
else:
    print(f"already patched or unexpected content: {p}")
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
  # Default is debug_all
  ./waf configure --build-profile=debug --enable-mpi --enable-examples --enable-tests --enable-gcov --out=build/debug_all || exit 1

else
  echo "Invalid build option: $1"
  echo "Usage: bash build.sh [--debug_all, --debug_minimal, --optimized, --optimized_with_tests]"
  exit 1
fi

# Perform the build
./waf -j4 || exit 1
