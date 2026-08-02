# Hypatia

Hypatia is a low earth orbit (LEO) satellite network simulation framework. It pre-calculates network state over time, enables packet-level simulations using ns-3 and provides visualizations to aid understanding.

<a href="#"><img alt="Kuiper side-view" src="https://raw.githubusercontent.com/leosatsim/leosatsim.github.io/master/images/Kuiper_side_view.png" width="20%" /></a>
<a href="#"><img alt="Telesat top-view" src="https://raw.githubusercontent.com/leosatsim/leosatsim.github.io/master/images/Telesat_top_view.png" width="20%" /></a>
<a href="#"><img alt="starlink_paris_luanda_short" src="https://raw.githubusercontent.com/leosatsim/leosatsim.github.io/master/images/starlink_paris_luanda_short.png" width="10%" /></a>

It consists of four main components:

* `satgenpy` : Python framework to generate LEO satellite networks and generate 
  routing over time over a period of time. It additionally includes several 
  analysis tools to study individual cases. It makes use of several Python modules
  among which: numpy, astropy, ephem, networkx, sgp4, geopy, matplotlib, 
  statsmodels, cartopy (and its dependent (data) packages: libproj-dev, proj-data,
  proj-bin, libgeos-dev), and exputil.
  More information can be found in `satgenpy/README.md`.
  (license: MIT)

* `ns3-sat-sim` : ns-3 based framework which takes as input the state generated 
  by `satgenpy` to perform packet-level simulations over LEO satellite networks.
  It makes use of the [`satellite`](https://gitlab.inesctec.pt/pmms/ns3-satellite)
  ns-3 module by Pedro Silva to calculate satellite locations over time.
  It uses the [`basic-sim`](https://github.com/snkas/basic-sim/tree/3b32597c183e1039be7f0bede17d36d354696776) 
  ns-3 module to make e.g., running end-to-end TCP flows easier, which makes use of several Python
  modules (e.g., numpy, statsmodels, exputil) as well as several other packages (e.g., OpenMPI, lcov, gnuplot).
  More information can be found in `ns3-sat-sim/README.md`.
  (license: GNU GPL version 2)
  
* `satviz` : Cesium visualization pipeline to generate interactive satellite network
  visualizations. It makes use of the online Cesium API by generating CesiumJS code.
  The API calls require its user to obtain a Cesium access token (via [https://cesium.com/]()).
  More information can be found in `satviz/README.md`.
  (license: MIT)

* `paper` : Experimental and plotting code to reproduce the experiments and 
  figures which are presented in the paper.
  It makes use of several Python modules among which: satgenpy, numpy, networkload, and exputil.
  It uses the gnuplot package for most of its plotting.
  More information can be found in `paper/README.md`.
  (license: MIT)
  
(there is a fifth folder called `integration_tests` which is used for integration testing purposes)

This is the code repository introduced and used in "Exploring the “Internet from space” with Hypatia" 
by Simon Kassing*, Debopam Bhattacherjee*, André Baptista Águas, Jens Eirik Saethre and Ankit Singla
(*equal contribution), which is published in the Internet Measurement Conference (IMC) 2020.

BibTeX citation:
```
@inproceedings {hypatia,
    author = {Kassing, Simon and Bhattacherjee, Debopam and Águas, André Baptista and Saethre, Jens Eirik and Singla, Ankit},
    title = {{Exploring the “Internet from space” with Hypatia}},
    booktitle = {{ACM IMC}},
    year = {2020}
}
```

## Getting started

1. System setup:
   - Python version 3.7+
   - Recent Linux operating system (e.g., Ubuntu 18+)

2. Install dependencies:
   ```
   bash hypatia_install_dependencies.sh
   ```
   
3. Build all four modules (as far as possible):
   ```
   bash hypatia_build.sh
   ```
   
4. Run tests:
   ```
   bash hypatia_run_tests.sh
   ```

5. The reproduction of the paper is essentially the tutorial for Hypatia.
   Please navigate to `paper/README.md`.

### Build workarounds for modern Fedora / RHEL

The steps above assume an Ubuntu-like environment. On a fresh Fedora / RHEL box (or any system with a recent toolchain), a few extra manual steps are required to get the framework to build cleanly. The following captures the full set of workarounds that were deployed together.

#### 1. Install system and Python dependencies

The system `pip` on Fedora is PEP 668-managed, so Python packages must be installed into the user site:

```bash
sudo dnf update -y
sudo dnf install -y gcc gcc-c++ make cmake ninja-build git python3 python3-devel \
    openmpi openmpi-devel gnuplot lcov patch proj-devel geos-devel environment-modules
pip3 install --user numpy astropy ephem networkx sgp4 geopy matplotlib \
    statsmodels cartopy
```

Fedora ships OpenMPI behind an environment module. Load it so that `mpic++` is on the path before `./waf` runs:

```bash
source /etc/profile.d/modules.sh
module load mpi/openmpi-x86_64
```

*Tip: add those two lines to your `~/.bashrc` so they persist across terminal sessions.*

#### 2. Fix git submodule cloning errors (`curl 92` / `early EOF`)

Hypatia pulls the `basic-sim` module as a git submodule. Flaky connections can drop the HTTP/2 stream mid-clone. Force HTTP/1.1 and raise the POST buffer:

```bash
git config --global http.version HTTP/1.1
git config --global http.postBuffer 524288000
git submodule update --init --recursive
```

#### 3. Bypass C++20 strict syntax errors

Modern GCC enforces C++20 strictly, which breaks the legacy ns-3 code in Hypatia with `template-id not allowed for constructor in C++20` (most visibly in `simulation-singleton.h`). Because ns-3 promotes warnings to errors (`-Werror`), the build halts.

The cleanest bypass is to export compiler flags that force C++17 and disable `-Werror` before invoking the build script:

```bash
# 1. Clear any broken Waf cache first
cd ns3-sat-sim/simulator
rm -rf build/
rm -f .lock-waf*
cd ../../

# 2. Export global GCC overrides
export CXXFLAGS="-std=c++17 -Wno-error"

# 3. Build the framework
bash hypatia_build.sh
```

#### 4. Generate the Starlink network state

After the build succeeds, pre-calculate the Starlink constellation state (via `satgenpy`) before running any packet-level simulation. To generate the Starlink-550 shell with the +Grid ISL topology (Scenario ID `6`):

```bash
cd paper/satellite_networks_state
bash generate_for_paper.sh 6 4
```

Adjust the second argument to match your CPU thread count (e.g., `4` for a Core i3). The output is written to `satgenpy/gen_data/`, which the `ns3-sat-sim` pipeline then consumes.

### Visualizations
Most of the visualizations in the paper are available [here](https://leosatsim.github.io/).
All of the visualizations can be regenerated using scripts available in `satviz` as discussed above.

Below are some examples of visualizations:

- SpaceX Starlink 5-shell side-view (left) and top-view (right). To know the configuration of the shells, click [here](https://leosatsim.github.io/).

  <a href="#"><img alt="Starlink side-view" src="https://raw.githubusercontent.com/leosatsim/leosatsim.github.io/master/images/Starlink_side_view.png" width="45%" /></a>
  <a href="#"><img alt="Starlink top-view" src="https://raw.githubusercontent.com/leosatsim/leosatsim.github.io/master/images/Starlink_top_view.png" width="45%" /></a>

- Amazon Kuiper 3-shell side-view (left) and top-view (right). To know the configuration of the shells, click [here](https://leosatsim.github.io/kuiper.html).

  <a href="#"><img alt="Kuiper side-view" src="https://raw.githubusercontent.com/leosatsim/leosatsim.github.io/master/images/Kuiper_side_view.png" width="45%" /></a>
  <a href="#"><img alt="Kuiper top-view" src="https://raw.githubusercontent.com/leosatsim/leosatsim.github.io/master/images/Kuiper_top_view.png" width="45%" /></a>

- RTT changes over time between Paris and Luanda over Starlink 1st shell. Left: 117 ms, Right: 85 ms. Click on the images for 3D interactive visualizations.

  <a href="https://leosatsim.github.io/starlink_550_path_Paris_1608_Luanda_1650_46800.html"><img alt="starlink_paris_luanda_long" src="https://raw.githubusercontent.com/leosatsim/leosatsim.github.io/master/images/starlink_paris_luanda_long.png" width="35%" /></a>
  <a href="https://leosatsim.github.io/starlink_550_path_Paris_1608_Luanda_1650_139900.html"><img alt="starlink_paris_luanda_short" src="https://raw.githubusercontent.com/leosatsim/leosatsim.github.io/master/images/starlink_paris_luanda_short.png" width="35%" /></a>

- Link utilizations change over time, even with the input traffic being static. For Kuiper 1st shell, path between Chicago and Zhengzhou at 10s (top) and 150s (bottom). Click on the images for 3D interactive visualizations.

  <a href="https://leosatsim.github.io/kuiper_630_path_wise_util_Chicago_1193_Zhengzhou_1243_10000.html"><img alt="kuiper_Chicago_Zhengzhou_10s" src="https://raw.githubusercontent.com/leosatsim/leosatsim.github.io/master/images/kuiper_Chicago_Zhengzhou_10s.png" width="90%" /></a>
  <a href="https://leosatsim.github.io/kuiper_630_path_wise_util_Chicago_1193_Zhengzhou_1243_150000.html"><img alt="kuiper_Chicago_Zhengzhou_150s" src="https://raw.githubusercontent.com/leosatsim/leosatsim.github.io/master/images/kuiper_Chicago_Zhengzhou_150s.png" width="90%" /></a>
