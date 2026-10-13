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
<div class="hint">Coverage is limited to the downloaded Minneapolis driving network. Time-of-day effects are a modeled estimate from historical traffic patterns, not live traffic. Search uses Photon; map tiles use OpenStreetMap.</div>
</aside>
<section class="mapwrap"><div class="mapbadge" id="mapBadge">Loading routes…</div><div id="map"></div></section>
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
function drawRoutes(data){
 clearLines();
 shortLine=L.polyline(data.shortest.coordinates,{color:'#5aa9ff',weight:6,opacity:.92}).addTo(map);
 fastLine=L.polyline(data.fastest.coordinates,{color:'#42d6c3',weight:4,opacity:.95,dashArray:'9 7'}).addTo(map);
 customLine=L.polyline(data.custom.coordinates,{color:'#b388ff',weight:5,opacity:.95}).addTo(map);
 const sig=r=>' · '+r.signals+' signals';
 document.getElementById('shortDistance').textContent=data.shortest.distance_km+' km';
 document.getElementById('shortTime').textContent='Estimated time: '+fmtTime(data.shortest.time_min)+sig(data.shortest);
 document.getElementById('fastDistance').textContent=data.fastest.distance_km+' km';
 document.getElementById('fastTime').textContent='Estimated time: '+fmtTime(data.fastest.time_min)+sig(data.fastest);
 document.getElementById('customDistance').textContent=data.custom.distance_km+' km';
 document.getElementById('customTime').textContent='Estimated time: '+fmtTime(data.custom.time_min)+sig(data.custom);
 document.getElementById('explain').textContent=data.explanation||'';
 updateMarkers();
 const bounds=L.latLngBounds(data.shortest.coordinates.concat(data.fastest.coordinates,data.custom.coordinates));
 bounds.extend([origin.lat,origin.lon]);bounds.extend([destination.lat,destination.lon]);map.fitBounds(bounds.pad(.12));
 badge('Shortest (blue) · Fastest (teal, dashed) · Custom (purple)');say('');
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