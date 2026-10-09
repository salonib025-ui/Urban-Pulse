"""
UrbanPulse Interactive Route Optimizer
Run from the UrbanPulse project root:
    python src/route_optimizer.py

Install dependencies:
    python -m pip install flask osmnx networkx
"""
from __future__ import annotations

import json
import os
import threading
import webbrowser
from pathlib import Path
from typing import Any

import flask
from flask import Flask, jsonify, request
import networkx as nx
import osmnx as ox

APP_TITLE = "UrbanPulse | Interactive Route Optimizer"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"
GRAPH_PATH = OUTPUT_DIR / "minneapolis_drive.graphml"
HOST = "127.0.0.1"
PORT = int(os.environ.get("URBANPULSE_PORT", "5000"))

app = Flask(__name__)
_graph: nx.MultiDiGraph | None = None
_graph_lock = threading.Lock()

DEFAULT_ORIGIN = {"name": "Minneapolis City Hall", "lat": 44.9778, "lon": -93.2650}
DEFAULT_DESTINATION = {"name": "Walker Art Center", "lat": 44.9672, "lon": -93.2887}


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


def _edge_for_weight(edge_data, weight):
    return min(
        edge_data.values(),
        key=lambda d: float(d.get(weight, d.get("length", 1.0)) or 1.0),
    )


def _route_distance_km(path):
    graph = get_graph()
    metres = 0.0
    for u, v in zip(path[:-1], path[1:]):
        data = graph.get_edge_data(u, v)
        if data:
            metres += float(_edge_for_weight(data, "length").get("length", 0.0) or 0.0)
    return metres / 1000.0


def _route_time_minutes(path):
    graph = get_graph()
    seconds = 0.0
    for u, v in zip(path[:-1], path[1:]):
        data = graph.get_edge_data(u, v)
        if data:
            seconds += float(_edge_for_weight(data, "travel_time").get("travel_time", 0.0) or 0.0)
    return seconds / 60.0


def _coordinates(path):
    graph = get_graph()
    return [[float(graph.nodes[n]["y"]), float(graph.nodes[n]["x"])] for n in path]


def _route_for_points(origin, destination):
    graph = get_graph()
    try:
        start = nearest_node(float(origin["lat"]), float(origin.get("lon", origin.get("lng"))))
        end = nearest_node(float(destination["lat"]), float(destination.get("lon", destination.get("lng"))))
        shortest = nx.shortest_path(graph, start, end, weight="length", method="dijkstra")
        fastest = nx.shortest_path(graph, start, end, weight="travel_time", method="dijkstra")
    except (nx.NetworkXNoPath, nx.NodeNotFound, ValueError, KeyError) as exc:
        raise ValueError(
            "No route was found on the downloaded Minneapolis road network. "
            "Try locations within Minneapolis and closer to the covered road network."
        ) from exc

    def pack(path):
        return {
            "coordinates": _coordinates(path),
            "distance_km": round(_route_distance_km(path), 2),
            "time_min": round(_route_time_minutes(path), 1),
        }

    return {
        "origin": origin,
        "destination": destination,
        "shortest": pack(shortest),
        "fastest": pack(fastest),
    }


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
        return jsonify(_route_for_points(origin, destination))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        app.logger.exception("Route calculation failed")
        return jsonify({"error": f"Route calculation failed: {exc}"}), 500


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
button{cursor:pointer;border:1px solid #354a66;background:#1a2a42;color:var(--text);padding:9px 11px;border-radius:9px;font-weight:600}button:hover{filter:brightness(1.15)}button.primary{background:var(--blue);border-color:var(--blue);color:#071321}button.small{padding:8px 10px;font-size:12px}
.actions{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.hint{color:var(--muted);font-size:12px;margin:12px 0 16px}.metrics{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:16px}.metric{padding:13px;background:var(--panel2);border:1px solid var(--line);border-radius:12px}.metric .name{font-size:11px;color:var(--muted)}.metric .value{font-size:21px;font-weight:750;margin:5px 0 2px}.metric .unit{font-size:11px;color:var(--muted)}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}.blue{background:var(--blue)}.teal{background:var(--teal)}
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
<button class="primary" style="width:100%" onclick="compareRoutes()">Compare routes</button><button style="width:100%;margin-top:8px" onclick="resetRoute()">Reset example</button>
<div id="message"></div>
<div class="metrics">
<div class="metric"><div class="name"><span class="dot blue"></span>Shortest distance</div><div class="value" id="shortDistance">—</div><div class="unit" id="shortTime">Estimated time: —</div></div>
<div class="metric"><div class="name"><span class="dot teal"></span>Fastest estimated time</div><div class="value" id="fastDistance">—</div><div class="unit" id="fastTime">Estimated time: —</div></div>
</div>
<div class="hint">Coverage is limited to the downloaded Minneapolis driving network. Search uses Photon; map tiles use OpenStreetMap.</div>
</aside>
<section class="mapwrap"><div class="mapbadge" id="mapBadge">Loading routes…</div><div id="map"></div></section>
</main>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const DEFAULT_ORIGIN=__DEFAULT_ORIGIN__;
const DEFAULT_DESTINATION=__DEFAULT_DESTINATION__;
const map=L.map('map').setView([44.9778,-93.2650],13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
let origin={...DEFAULT_ORIGIN},destination={...DEFAULT_DESTINATION},originMarker=null,destinationMarker=null,shortLine=null,fastLine=null,pickMode=null,clickCount=0;
function say(msg){document.getElementById('message').textContent=msg||''}
function badge(msg){document.getElementById('mapBadge').textContent=msg}
function fmtTime(n){if(n<60)return `${Math.round(n)} min`;return `${Math.floor(n/60)} h ${Math.round(n%60)} min`}
function updateMarkers(){
 if(originMarker)map.removeLayer(originMarker);if(destinationMarker)map.removeLayer(destinationMarker);
 originMarker=L.marker([origin.lat,origin.lon]).addTo(map).bindPopup('Origin: '+(origin.name||'Selected origin'));
 destinationMarker=L.marker([destination.lat,destination.lon]).addTo(map).bindPopup('Destination: '+(destination.name||'Selected destination'));
 document.getElementById('originSearch').value=origin.name||`${origin.lat.toFixed(5)}, ${origin.lon.toFixed(5)}`;
 document.getElementById('destinationSearch').value=destination.name||`${destination.lat.toFixed(5)}, ${destination.lon.toFixed(5)}`;
}
function clearLines(){if(shortLine)map.removeLayer(shortLine);if(fastLine)map.removeLayer(fastLine);shortLine=fastLine=null}
function drawRoutes(data){
 clearLines();shortLine=L.polyline(data.shortest.coordinates,{color:'#5aa9ff',weight:6,opacity:.92}).addTo(map);
 fastLine=L.polyline(data.fastest.coordinates,{color:'#42d6c3',weight:4,opacity:.95,dashArray:'9 7'}).addTo(map);
 document.getElementById('shortDistance').textContent=data.shortest.distance_km+' km';
 document.getElementById('shortTime').textContent='Estimated time: '+fmtTime(data.shortest.time_min);
 document.getElementById('fastDistance').textContent=data.fastest.distance_km+' km';
 document.getElementById('fastTime').textContent='Estimated time: '+fmtTime(data.fastest.time_min);
 updateMarkers();const bounds=L.latLngBounds(data.shortest.coordinates.concat(data.fastest.coordinates));
 bounds.extend([origin.lat,origin.lon]);bounds.extend([destination.lat,destination.lon]);map.fitBounds(bounds.pad(.12));
 badge('Routes calculated · shortest distance vs. fastest estimated time');say('');
}
async function compareRoutes(){
 say('Calculating routes…');
 try{const r=await fetch('/api/route',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({origin,destination})});
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
function resetRoute(){origin={...DEFAULT_ORIGIN};destination={...DEFAULT_DESTINATION};clickCount=0;pickMode=null;updateMarkers();loadDefaults()}
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
    url = f"http://{HOST}:{PORT}"
    print(f"\nOpen in your browser: {url}")
    print("Keep this terminal open while using UrbanPulse.")
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
