from pathlib import Path

import folium
import networkx as nx
import osmnx as ox
from folium.plugins import Fullscreen

# Output paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

MAP_FILE = OUTPUT_DIR / "route_comparison.html"

# Minneapolis, Minnesota
PLACE = "Minneapolis, Minnesota, USA"


def build_road_network(place):
    """Download a drivable road network and estimate travel speeds."""
    print(f"Downloading road network for {place}...")

    graph = ox.graph_from_place(
        place,
        network_type="drive",
        simplify=True
    )
    graph = ox.add_edge_speeds(graph)
    graph = ox.add_edge_travel_times(graph)

    print(
        f"Road network loaded: "
        f"{len(graph.nodes)} intersections/nodes, "
        f"{len(graph.edges)} road segments."
    )
    return graph


def find_routes(graph, origin, destination):
    """Find shortest-distance and estimated-fastest routes."""
    origin_node = ox.distance.nearest_nodes(
        graph, origin[1], origin[0]
    )
    destination_node = ox.distance.nearest_nodes(
        graph, destination[1], destination[0]
    )

    shortest_route = nx.shortest_path(
        graph, origin_node, destination_node, weight="length"
    )
    fastest_route = nx.shortest_path(
        graph, origin_node, destination_node, weight="travel_time"
    )

    return shortest_route, fastest_route


def route_metrics(graph, route):
    """Return route distance in kilometres and estimated time in minutes."""
    distance_m = nx.path_weight(graph, route, weight="length")
    time_s = nx.path_weight(graph, route, weight="travel_time")
    return distance_m / 1000, time_s / 60


def create_route_map(graph, shortest_route, fastest_route, origin, destination):
    """Create a polished interactive map comparing both routes."""

    shortest_km, shortest_min = route_metrics(graph, shortest_route)
    fastest_km, fastest_min = route_metrics(graph, fastest_route)

    time_saved = shortest_min - fastest_min
    extra_distance = fastest_km - shortest_km

    shortest_coords = [
        (graph.nodes[node]["y"], graph.nodes[node]["x"])
        for node in shortest_route
    ]
    fastest_coords = [
        (graph.nodes[node]["y"], graph.nodes[node]["x"])
        for node in fastest_route
    ]

    center = [
        (origin[0] + destination[0]) / 2,
        (origin[1] + destination[1]) / 2
    ]

    # Keep OpenStreetMap as the basemap. Open this HTML through localhost
    # if opening it directly as a file causes tile requests to return 403.
    route_map = folium.Map(
        location=center,
        zoom_start=13,
        tiles="OpenStreetMap",
        control_scale=True,
        prefer_canvas=True
    )

    # Make map controls more useful for a demo/presentation.
    Fullscreen(
        position="topleft",
        title="Enter fullscreen",
        title_cancel="Exit fullscreen",
        force_separate_button=True
    ).add_to(route_map)

    # Separate feature groups let users turn either route on/off.
    shortest_layer = folium.FeatureGroup(
        name="Shortest-distance route",
        show=True
    )
    fastest_layer = folium.FeatureGroup(
        name="Fastest estimated-time route",
        show=True
    )

    # White casing makes each route easier to distinguish from busy roads.
    folium.PolyLine(
        shortest_coords,
        color="#FFFFFF",
        weight=10,
        opacity=0.95,
        interactive=False
    ).add_to(shortest_layer)
    folium.PolyLine(
        shortest_coords,
        color="#2563EB",
        weight=6,
        opacity=0.95,
        tooltip=f"Shortest route · {shortest_km:.2f} km · {shortest_min:.1f} min"
    ).add_to(shortest_layer)

    folium.PolyLine(
        fastest_coords,
        color="#FFFFFF",
        weight=9,
        opacity=0.95,
        interactive=False
    ).add_to(fastest_layer)
    folium.PolyLine(
        fastest_coords,
        color="#16A34A",
        weight=5,
        opacity=0.98,
        tooltip=f"Fastest route · {fastest_km:.2f} km · {fastest_min:.1f} min"
    ).add_to(fastest_layer)

    shortest_layer.add_to(route_map)
    fastest_layer.add_to(route_map)

    # Clear, compact origin and destination markers.
    folium.Marker(
        location=origin,
        tooltip="Origin",
        popup="<b>Origin</b><br>Minneapolis city centre",
        icon=folium.Icon(color="blue", icon="play")
    ).add_to(route_map)

    folium.Marker(
        location=destination,
        tooltip="Destination",
        popup="<b>Destination</b><br>Destination point",
        icon=folium.Icon(color="red", icon="flag")
    ).add_to(route_map)

    # Allow the audience to toggle either route independently.
    folium.LayerControl(
        position="topleft",
        collapsed=True
    ).add_to(route_map)

    # Floating route comparison panel.
    summary_html = f"""
    <style>
      .up-panel, .up-legend {{
        box-sizing: border-box;
        font-family: Inter, "Segoe UI", Arial, sans-serif;
        color: #172033;
        background: rgba(255,255,255,0.97);
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        box-shadow: 0 8px 28px rgba(15,23,42,0.16);
        backdrop-filter: blur(8px);
      }}
      .up-panel {{
        position: fixed; top: 16px; right: 16px; z-index: 9999;
        width: 300px; padding: 18px;
      }}
      .up-brand {{ display:flex; align-items:center; gap:10px; margin-bottom:5px; }}
      .up-logo {{
        width:34px; height:34px; display:flex; align-items:center;
        justify-content:center; border-radius:10px; color:white;
        font-size:18px; font-weight:800; background:#0f766e;
      }}
      .up-title {{ font-size:17px; font-weight:750; letter-spacing:-0.3px; }}
      .up-subtitle {{ color:#64748b; font-size:11px; margin:0 0 15px 44px; }}
      .up-route {{
        border:1px solid #e5eaf1; border-radius:12px;
        padding:12px; margin-top:10px;
      }}
      .up-route-head {{ display:flex; align-items:center; gap:8px; font-weight:700; font-size:13px; }}
      .up-dot {{ width:9px; height:9px; border-radius:50%; display:inline-block; }}
      .up-metrics {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:10px; }}
      .up-metric-label {{ font-size:10px; color:#64748b; margin-bottom:3px; }}
      .up-metric-value {{ font-size:17px; font-weight:750; letter-spacing:-0.4px; }}
      .up-fastest {{ background:#f0fdf4; border-color:#bbf7d0; }}
      .up-savings {{
        margin-top:12px; padding:10px 11px; border-radius:10px;
        background:#ecfdf5; color:#166534; font-size:12px; line-height:1.45;
      }}
      .up-note {{ margin-top:12px; color:#64748b; font-size:10px; line-height:1.45; }}
      .up-legend {{ position:fixed; bottom:24px; left:24px; z-index:9999; padding:13px 15px; min-width:200px; }}
      .up-legend-title {{ font-size:12px; font-weight:750; margin-bottom:10px; }}
      .up-legend-row {{ display:flex; align-items:center; gap:9px; font-size:11px; margin:7px 0; color:#334155; }}
      .up-line {{ width:23px; height:4px; border-radius:4px; display:inline-block; }}
      .up-pin {{ width:9px; height:9px; border-radius:50%; display:inline-block; }}
      @media (max-width: 600px) {{
        .up-panel {{ width: min(270px, calc(100vw - 28px)); top:10px; right:10px; padding:13px; }}
        .up-legend {{ left:10px; bottom:12px; min-width:170px; padding:10px 12px; }}
        .up-metric-value {{ font-size:15px; }}
      }}
    </style>

    <div class="up-panel">
      <div class="up-brand">
        <div class="up-logo">U</div>
        <div class="up-title">UrbanPulse</div>
      </div>
      <div class="up-subtitle">SMART ROUTE COMPARISON</div>

      <div class="up-route">
        <div class="up-route-head">
          <span class="up-dot" style="background:#2563EB"></span>
          <span>Shortest distance</span>
        </div>
        <div class="up-metrics">
          <div>
            <div class="up-metric-label">DISTANCE</div>
            <div class="up-metric-value">{shortest_km:.2f} <span style="font-size:11px;font-weight:600">km</span></div>
          </div>
          <div>
            <div class="up-metric-label">EST. TIME</div>
            <div class="up-metric-value">{shortest_min:.1f} <span style="font-size:11px;font-weight:600">min</span></div>
          </div>
        </div>
      </div>

      <div class="up-route up-fastest">
        <div class="up-route-head">
          <span class="up-dot" style="background:#16A34A"></span>
          <span>Fastest estimated time</span>
        </div>
        <div class="up-metrics">
          <div>
            <div class="up-metric-label">DISTANCE</div>
            <div class="up-metric-value">{fastest_km:.2f} <span style="font-size:11px;font-weight:600">km</span></div>
          </div>
          <div>
            <div class="up-metric-label">EST. TIME</div>
            <div class="up-metric-value">{fastest_min:.1f} <span style="font-size:11px;font-weight:600">min</span></div>
          </div>
        </div>
      </div>

      <div class="up-savings">
        <strong>⚡ Faster by {abs(time_saved):.1f} minutes</strong><br>
        {abs(extra_distance):.2f} km {'longer' if extra_distance > 0 else 'shorter'} than the shortest route.
      </div>
      <div class="up-note">
        Travel times are estimates based on road-speed data, not live traffic.
      </div>
    </div>
    """

    legend_html = """
    <div class="up-legend">
      <div class="up-legend-title">MAP LEGEND</div>
      <div class="up-legend-row"><span class="up-line" style="background:#2563EB"></span> Shortest-distance route</div>
      <div class="up-legend-row"><span class="up-line" style="background:#16A34A"></span> Fastest-time route</div>
      <div class="up-legend-row"><span class="up-pin" style="background:#2878D0"></span> Origin</div>
      <div class="up-legend-row"><span class="up-pin" style="background:#DC2626"></span> Destination</div>
      <div style="border-top:1px solid #e2e8f0;margin-top:10px;padding-top:9px;color:#64748b;font-size:10px">
        Use the layer control to show or hide routes.
      </div>
    </div>
    """

    route_map.get_root().html.add_child(folium.Element(summary_html))
    route_map.get_root().html.add_child(folium.Element(legend_html))

    # Frame both routes with some breathing room.
    all_route_coords = shortest_coords + fastest_coords
    route_map.fit_bounds(all_route_coords, padding=(55, 55))

    route_map.save(str(MAP_FILE))
    print(f"\nInteractive map saved to: {MAP_FILE}")
    return route_map


def main():
    graph = build_road_network(PLACE)

    # Example coordinates: Minneapolis city centre to the
    # University of Minnesota area. Coordinates are (latitude, longitude).
    origin = (44.9778, -93.2650)
    destination = (44.9396, -93.1660)

    shortest_route, fastest_route = find_routes(graph, origin, destination)

    print("Same route:", shortest_route == fastest_route)
    print("Shortest route nodes:", len(shortest_route))
    print("Fastest route nodes:", len(fastest_route))

    shortest_km, shortest_min = route_metrics(graph, shortest_route)
    fastest_km, fastest_min = route_metrics(graph, fastest_route)

    print("\n--- Route Comparison ---")
    print(
        f"Shortest route: {shortest_km:.2f} km, "
        f"estimated {shortest_min:.1f} minutes"
    )
    print(
        f"Fastest route:  {fastest_km:.2f} km, "
        f"estimated {fastest_min:.1f} minutes"
    )

    create_route_map(
        graph, shortest_route, fastest_route, origin, destination
    )


if __name__ == "__main__":
    main()
    