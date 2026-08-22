# MIT License
#
# Copyright (c) 2020 Debopam Bhattacherjee
# Modifications: time-varying rendering + fstate route overlay
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
WHAT CHANGED VS THE ORIGINAL SCRIPT
====================================
1. THE ACTUAL BUG FIX (this is the whole reason the constellation looked frozen):

     Original:
         sat_objs[j]["sat_obj"].compute(EPOCH)

     EPOCH ("2000-01-01 00:00:00") is the orbital-ELEMENT epoch used when the
     satellite objects were constructed by util.generate_sat_obj_list(...) --
     that part is correct and unchanged below. But .compute(...) is a
     *separate* call that tells pyephem which OBSERVATION TIME to compute the
     satellite's position at. Passing EPOCH there too means every render
     freezes the constellation at t=0, no matter what "time" you thought you
     were visualizing. Fixed by computing a `render_time` = EPOCH + elapsed
     seconds, and calling .compute(render_time) instead.

2. Optional route overlay: replays fstate diff files up to the requested
   elapsed time (same cumulative-replay pattern as satgen's
   print_routes_and_rtt.py) and draws the resulting src->dst path as a
   highlighted polyline, so the picture matches what you already verified
   numerically in networkx_path_*.txt.

3. Output filename now encodes elapsed_time_s, so you can render one HTML per
   timestamp (e.g. each row of your networkx_path_1584_to_1585.txt) and click
   through them like a flipbook -- a lightweight stand-in for true CZML
   animation, which would require pulling in poliastro's CZMLExtractor (the
   import at the top of the original file was already commented out, meaning
   it wasn't wired up / available in your environment). Given your defense
   timeline, this gets you a time-correct, defensible visualization without a
   new dependency to debug. If you want continuous CZML animation instead of
   discrete snapshots afterwards, say so and I'll build that separately.

USAGE
=====
    python visualize_constellation_patched.py <elapsed_time_s> [options]

    # Single snapshot at t=304.9s, no route overlay
    python visualize_constellation_patched.py 304.9

    # Snapshot at t=304.9s with the 1584->1585 route highlighted
    python visualize_constellation_patched.py 304.9 \\
        --dynamic-state-dir ../satellite_networks_state/gen_data/starlink_550_isls_plus_grid_ground_stations_top_100_algorithm_free_one_only_over_isls/dynamic_state_50ms_for_600s \\
        --ground-stations-file ../satellite_networks_state/gen_data/starlink_550_isls_plus_grid_ground_stations_top_100_algorithm_free_one_only_over_isls/ground_stations.txt \\
        --route-src 1584 --route-dst 1585

    # One snapshot per row of your existing networkx_path file (flipbook mode)
    python visualize_constellation_patched.py --from-path-file /path/to/networkx_path_1584_to_1585.txt \\
        --dynamic-state-dir ... --ground-stations-file ... --route-src 1584 --route-dst 1585

Adjust NUM_SATS_PER_ORB / etc. below to match your actual constellation
config if you've changed it from the default Starlink-550 5-shell block
(same as your original file).
"""

import argparse
import math
import os

try:
    from . import util
except (ImportError, SystemError):
    import util

import ephem

# ----------------------------------------------------------------------------
# CONSTELLATION GENERATION GENERAL CONSTANTS (unchanged from your original)
# ----------------------------------------------------------------------------

EARTH_RADIUS = 6378135.0  # WGS72

ECCENTRICITY = 0.0000001
ARG_OF_PERIGEE_DEGREE = 0.0
PHASE_DIFF = True
EPOCH = "2000-01-01 00:00:00"  # orbital ELEMENT epoch -- do not repurpose this as render time

COLOR = ['CRIMSON', 'FORESTGREEN', 'DODGERBLUE', 'PERU', 'BLUEVIOLET', 'DARKMAGENTA']
ROUTE_COLOR = 'GOLD'

NAME = "Starlink"
SHELL_CNTR = 1

MEAN_MOTION_REV_PER_DAY = [None] * SHELL_CNTR
ALTITUDE_M = [None] * SHELL_CNTR
NUM_ORBS = [None] * SHELL_CNTR
NUM_SATS_PER_ORB = [None] * SHELL_CNTR
INCLINATION_DEGREE = [None] * SHELL_CNTR
BASE_ID = [None] * SHELL_CNTR
ORB_WISE_IDS = [None] * SHELL_CNTR

MEAN_MOTION_REV_PER_DAY[0] = 15.19
ALTITUDE_M[0] = 550000
NUM_ORBS[0] = 72
NUM_SATS_PER_ORB[0] = 22
INCLINATION_DEGREE[0] = 53
BASE_ID[0] = 0
ORB_WISE_IDS[0] = []

# MEAN_MOTION_REV_PER_DAY[1] = 13.4
# ALTITUDE_M[1] = 1110000
# NUM_ORBS[1] = 32
# NUM_SATS_PER_ORB[1] = 50
# INCLINATION_DEGREE[1] = 53.8
# BASE_ID[1] = 1584
# ORB_WISE_IDS[1] = []

# MEAN_MOTION_REV_PER_DAY[2] = 13.35
# ALTITUDE_M[2] = 1130000
# NUM_ORBS[2] = 8
# NUM_SATS_PER_ORB[2] = 50
# INCLINATION_DEGREE[2] = 74
# BASE_ID[2] = 3184
# ORB_WISE_IDS[2] = []

# MEAN_MOTION_REV_PER_DAY[3] = 12.97
# ALTITUDE_M[3] = 1275000
# NUM_ORBS[3] = 5
# NUM_SATS_PER_ORB[3] = 75
# INCLINATION_DEGREE[3] = 81
# BASE_ID[3] = 3584
# ORB_WISE_IDS[3] = []

# MEAN_MOTION_REV_PER_DAY[4] = 12.84
# ALTITUDE_M[4] = 1325000
# NUM_ORBS[4] = 6
# NUM_SATS_PER_ORB[4] = 75
# INCLINATION_DEGREE[4] = 70
# BASE_ID[4] = 3959
# ORB_WISE_IDS[4] = []

TOTAL_SATELLITES = 1584  # shell 0 only, matching your fstate node numbering (GS ids start at 1584)

topFile = "../static_html/top.html"
bottomFile = "../static_html/bottom.html"
OUT_DIR = "../viz_output/"


# ----------------------------------------------------------------------------
# Route replay (mirrors satgen.post_analysis.print_routes_and_rtt's cumulative
# diff-replay -- see the earlier discussion of why fstate files are diffs,
# not full snapshots)
# ----------------------------------------------------------------------------

def build_fstate_at(dynamic_state_dir, update_interval_ns, elapsed_time_ns):
    """Replay fstate_*.txt diffs from t=0 up to (and including) elapsed_time_ns.
    Returns dict[(current, destination)] -> next_hop_node_id."""
    fstate = {}
    t = 0
    while t <= elapsed_time_ns:
        fpath = os.path.join(dynamic_state_dir, "fstate_%d.txt" % t)
        if not os.path.isfile(fpath):
            break
        with open(fpath, "r") as f_in:
            for line in f_in:
                line = line.strip()
                if not line:
                    continue
                spl = line.split(",")
                current, destination, next_hop = int(spl[0]), int(spl[1]), int(spl[2])
                fstate[(current, destination)] = next_hop
        t += update_interval_ns
    return fstate


def walk_path(fstate, src, dst, max_hops=1000):
    """Follow next-hop entries from src toward dst. Returns list of node ids,
    or None if unreachable / no data for this pair yet."""
    path = [src]
    current = src
    for _ in range(max_hops):
        if current == dst:
            return path
        next_hop = fstate.get((current, dst), -1)
        if next_hop == -1:
            return None
        path.append(next_hop)
        current = next_hop
    return None  # loop guard tripped -- shouldn't happen with correct fstate


def read_ground_stations(gs_file, num_satellites):
    """Parser for Hypatia's ground_stations.txt / the raw top-100-cities input file.
    Expected columns (comma-separated): gid,name,latitude,longitude,elevation,...
    (confirmed against ground_stations_cities_sorted_by_estimated_2025_pop_top_100.basic.txt)

    IMPORTANT: fstate files address ground stations as (num_satellites + gid), not
    the raw gid -- e.g. gid=0 (Tokyo) is graph node 1584, gid=1 (Delhi) is node 1585.
    Returns dict[num_satellites + gid] -> (lat_deg, lon_deg, elevation_m), keyed to
    match fstate node ids directly."""
    gs = {}
    with open(gs_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            spl = line.split(",")
            gid = int(spl[0])
            lat = float(spl[2])
            lon = float(spl[3])
            elevation = float(spl[4]) if len(spl) > 4 else 0.0
            gs[num_satellites + gid] = (lat, lon, elevation)
    return gs


# ----------------------------------------------------------------------------
# Main rendering
# ----------------------------------------------------------------------------

def generate_satellite_trajectories(elapsed_time_s, route_path=None, gs_coords=None):
    """
    Generates satellite + ISL visualization, computed at the REQUESTED time
    (EPOCH + elapsed_time_s), not frozen at EPOCH.

    Two independent pieces of state are combined here:
      - PHYSICAL state: satellite positions at simulation time t, from pyephem.
      - ROUTING state: forwarding path at time t, reconstructed by the caller
        via cumulative fstate-diff replay (build_fstate_at / walk_path) and
        passed in as `route_path`.
    They're computed separately and only meet here at render time.
    """
    # This is the actual fix: advance the observation time pyephem computes at.
    render_time = ephem.Date(ephem.Date(EPOCH) + elapsed_time_s * ephem.second)

    viz_string = ""
    sat_id_to_latlonalt = {}  # for route overlay lookups

    for i in range(0, SHELL_CNTR):
        sat_objs = util.generate_sat_obj_list(
            NUM_ORBS[i],
            NUM_SATS_PER_ORB[i],
            EPOCH,  # element epoch -- unchanged, this is correct as-is
            PHASE_DIFF,
            INCLINATION_DEGREE[i],
            ECCENTRICITY,
            ARG_OF_PERIGEE_DEGREE,
            MEAN_MOTION_REV_PER_DAY[i],
            ALTITUDE_M[i]
        )
        for j in range(len(sat_objs)):
            sat_objs[j]["sat_obj"].compute(render_time)  # <-- was .compute(EPOCH)

            global_id = BASE_ID[i] + j
            lat_deg = math.degrees(sat_objs[j]["sat_obj"].sublat)
            lon_deg = math.degrees(sat_objs[j]["sat_obj"].sublong)
            alt_m = sat_objs[j]["alt_km"] * 1000
            sat_id_to_latlonalt[global_id] = (lat_deg, lon_deg, alt_m)

            viz_string += "var redSphere = viewer.entities.add({name : '', position: Cesium.Cartesian3.fromDegrees(" \
                          + str(lon_deg) + ", " + str(lat_deg) + ", " + str(alt_m) + "), " \
                          + "ellipsoid : {radii : new Cesium.Cartesian3(30000.0, 30000.0, 30000.0), " \
                          + "material : Cesium.Color.BLACK.withAlpha(1),}});\n"

        orbit_links = util.find_orbit_links(sat_objs, NUM_ORBS[i], NUM_SATS_PER_ORB[i])
        for key in orbit_links:
            sat1 = orbit_links[key]["sat1"]
            sat2 = orbit_links[key]["sat2"]
            viz_string += "viewer.entities.add({name : '', polyline: { positions: Cesium.Cartesian3.fromDegreesArrayHeights([" \
                          + str(math.degrees(sat_objs[sat1]["sat_obj"].sublong)) + "," \
                          + str(math.degrees(sat_objs[sat1]["sat_obj"].sublat)) + "," \
                          + str(sat_objs[sat1]["alt_km"] * 1000) + "," \
                          + str(math.degrees(sat_objs[sat2]["sat_obj"].sublong)) + "," \
                          + str(math.degrees(sat_objs[sat2]["sat_obj"].sublat)) + "," \
                          + str(sat_objs[sat2]["alt_km"] * 1000) + "]), " \
                          + "width: 0.5, arcType: Cesium.ArcType.NONE, " \
                          + "material: new Cesium.PolylineOutlineMaterialProperty({ " \
                          + "color: Cesium.Color." + COLOR[i] + ".withAlpha(0.4), outlineWidth: 0, outlineColor: Cesium.Color.BLACK})}});"

    # Ground station markers -- distinct from satellite spheres so it's clear
    # in the render which points are fixed cities vs moving satellites.
    # NOTE: uses a flat billboard-style point (not an extruded 3D shape like a
    # cylinder or box) specifically because any object with real height gets
    # visually displaced from its true ground coordinate under perspective
    # projection at anything other than a straight-overhead camera angle --
    # a tall marker's silhouette leans away from its base the same way a real
    # building does in an oblique photo. A flat point always renders exactly
    # at its lat/lon regardless of viewing angle.
    if gs_coords:
        route_endpoints = set()
        if route_path:
            route_endpoints = {route_path[0], route_path[-1]}
        for node_id, (lat_deg, lon_deg, alt_m) in gs_coords.items():
            is_endpoint = node_id in route_endpoints
            color = "ORANGE" if is_endpoint else "SLATEGRAY"
            pixel_size = "14" if is_endpoint else "6"
            viz_string += "viewer.entities.add({name : 'gs_%d', position: Cesium.Cartesian3.fromDegrees(" % node_id \
                          + str(lon_deg) + ", " + str(lat_deg) + ", " + str(alt_m) + "), " \
                          + "point : {pixelSize: %s, color: Cesium.Color.%s, outlineColor: Cesium.Color.BLACK, outlineWidth: 2, disableDepthTestDistance: 0}});\n" % (pixel_size, color)

    # Route overlay: draw the actual forwarding path as a highlighted line
    if route_path:
        coords_flat = []
        for node_id in route_path:
            if node_id in sat_id_to_latlonalt:
                lat_deg, lon_deg, alt_m = sat_id_to_latlonalt[node_id]
            elif gs_coords and node_id in gs_coords:
                lat_deg, lon_deg, alt_m = gs_coords[node_id]
            else:
                continue  # node outside this shell / unknown -- skip rather than crash the render
            coords_flat += [str(lon_deg), str(lat_deg), str(alt_m)]

        if len(coords_flat) >= 6:  # need at least 2 points
            viz_string += "viewer.entities.add({name : 'route', polyline: { positions: Cesium.Cartesian3.fromDegreesArrayHeights([" \
                          + ",".join(coords_flat) + "]), " \
                          + "width: 4, arcType: Cesium.ArcType.GEODESIC, clampToGround: false, " \
                          + "disableDepthTestDistance: 0, " \
                          + "material: new Cesium.PolylineOutlineMaterialProperty({ " \
                          + "color: Cesium.Color." + ROUTE_COLOR + ".withAlpha(0.95), outlineWidth: 1, outlineColor: Cesium.Color.BLACK})}});\n"

    return viz_string


def write_viz_files(viz_string, out_html_file):
    with open(out_html_file, 'w') as writer_html:
        with open(topFile, 'r') as fi:
            writer_html.write(fi.read())
        writer_html.write(viz_string)
        with open(bottomFile, 'r') as fb:
            writer_html.write(fb.read())


# def render_one(elapsed_time_s, args):
#     route_path = None
#     gs_coords = None

#     if args.route_src is not None and args.route_dst is not None:
#         if not args.dynamic_state_dir:
#             raise ValueError("--route-src/--route-dst requires --dynamic-state-dir")
#         elapsed_time_ns = int(round(elapsed_time_s * 1e9))
#         fstate = build_fstate_at(args.dynamic_state_dir, args.update_interval_ms * 1000 * 1000, elapsed_time_ns)
#         route_path = walk_path(fstate, args.route_src, args.route_dst)
#         if route_path is None:
#             print("  [warn] no path found for %d -> %d at t=%.3fs (unreachable, or fstate not yet loaded for this t)"
#                   % (args.route_src, args.route_dst, elapsed_time_s))
#         if args.ground_stations_file:
#             gs_coords = read_ground_stations(args.ground_stations_file, TOTAL_SATELLITES)

#     viz_string = generate_satellite_trajectories(elapsed_time_s, route_path, gs_coords)
#     out_html_file = os.path.join(OUT_DIR, "%s_t%d.html" % (NAME, int(round(elapsed_time_s * 1000))))
#     os.makedirs(OUT_DIR, exist_ok=True)
#     write_viz_files(viz_string, out_html_file)
#     print("Wrote: %s%s" % (out_html_file, "  (route: %s)" % "-".join(map(str, route_path)) if route_path else ""))

def render_one(elapsed_time_s, args):
    route_path = None
    gs_coords = None

    if args.ground_stations_file:
        gs_coords = read_ground_stations(
            args.ground_stations_file,
            TOTAL_SATELLITES
        )
    route_path = [
        1584,
        1586,
        839,
        817,
        795,
        773,
        751,
        729,
        707,
        706,
        1585
    ]

    viz_string = generate_satellite_trajectories(
        elapsed_time_s,
        route_path,
        gs_coords
    )

    out_html_file = os.path.join(
        OUT_DIR,
        "%s_t%d.html" % (NAME, int(round(elapsed_time_s * 1000)))
    )

    os.makedirs(OUT_DIR, exist_ok=True)
    write_viz_files(viz_string, out_html_file)

    print(
        "Wrote: %s  (fake route: %s)"
        % (out_html_file, "-".join(map(str, route_path)))
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("elapsed_time_s", type=float, nargs="?", default=None,
                        help="Seconds since EPOCH to render the constellation at")
    parser.add_argument("--from-path-file", type=str, default=None,
                        help="Render one snapshot per timestamp found in a networkx_path_*.txt file "
                             "(first column of each line is time in ns)")
    parser.add_argument("--dynamic-state-dir", type=str, default=None,
                        help="Path to dynamic_state_<ms>ms_for_<s>s directory (for route overlay)")
    parser.add_argument("--update-interval-ms", type=int, default=50)
    parser.add_argument("--ground-stations-file", type=str, default=None)
    parser.add_argument("--route-src", type=int, default=None)
    parser.add_argument("--route-dst", type=int, default=None)
    args = parser.parse_args()

    if args.from_path_file:
        times_ns = []
        with open(args.from_path_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                times_ns.append(int(line.split(",")[0]))
        for t_ns in times_ns:
            render_one(t_ns / 1e9, args)
    elif args.elapsed_time_s is not None:
        render_one(args.elapsed_time_s, args)
    else:
        parser.error("Provide elapsed_time_s or --from-path-file")


if __name__ == "__main__":
    main()