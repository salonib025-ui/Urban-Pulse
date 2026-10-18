"""
UrbanPulse Interactive Route Optimizer
Run from the UrbanPulse project root:
    python src/route_optimizer.py

Install dependencies:
    python -m pip install flask osmnx networkx pandas scikit-learn
"""
from __future__ import annotations

import json
import os
import threading
import webbrowser
from pathlib import Path

import flask
from flask import Flask, jsonify, request
import networkx as nx
import osmnx as ox
import pandas as pd

APP_TITLE = "UrbanPulse | Interactive Route Optimizer"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"
GRAPH_PATH = OUTPUT_DIR / "minneapolis_drive.graphml"
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "metro_traffic_cleaned.csv"
HOST = "127.0.0.1"
PORT = int(os.environ.get("URBANPULSE_PORT", "5000"))

# Modeling assumptions (state these in your project report)
SIGNAL_PENALTY_S = 20          # assumed delay per traffic signal, in seconds
MAX_PEAK_SLOWDOWN = 0.5        # major roads up to +50% travel time at the busiest hour
SIDE_STREET_FACTOR = 0.4       # side streets slow down 40% as much as major roads
MAJOR_ROADS = ("motorway", "trunk", "primary", "secondary")

app = Flask(__name__)
_graph: nx.MultiDiGraph | None = None
_graph_lock = threading.Lock()
_hour_load: dict | None = None
_signal_nodes: set | None = None

DEFAULT_ORIGIN = {"name": "Minneapolis City Hall", "lat": 44.9778, "lon": -93.2650}
DEFAULT_DESTINATION = {"name": "Walker Art Center", "lat": 44.9672, "lon": -93.2887}


# --------------------------------------------------------------------------
# Graph loading
# --------------------------------------------------------------------------
def _ensure_travel_times(graph):
    """Add speed and travel-time attributes if missing."""
    try:
        graph = ox.routing.add_edge_speeds(graph)
        graph = ox.routing.add_edge_travel_times(graph)
    except Exception:
        for _, _, _, data in graph.edges(keys=True, data=True):
            length = float(data.get("length", 1.0) or 1.0)
            speed = float(data.get("speed_kph", 30.0) or 30.0)
            data.setdefault("travel_time", length / max(speed / 3.6, 0.1))
            data.setdefault("length", length)
    return graph


def get_graph():
    """Load the cached road graph, or download Minneapolis driving roads."""
    global _graph
    if _graph is not None:
        return _graph
    with _graph_lock:
        if _graph is not None:
            return _graph
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if GRAPH_PATH.exists():
            print(f"Loading cached road network: {GRAPH_PATH}")
            graph = ox.load_graphml(GRAPH_PATH)
        else:
            print("Downloading Minneapolis driving network from OpenStreetMap...")
            print("The first download may take a few minutes.")
            graph = ox.graph_from_place(
                "Minneapolis, Minnesota, USA", network_type="drive", simplify=True
            )
            ox.save_graphml(graph, GRAPH_PATH)
            print(f"Cached road network at: {GRAPH_PATH}")
        _graph = _ensure_travel_times(graph)
        print(f"Road network ready: {len(_graph.nodes):,} nodes, {len(_graph.edges):,} edges")
        return _graph


def nearest_node(lat, lon):
    return ox.distance.nearest_nodes(get_graph(), X=lon, Y=lat)


# --------------------------------------------------------------------------
# Custom-priority routing helpers
# --------------------------------------------------------------------------
def get_hour_load():
    """Relative traffic load by hour (0..1), learned from the historical dataset."""
    global _hour_load
    if _hour_load is not None:
        return _hour_load
    load = {h: 0.0 for h in range(24)}
    try:
        df = pd.read_csv(DATA_PATH)
        tcol = next(c for c in df.columns if c.lower().replace(" ", "_") == "traffic_volume")
        dcol = next(c for c in df.columns if c.lower() in ("date_time", "datetime", "date"))
        df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
        by_hour = df.groupby(df[dcol].dt.hour)[tcol].mean()
        for h, v in by_hour.items():
            load[int(h)] = float(v / by_hour.max())
        print("Hourly traffic profile loaded from historical data.")
    except Exception as exc:
        print(f"Hourly traffic profile unavailable ({exc}); using free-flow times.")
    _hour_load = load
    return load


def get_slowdown(hour):
    """Travel-time multiplier for major roads at a given hour (modeled estimate)."""
    try:
        hour = int(hour)
    except (TypeError, ValueError):
        return 1.0
    if hour < 0 or hour > 23:
        return 1.0
    return 1.0 + MAX_PEAK_SLOWDOWN * get_hour_load().get(hour, 0.0)


def get_signal_nodes():
    """Nodes tagged as traffic signals in OpenStreetMap."""
    global _signal_nodes
    if _signal_nodes is None:
        _signal_nodes = {
            n for n, d in get_graph().nodes(data=True)
            if "traffic_signals" in str(d.get("highway", ""))
        }
        print(f"Traffic signals found in graph: {len(_signal_nodes):,}")
    return _signal_nodes


def _edge_time(attrs, slowdown):
    t = float(attrs.get("travel_time", 0) or 0)
    if any(m in str(attrs.get("highway", "")) for m in MAJOR_ROADS):
        return t * slowdown
    return t * (1 + (slowdown - 1) * SIDE_STREET_FACTOR)


def make_cost(w_time, w_dist, w_signal, slowdown):
    """Edge cost = blend of time, distance and signal delay, set by the sliders."""
    signals = get_signal_nodes()

    def cost(u, v, edges):
        best = float("inf")
        for a in edges.values():
            c = (
                w_time * _edge_time(a, slowdown)
                + w_dist * float(a.get("length", 0) or 0) / 10   # ~10 m/s scaling
                + w_signal * (SIGNAL_PENALTY_S if v in signals else 0)
            )
            best = min(best, c)
        return best

    return cost


def _path_stats(path, slowdown):
    graph = get_graph()
    signals = get_signal_nodes()
    secs = metres = 0.0
    for u, v in zip(path[:-1], path[1:]):
        data = graph.get_edge_data(u, v)
        if data:
            e = min(data.values(), key=lambda a: _edge_time(a, slowdown))
            secs += _edge_time(e, slowdown)
            metres += float(e.get("length", 0) or 0)
    return {
        "distance_km": round(metres / 1000, 2),
        "time_min": round(secs / 60, 1),
        "signals": sum(1 for n in path[1:-1] if n in signals),
    }


def _coordinates(path):
    graph = get_graph()
    return [[float(graph.nodes[n]["y"]), float(graph.nodes[n]["x"])] for n in path]


def explain(custom, fastest):
    """Plain-English trade-off between the custom route and the fastest route."""
    dt = custom["time_min"] - fastest["time_min"]
    dd = custom["distance_km"] - fastest["distance_km"]
    ds = fastest["signals"] - custom["signals"]
    if abs(dt) < 0.05 and abs(dd) < 0.005 and ds == 0:
        return "Your custom route matches the fastest route."
    msg = (
        f"vs. the fastest route: {abs(dt):.1f} min {'slower' if dt > 0 else 'faster'}, "
        f"{abs(dd):.2f} km {'longer' if dd > 0 else 'shorter'}"
    )
    if ds > 0:
        msg += f", {ds} fewer traffic signals"
    elif ds < 0:
        msg += f", {-ds} more traffic signals"
    return msg + "."


def _route_for_points(origin, destination, prefs=None):
    graph = get_graph()
    prefs = prefs or {}
    slowdown = get_slowdown(prefs.get("hour"))
    try:
        start = nearest_node(float(origin["lat"]), float(origin.get("lon", origin.get("lng"))))
        end = nearest_node(float(destination["lat"]), float(destination.get("lon", destination.get("lng"))))
        shortest = nx.shortest_path(graph, start, end, weight="length", method="dijkstra")
        fastest = nx.shortest_path(graph, start, end, weight="travel_time", method="dijkstra")
        custom = nx.shortest_path(
            graph, start, end,
            weight=make_cost(
                float(prefs.get("w_time", 1)),
                float(prefs.get("w_dist", 0)),
                float(prefs.get("w_signal", 0)),
                slowdown,
            ),
        )
    except (nx.NetworkXNoPath, nx.NodeNotFound, ValueError, KeyError) as exc:
        raise ValueError(
            "No route was found on the downloaded Minneapolis road network. "
            "Try locations within Minneapolis and closer to the covered road network."
        ) from exc

    def pack(path):
        return {"coordinates": _coordinates(path), **_path_stats(path, slowdown)}

    result = {
        "origin": origin,
        "destination": destination,
        "shortest": pack(shortest),
        "fastest": pack(fastest),
        "custom": pack(custom),
    }
    result["explanation"] = explain(result["custom"], result["fastest"])
    return result


# --------------------------------------------------------------------------
# Flask routes
# --------------------------------------------------------------------------
@app.get("/")
def index():
    return flask.Response(PAGE, mimetype="text/html")


@app.get("/api/defaults")
def defaults():
    try:
        return jsonify(_route_for_points(DEFAULT_ORIGIN, DEFAULT_DESTINATION))
    except Exception as exc:
        app.logger.exception("Could not calculate default routes")
        return jsonify({"error": str(exc)}), 500


@app.post("/api/route")
def calculate_route():
    data = request.get_json(silent=True) or {}
    try:
        origin = dict(data.get("origin") or {})
        destination = dict(data.get("destination") or {})
        for label, point in (("Origin", origin), ("Destination", destination)):
            if "lat" not in point or ("lon" not in point and "lng" not in point):
                raise ValueError(f"{label} needs latitude and longitude coordinates.")
            point["lat"] = float(point["lat"])
            point["lon"] = float(point.get("lon", point.get("lng")))
            if not (-90 <= point["lat"] <= 90 and -180 <= point["lon"] <= 180):
                raise ValueError(f"{label} coordinates are invalid.")
        return jsonify(_route_for_points(origin, destination, data.get("prefs")))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        app.logger.exception("Route calculation failed")
        return jsonify({"error": f"Route calculation failed: {exc}"}), 500


# --------------------------------------------------------------------------
# Front-end page (HTML + CSS + JS)
# --------------------------------------------------------------------------
PAGE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>UrbanPulse | Interactive Route Optimizer</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
:root{--bg:#0b1220;--panel:#111c2e;--panel2:#17253b;--line:#263750;--text:#e8effa;--muted:#9aacc5;--blue:#5aa9ff;--teal:#42d6c3;--orange:#ffb86b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 Inter,Segoe UI,Arial,sans-serif}
header{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:18px 24px;border-bottom:1px solid var(--line);background:#0d1728}
.brand{display:flex;align-items:center;gap:12px}.logo{width:38px;height:38px;border-radius:12px;background:linear-gradient(135deg,#48d7c3,#438bff);display:grid;place-items:center;color:#071321;font-size:20px;font-weight:900}
h1{font-size:18px;margin:0}.sub{color:var(--muted);font-size:12px;margin-top:3px}.status{color:var(--teal);font-size:12px}
main{display:grid;grid-template-columns:340px minmax(0,1fr);gap:16px;padding:16px;min-height:calc(100vh - 76px)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px;min-width:0}.panel h2{font-size:14px;margin:0 0 14px}.field{margin-bottom:14px}.field label{display:block;color:var(--muted);font-size:12px;margin-bottom:6px}
.inputrow{display:flex;gap:7px}.inputrow input{min-width:0;flex:1}input{background:#0a1424;border:1px solid #30435e;border-radius:9px;color:var(--text);padding:10px 11px;width:100%;outline:none}input:focus{border-color:var(--blue)}
input[type=range]{padding:0;border:none;background:transparent;accent-color:#b388ff}
select{background:#0a1424;border:1px solid #30435e;border-radius:9px;color:var(--text);padding:10px 11px;width:100%}
.sliders label{margin-top:8px}
button{cursor:pointer;border:1px solid #354a66;background:#1a2a42;color:var(--text);padding:9px 11px;border-radius:9px;font-weight:600}button:hover{filter:brightness(1.15)}button.primary{background:var(--blue);border-color:var(--blue);color:#071321}button.small{padding:8px 10px;font-size:12px}
.actions{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.hint{color:var(--muted);font-size:12px;margin:12px 0 16px}.metrics{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:16px}.metric{padding:13px;background:var(--panel2);border:1px solid var(--line);border-radius:12px}.metric .name{font-size:11px;color:var(--muted)}.metric .value{font-size:21px;font-weight:750;margin:5px 0 2px}.metric .unit{font-size:11px;color:var(--muted)}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}.blue{background:var(--blue)}.teal{background:var(--teal)}.purple{background:#b388ff}
#map{height:calc(100vh - 112px);min-height:520px;border-radius:14px;overflow:hidden;border:1px solid var(--line)}.mapwrap{min-width:0;position:relative}.mapbadge{position:absolute;z-index:500;top:12px;left:12px;background:#0b1220e8;border:1px solid var(--line);padding:9px 12px;border-radius:10px;font-size:12px;max-width:calc(100% - 24px)}
#message{white-space:pre-wrap;color:var(--orange);font-size:12px;margin-top:12px;min-height:18px}


.recommendation {
    margin-top: 14px;
    border: 1px solid #7655b7;
    background: linear-gradient(135deg, #1b2540, #211b3a);
}

.recommendation .name {
    color: #c4a5ff;
    letter-spacing: 0.7px;
    font-weight: 700;
}

.recommendation .value {
    font-size: 17px;
    line-height: 1.4;
}

.recommendation .unit {
    line-height: 1.6;
}


.comparison-scroll {
    width: 100%;
    overflow-x: auto;
}

.comparison-table {
    width: 100%;
    min-width: 470px;
    border-collapse: collapse;
    font-size: 11px;
    text-align: left;
}

.comparison-table th,
.comparison-table td {
    padding: 10px 8px;
    border-bottom: 1px solid var(--line);
    white-space: nowrap;
}

.comparison-table th {
    color: var(--muted);
    font-weight: 600;
}

.comparison-table td {
    color: var(--text);
}

.comparison-table tbody tr:last-child td {
    border-bottom: none;
}

.route-name {
    font-weight: 700;
}

.route-blue { color: #5aa9ff !important; }
.route-green { color: #22c55e !important; }
.route-purple { color: #b388ff !important; }


/* ===== URBAN PULSE: DARK COMMAND CENTER UI ===== */

:root {
  --lime: #c5f36b;
  --lime-soft: rgba(197, 243, 107, 0.12);
  --bg: #080d0b;
  --panel: #101713;
  --panel2: #17221b;
  --line: #2a3a30;
  --text: #edf5ee;
  --muted: #9eafa2;
  --orange: #ffc16e;
}

body {
  background:
    radial-gradient(ellipse at 15% 0%, rgba(93, 143, 72, 0.10), transparent 38%),
    var(--bg);
  color: var(--text);
  letter-spacing: 0.1px;
}

header {
  background: rgba(11, 18, 13, 0.97);
  border-bottom: 1px solid var(--line);
  padding: 20px 26px;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.16);
}

.logo {
  background: linear-gradient(135deg, #d5ff83, #83c84c);
  color: #11190c;
  border-radius: 12px;
  box-shadow: 0 0 24px rgba(197, 243, 107, 0.15);
}

h1 {
  font-size: 19px;
  letter-spacing: -0.4px;
}

.sub {
  letter-spacing: 0.2px;
}

.status {
  color: var(--lime);
}

main {
  gap: 18px;
  padding: 18px;
}

.panel {
  background: linear-gradient(155deg, #121b15, #0e1511);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 20px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.16);
}

.panel h2 {
  font-size: 13px;
  font-weight: 750;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  margin-bottom: 17px;
}

.field label {
  letter-spacing: 0.25px;
}

input,
select {
  background: #0a110d;
  border-color: #34483a;
  border-radius: 10px;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

input:focus,
select:focus {
  border-color: var(--lime);
  box-shadow: 0 0 0 3px rgba(197, 243, 107, 0.10);
}

input[type=range] {
  accent-color: var(--lime);
}

button {
  border-radius: 10px;
  transition: transform 0.18s ease, filter 0.18s ease,
    border-color 0.18s ease;
}

button:hover {
  filter: brightness(1.12);
  border-color: #60775f;
}

button.primary {
  background: var(--lime);
  border-color: var(--lime);
  color: #11190c;
  font-weight: 800;
  box-shadow: 0 4px 18px rgba(197, 243, 107, 0.12);
}

button.primary:hover {
  filter: brightness(1.05);
  transform: translateY(-1px);
}

.metrics {
  gap: 11px;
}

.metric {
  background: linear-gradient(145deg, #19251c, #131c16);
  border: 1px solid #304334;
  border-radius: 14px;
  padding: 15px;
  transition: border-color 0.2s ease, transform 0.2s ease;
}

.metric:hover {
  border-color: #617a4b;
  transform: translateY(-2px);
}

.metric .name {
  text-transform: uppercase;
  letter-spacing: 0.65px;
  font-size: 10px;
}

.metric .value {
  font-size: 23px;
  letter-spacing: -0.6px;
  font-variant-numeric: tabular-nums;
}

.metric .unit {
  line-height: 1.5;
}

#map {
  border: 1px solid #304236;
  border-radius: 17px;
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.20);
}


.mapbadge {
  background: rgba(10, 17, 12, 0.96);
  color: #edf5ee;
  border: 1px solid #40563f;
  border-radius: 12px;
  padding: 11px 14px;
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 26px rgba(0, 0, 0, 0.32);
  font-size: 11px;
  font-weight: 650;
  line-height: 1.6;
  letter-spacing: 0.15px;
  max-width: min(390px, calc(100% - 24px));
}


.legend-heading {
  color: #c5f36b;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 1.2px;
  margin-bottom: 9px;
}

.legend-items {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #edf5ee;
  font-size: 11px;
  font-weight: 650;
}

.legend-line {
  display: inline-block;
  width: 20px;
  height: 3px;
  border-radius: 4px;
}

.shortest-line {
  background: #5aa9ff;
}

.fastest-line {
  background: #22c55e;
}

.custom-line {
  background: #b388ff;
}

#message {
  line-height: 1.6;
}

/* Keep the existing mobile layout working */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    transition: none !important;
    animation: none !important;
  }
}


/* ===== ROUTE INSIGHTS & COMPARISON POLISH ===== */

.recommendation {
  background:
    radial-gradient(ellipse at top left, rgba(197, 243, 107, 0.10), transparent 65%),
    linear-gradient(145deg, #172219, #101713);
  border: 1px solid #50683b;
  border-radius: 15px;
  box-shadow: inset 3px 0 0 var(--lime);
  padding: 17px;
}

.recommendation .name {
  color: var(--lime);
  font-size: 10px;
  letter-spacing: 1px;
  margin-bottom: 9px;
}

.recommendation .value {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.3px;
  margin: 7px 0;
}

.recommendation .unit {
  color: #b2c1b5;
  font-size: 12px;
  line-height: 1.7;
}

.comparison-table {
  border-spacing: 0;
  font-size: 12px;
}

.comparison-table th {
  background: #18231b;
  color: #b5c6b8;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.7px;
  text-transform: uppercase;
}

.comparison-table th,
.comparison-table td {
  padding: 12px 9px;
  border-bottom: 1px solid #2b3b30;
}

.comparison-table tbody tr {
  transition: background 0.18s ease;
}

.comparison-table tbody tr:hover {
  background: rgba(197, 243, 107, 0.055);
}

.comparison-table tbody tr:last-child td {
  border-bottom: none;
}

.route-blue {
  color: #68b6ff !important;
  font-weight: 750;
}

.route-green {
  color: #65e6a0 !important;
  font-weight: 750;
}

.route-purple {
  color: #c4a5ff !important;
  font-weight: 750;
}

.comparison-scroll {
  border: 1px solid #293a2e;
  border-radius: 11px;
  overflow-x: auto;
}

#explain {
  line-height: 1.7;
  padding: 2px 1px;
}


/* ===== POLISHED ROUTE METRIC CARDS ===== */

.metrics {
    gap: 12px;
    margin-top: 18px;
}

.metrics .metric {
    position: relative;
    overflow: hidden;
    padding: 17px 16px 15px;
    background: linear-gradient(
        145deg,
        rgba(25, 39, 57, 0.98),
        rgba(15, 25, 39, 0.98)
    );
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 14px;
    box-shadow: 0 5px 16px rgba(0, 0, 0, 0.12);
    transition:
        transform 0.2s ease,
        border-color 0.2s ease,
        box-shadow 0.2s ease;
}

/* Subtle route-coloured accent at the top */
.metrics .metric::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    opacity: 0.95;
}

.metrics .metric:nth-child(1)::before {
    background: #5aa9ff;
}

.metrics .metric:nth-child(2)::before {
    background: #42d6c3;
}

.metrics .metric:nth-child(3)::before {
    background: #b388ff;
}

.metrics .metric:hover {
    transform: translateY(-2px);
    border-color: rgba(197, 243, 107, 0.35);
    box-shadow: 0 9px 22px rgba(0, 0, 0, 0.2);
}

/* Card labels */
.metrics .metric .name {
    display: flex;
    align-items: center;
    gap: 7px;
    margin-bottom: 12px;
    color: #b7c5d8;
    font-size: 10px;
    font-weight: 750;
    letter-spacing: 1px;
    line-height: 1.5;
    text-transform: uppercase;
}

/* Distance values */
.metrics .metric .value {
    margin: 0 0 8px;
    color: #f2f7ff;
    font-size: clamp(22px, 2vw, 28px);
    font-weight: 800;
    letter-spacing: -0.8px;
    line-height: 1.2;
    font-variant-numeric: tabular-nums;
    overflow-wrap: anywhere;
}

/* Supporting estimated-time text */
.metrics .metric .unit {
    color: #91a5bd;
    font-size: 11px;
    font-weight: 500;
    line-height: 1.6;
}

/* Keep the custom route card spacious */
.metrics .metric:nth-child(3) {
    padding-top: 18px;
    padding-bottom: 17px;
}

.metrics .metric:nth-child(3) .value {
    font-size: clamp(24px, 2.2vw, 30px);
}

/* Preserve comfortable spacing on smaller screens */
@media (max-width: 480px) {
    .metrics {
        gap: 9px;
    }

    .metrics .metric {
        padding: 14px 11px 12px;
    }

    .metrics .metric .name {
        font-size: 9px;
        letter-spacing: 0.6px;
    }

    .metrics .metric .value {
        font-size: 21px;
    }
}


/* ===== COMPACT ROUTE COMPARISON TABLE ===== */

.comparison-scroll {
    width: 100%;
    max-width: 100%;
    overflow-x: hidden;
    border-radius: 8px;
}

.comparison-table {
    width: 100%;
    min-width: 0;
    table-layout: fixed;
    border-collapse: collapse;
    font-size: 10px;
}

.comparison-table th,
.comparison-table td {
    padding: 9px 3px;
    white-space: normal;
    overflow-wrap: break-word;
    word-break: normal;
    text-align: left;
    vertical-align: middle;
    line-height: 1.5;
}

.comparison-table th:first-child,
.comparison-table td:first-child {
    width: 24%;
}

.comparison-table th:nth-child(2),
.comparison-table td:nth-child(2) {
    width: 21%;
}

.comparison-table th:nth-child(3),
.comparison-table td:nth-child(3) {
    width: 17%;
}

.comparison-table th:nth-child(4),
.comparison-table td:nth-child(4) {
    width: 16%;
}

.comparison-table th:nth-child(5),
.comparison-table td:nth-child(5) {
    width: 22%;
}

.comparison-table th {
    font-size: 8px;
    letter-spacing: 0.1px;
    line-height: 1.4;
}

.comparison-table td {
    font-size: 9px;
}


/* ===== SIDEBAR TEXT READABILITY ===== */

/* Field labels and slider labels */
.panel .field label {
    color: #c0cebf;
    font-size: 12px;
    line-height: 1.5;
}

/* Helper text beneath the map-picking controls */
.panel .hint,
#explain {
    color: #b7c6b8;
    font-size: 12px;
    line-height: 1.65;
}

/* Route metric card labels */
.metrics .metric .name {
    color: #c4d1df;
    font-size: 11px;
    letter-spacing: 0.6px;
    line-height: 1.5;
}

/* Estimated travel time and signal details */
.metrics .metric .unit {
    color: #b0bfd1;
    font-size: 12px;
    line-height: 1.55;
}

/* Recommendation heading and explanation */
.recommendation .name {
    font-size: 11px;
    line-height: 1.5;
}

.recommendation .unit {
    color: #c0cec2;
    font-size: 12px;
    line-height: 1.65;
}

/* Keep input text comfortable to read */
.panel input:not([type="range"]),
.panel select {
    font-size: 12px;
}

/* Keep the compact layout on smaller screens */
@media (max-width: 480px) {
    .metrics .metric .name {
        font-size: 10px;
    }

    .metrics .metric .unit {
        font-size: 11px;
    }

    .recommendation .unit,
    .panel .hint,
    #explain {
        font-size: 11px;
    }
}


@media(max-width:850px){main{grid-template-columns:1fr}.mapwrap{order:1}aside{order:2}#map{height:58vh;min-height:400px}header{padding:14px 16px}}
</style></head>
<body>
<header><div class="brand"><div class="logo">U</div><div><h1>UrbanPulse</h1><div class="sub">Interactive Route Optimizer · Minneapolis</div></div></div><div class="status">● Road-network routing</div></header>
<main>
<aside class="panel">
<h2>Plan your journey</h2>
<div class="field"><label for="originSearch">Origin</label><div class="inputrow"><input id="originSearch" placeholder="Search a Minneapolis place"><button class="small" onclick="searchPlace('origin')">Find</button></div></div>
<div class="field"><label for="destinationSearch">Destination</label><div class="inputrow"><input id="destinationSearch" placeholder="Search a destination"><button class="small" onclick="searchPlace('destination')">Find</button></div></div>
<div class="actions"><button onclick="startPick('origin')">Pick origin on map</button><button onclick="startPick('destination')">Pick destination</button></div>
<div class="hint" id="pickHint">Choose a point using search or the map. If no pick button is active, map clicks alternate between origin and destination.</div>

<div class="field sliders"><label>Route priorities</label>
<label for="wTime">Travel time</label><input type="range" id="wTime" min="0" max="2" step="0.1" value="1">
<label for="wDist">Short distance</label><input type="range" id="wDist" min="0" max="2" step="0.1" value="0">
<label for="wSig">Avoid traffic signals</label><input type="range" id="wSig" min="0" max="3" step="0.1" value="0">
<label for="hourSel">Departure time</label><select id="hourSel"><option value="-1">Free-flow (ignore time of day)</option></select></div>

<button class="primary" style="width:100%" onclick="compareRoutes()">Compare routes</button><button style="width:100%;margin-top:8px" onclick="resetRoute()">Reset example</button>
<div id="message"></div>
<div class="metrics">
<div class="metric"><div class="name"><span class="dot blue"></span>Shortest distance</div><div class="value" id="shortDistance">—</div><div class="unit" id="shortTime">Estimated time: —</div></div>
<div class="metric"><div class="name"><span class="dot teal"></span>Fastest estimated time</div><div class="value" id="fastDistance">—</div><div class="unit" id="fastTime">Estimated time: —</div></div>
<div class="metric" style="grid-column:1/-1"><div class="name"><span class="dot purple"></span>Your custom route</div><div class="value" id="customDistance">—</div><div class="unit" id="customTime">Estimated time: —</div></div>
</div>
<div class="hint" id="explain"></div>

<div class="metric recommendation" id="recommendationCard">
    <div class="name">✦ URBANPULSE RECOMMENDATION</div>
    <div class="value" id="recommendationTitle">Calculating best route...</div>
    <div class="unit" id="recommendationReason">
        Adjust your route priorities to get a personalized recommendation.
    </div>
</div>


<div class="metric" style="margin-top:14px; grid-column:1/-1;">
    <div class="name">ROUTE COMPARISON</div>
    <div class="unit" style="margin:6px 0 12px;">
        Trade-offs compared with the fastest route
    </div>

    <div class="comparison-scroll">
        <table class="comparison-table">
            <thead>
                <tr>
                    <th>Route</th>
                    <th>Distance</th>
                    <th>Time</th>
                    <th>Signals</th>
                    <th>Trade-off vs. fastest</th>
                </tr>
            </thead>
            <tbody id="comparisonBody">
                <tr>
                    <td colspan="5">Calculate a route to see comparisons.</td>
                </tr>
            </tbody>
        </table>
    </div>
</div>


<div class="hint">Coverage is limited to the downloaded Minneapolis driving network. Time-of-day effects are a modeled estimate from historical traffic patterns, not live traffic. Search uses Photon; map tiles use OpenStreetMap.</div>
</aside>

<section class="mapwrap">
  <div class="mapbadge" id="mapBadge">
    <div class="legend-heading">ROUTE LEGEND</div>
    <div class="legend-items">
      <span class="legend-item">
        <span class="legend-line shortest-line"></span>
        Shortest
      </span>
      <span class="legend-item">
        <span class="legend-line fastest-line"></span>
        Fastest
      </span>
      <span class="legend-item">
        <span class="legend-line custom-line"></span>
        Custom
      </span>
    </div>
  </div>
  <div id="map"></div>
</section>

</main>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const DEFAULT_ORIGIN=__DEFAULT_ORIGIN__;
const DEFAULT_DESTINATION=__DEFAULT_DESTINATION__;
const map=L.map('map').setView([44.9778,-93.2650],13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
let origin={...DEFAULT_ORIGIN},destination={...DEFAULT_DESTINATION},originMarker=null,destinationMarker=null,shortLine=null,fastLine=null,customLine=null,pickMode=null,clickCount=0;
function say(msg){document.getElementById('message').textContent=msg||''}
function badge(msg){document.getElementById('mapBadge').textContent=msg}
function fmtTime(n){if(n<60)return `${Math.round(n*10)/10} min`;return `${Math.floor(n/60)} h ${Math.round(n%60)} min`}
function updateMarkers(){
 if(originMarker)map.removeLayer(originMarker);if(destinationMarker)map.removeLayer(destinationMarker);
 originMarker=L.marker([origin.lat,origin.lon]).addTo(map).bindPopup('Origin: '+(origin.name||'Selected origin'));
 destinationMarker=L.marker([destination.lat,destination.lon]).addTo(map).bindPopup('Destination: '+(destination.name||'Selected destination'));
 document.getElementById('originSearch').value=origin.name||`${origin.lat.toFixed(5)}, ${origin.lon.toFixed(5)}`;
 document.getElementById('destinationSearch').value=destination.name||`${destination.lat.toFixed(5)}, ${destination.lon.toFixed(5)}`;
}
function clearLines(){[shortLine,fastLine,customLine].forEach(l=>{if(l)map.removeLayer(l)});shortLine=fastLine=customLine=null}
function getPrefs(){return{w_time:+document.getElementById('wTime').value,w_dist:+document.getElementById('wDist').value,w_signal:+document.getElementById('wSig').value,hour:+document.getElementById('hourSel').value}}


function updateRecommendation(data) {
    const routes = [
        { key: "shortest", name: "Blue route — Shortest distance", color: "#5aa9ff" },
        { key: "fastest", name: "Green route — Fastest estimated time", color: "#22c55e" },
        { key: "custom", name: "Purple route — Your custom route", color: "#b388ff" }
    ];

    const weights = {
        time: Math.max(0, Number(document.getElementById("wTime").value)),
        distance: Math.max(0, Number(document.getElementById("wDist").value)),
        signals: Math.max(0, Number(document.getElementById("wSig").value))
    };

    const totalWeight = weights.time + weights.distance + weights.signals;

    // If all sliders are zero, recommend the custom route by default.
    if (totalWeight === 0) {
        document.getElementById("recommendationTitle").textContent =
            "Purple route — Your custom route";

        document.getElementById("recommendationReason").textContent =
            "All priorities are set to zero. Increase a priority to personalize the recommendation.";

        return;
    }

    const values = {
        time: routes.map(r => Number(data[r.key].time_min)),
        distance: routes.map(r => Number(data[r.key].distance_km)),
        signals: routes.map(r => Number(data[r.key].signals))
    };

    // Normalize metrics so minutes, kilometres, and signal counts
    // can be compared fairly.
    function normalized(value, list) {
        const min = Math.min(...list);
        const max = Math.max(...list);
        return max === min ? 0 : (value - min) / (max - min);
    }

    const ranked = routes.map((route, i) => {
        const score =
            weights.time / totalWeight *
                normalized(values.time[i], values.time) +
            weights.distance / totalWeight *
                normalized(values.distance[i], values.distance) +
            weights.signals / totalWeight *
                normalized(values.signals[i], values.signals);

        return { ...route, score, stats: data[route.key] };
    }).sort((a, b) => a.score - b.score);

    const best = ranked[0];

    let reason = "This route best matches your current priority settings. ";
    const priorities = [
        { key: "time", weight: weights.time, label: "travel time" },
        { key: "distance", weight: weights.distance, label: "short distance" },
        { key: "signals", weight: weights.signals, label: "avoiding traffic signals" }
    ].sort((a, b) => b.weight - a.weight);

    if (priorities[0].weight > 0) {
        reason += "Your strongest priority is " + priorities[0].label + ". ";
    }

    reason += "Estimated time: " + best.stats.time_min +
        " min; distance: " + best.stats.distance_km +
        " km; traffic signals: " + best.stats.signals + ".";

    document.getElementById("recommendationTitle").textContent = best.name;
    document.getElementById("recommendationTitle").style.color = best.color;
    document.getElementById("recommendationReason").textContent = reason;
}


function updateComparisonTable(data) {
    const fastest = data.fastest;

    const routes = [
        {
            key: "shortest",
            name: "Shortest",
            className: "route-blue"
        },
        {
            key: "fastest",
            name: "Fastest",
            className: "route-green"
        },
        {
            key: "custom",
            name: "Custom",
            className: "route-purple"
        }
    ];

    function difference(value, unit, digits = 1) {
        const rounded = Number(Number(value).toFixed(digits));

        if (rounded === 0) {
            return "Same";
        }

        return `${rounded > 0 ? "+" : ""}${rounded.toFixed(digits)} ${unit}`;
    }

    function tradeoff(route) {
        if (route.key === "fastest") {
            return "Baseline — fastest";
        }

        const stats = data[route.key];

        const timeDiff = stats.time_min - fastest.time_min;
        const distanceDiff = stats.distance_km - fastest.distance_km;
        const signalDiff = stats.signals - fastest.signals;

        const parts = [];

        if (Math.abs(timeDiff) >= 0.05) {
            parts.push(difference(timeDiff, "min"));
        }

        if (Math.abs(distanceDiff) >= 0.005) {
            parts.push(difference(distanceDiff, "km", 2));
        }

        if (signalDiff !== 0) {
            parts.push(difference(signalDiff, "signals", 0));
        }

        return parts.length ? parts.join(" · ") : "Very similar";
    }

    document.getElementById("comparisonBody").innerHTML =
        routes.map(route => {
            const stats = data[route.key];

            return `
                <tr>
                    <td class="route-name ${route.className}">
                        ${route.name}
                    </td>
                    <td>${Number(stats.distance_km).toFixed(2)} km</td>
                    <td>${Number(stats.time_min).toFixed(1)} min</td>
                    <td>${stats.signals}</td>
                    <td>${tradeoff(route)}</td>
                </tr>
            `;
        }).join("");
}


function drawRoutes(data){
 clearLines();
 shortLine=L.polyline(data.shortest.coordinates,{color:'#5aa9ff',weight:6,opacity:.92}).addTo(map);
 fastLine=L.polyline(data.fastest.coordinates,{
    color:'#22c55e',
    weight:5,
    opacity:0.95
}).addTo(map);
 customLine=L.polyline(data.custom.coordinates,{color:'#b388ff',weight:5,opacity:.95}).addTo(map);
 const sig=r=>' · '+r.signals+' signals';
 document.getElementById('shortDistance').textContent=data.shortest.distance_km+' km';
 document.getElementById('shortTime').textContent='Estimated time: '+fmtTime(data.shortest.time_min)+sig(data.shortest);
 document.getElementById('fastDistance').textContent=data.fastest.distance_km+' km';
 document.getElementById('fastTime').textContent='Estimated time: '+fmtTime(data.fastest.time_min)+sig(data.fastest);
 document.getElementById('customDistance').textContent=data.custom.distance_km+' km';
 document.getElementById('customTime').textContent='Estimated time: '+fmtTime(data.custom.time_min)+sig(data.custom);
 document.getElementById('explain').textContent=data.explanation||'';
 updateRecommendation(data);
 updateComparisonTable(data);
 updateMarkers();
 const bounds=L.latLngBounds(data.shortest.coordinates.concat(data.fastest.coordinates,data.custom.coordinates));
 bounds.extend([origin.lat,origin.lon]);bounds.extend([destination.lat,destination.lon]);map.fitBounds(bounds.pad(.12));
 say('');
}
async function compareRoutes(){
 say('Calculating routes…');
 try{const r=await fetch('/api/route',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({origin,destination,prefs:getPrefs()})});
 const d=await r.json();if(!r.ok)throw new Error(d.error||'Could not calculate routes.');drawRoutes(d);}
 catch(e){say(e.message);badge('Route calculation needs attention');}
}
async function loadDefaults(){
 try{const r=await fetch('/api/defaults');const d=await r.json();if(!r.ok||d.error)throw new Error(d.error||'Could not load routes.');drawRoutes(d);}
 catch(e){say(e.message);badge('Unable to load routes');}
}
function startPick(which){pickMode=which;document.getElementById('pickHint').textContent=`Click the map to set the ${which}.`;say('')}
map.on('click',e=>{
 const p={lat:e.latlng.lat,lon:e.latlng.lng,name:`Map point (${e.latlng.lat.toFixed(4)}, ${e.latlng.lng.toFixed(4)})`};
 if(pickMode==='origin'){origin=p;pickMode=null;}else if(pickMode==='destination'){destination=p;pickMode=null;}
 else if(clickCount%2===0){origin=p;clickCount++;}else{destination=p;clickCount++;}
 updateMarkers();say('Location selected. Click Compare routes to recalculate.');
});
async function searchPlace(which){
 const input=document.getElementById(which==='origin'?'originSearch':'destinationSearch'),q=input.value.trim();
 if(!q){say('Enter a place name first.');return;}say('Searching for a place…');
 try{
  const r=await fetch('https://photon.komoot.io/api/?limit=8&q='+encodeURIComponent(q+' Minneapolis Minnesota'));
  if(!r.ok)throw new Error('Place search service did not respond.');
  const d=await r.json(),features=(d.features||[]).filter(f=>{
   const p=f.properties||{},txt=[p.city,p.county,p.state,p.country].join(' ').toLowerCase();
   return txt.includes('minneapolis')||txt.includes('minnesota');
  });
  if(!features.length)throw new Error('No matching Minneapolis place found. Try a more specific landmark or address.');
  const f=features[0],c=f.geometry.coordinates,p=f.properties||{},name=[p.name,p.street,p.city].filter(Boolean).join(', ')||q;
  const point={name,lon:c[0],lat:c[1]};if(which==='origin')origin=point;else destination=point;
  updateMarkers();say('Place selected. Click Compare routes to calculate both routes.');map.setView([point.lat,point.lon],15);
 }catch(e){say(e.message)}
}
function resetRoute(){origin={...DEFAULT_ORIGIN};destination={...DEFAULT_DESTINATION};clickCount=0;pickMode=null;
 document.getElementById('wTime').value=1;document.getElementById('wDist').value=0;document.getElementById('wSig').value=0;document.getElementById('hourSel').value=-1;
 updateMarkers();loadDefaults()}

// Departure-time dropdown and live slider updates
const hs=document.getElementById('hourSel');
for(let h=0;h<24;h++){const o=document.createElement('option');o.value=h;o.textContent=(h%12||12)+':00 '+(h<12?'AM':'PM');hs.appendChild(o);}
let _t=null;
['wTime','wDist','wSig','hourSel'].forEach(id=>document.getElementById(id).addEventListener('input',()=>{clearTimeout(_t);_t=setTimeout(compareRoutes,350);}));

updateMarkers();loadDefaults();
</script></body></html>
""".replace("__DEFAULT_ORIGIN__", json.dumps(DEFAULT_ORIGIN)).replace(
    "__DEFAULT_DESTINATION__", json.dumps(DEFAULT_DESTINATION)
)


if __name__ == "__main__":
    print("=" * 58)
    print(APP_TITLE)
    print("=" * 58)
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Road graph:   {GRAPH_PATH}")
    get_graph()
    get_signal_nodes()
    get_hour_load()
    url = f"http://{HOST}:{PORT}"
    print(f"\nOpen in your browser: {url}")
    print("Keep this terminal open while using UrbanPulse.")
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host=HOST, port=PORT, debug=False, threaded=True)