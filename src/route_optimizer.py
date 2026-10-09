
from pathlib import Path

import osmnx as ox
import networkx as nx
import folium

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
        graph,
        origin_node,
        destination_node,
        weight="length"
    )

    fastest_route = nx.shortest_path(
        graph,
        origin_node,
        destination_node,
        weight="travel_time"
    )

    return shortest_route, fastest_route


def route_metrics(graph, route):
    """Calculate route distance and estimated travel time."""
    distance_m = nx.path_weight(graph, route, weight="length")
    time_s = nx.path_weight(graph, route, weight="travel_time")

    return distance_m / 1000, time_s / 60



def create_route_map(graph, shortest_route, fastest_route,
                     origin, destination):
    """Display both routes on an interactive Folium map."""

    # Calculate route metrics
    shortest_km, shortest_min = route_metrics(
        graph, shortest_route
    )
    fastest_km, fastest_min = route_metrics(
        graph, fastest_route
    )

    # Calculate map center
    center = [
        (origin[0] + destination[0]) / 2,
        (origin[1] + destination[1]) / 2
    ]

    # Create map without external background tiles
    route_map = folium.Map(
        location=center,
        zoom_start=13,
        tiles=None
    )

    # Draw the shortest-distance route
    shortest_coords = [
        (graph.nodes[node]["y"], graph.nodes[node]["x"])
        for node in shortest_route
    ]

    folium.PolyLine(
        shortest_coords,
        color="blue",
        weight=6,
        opacity=0.8,
        tooltip="Shortest-distance route"
    ).add_to(route_map)

    # Draw the fastest estimated-time route
    fastest_coords = [
        (graph.nodes[node]["y"], graph.nodes[node]["x"])
        for node in fastest_route
    ]

    folium.PolyLine(
        fastest_coords,
        color="green",
        weight=5,
        opacity=0.8,
        tooltip="Fastest estimated-time route"
    ).add_to(route_map)

    # Add origin marker
    folium.Marker(
        location=origin,
        tooltip="Origin",
        icon=folium.Icon(color="blue", icon="play")
    ).add_to(route_map)

    # Add destination marker
    folium.Marker(
        location=destination,
        tooltip="Destination",
        icon=folium.Icon(color="red", icon="stop")
    ).add_to(route_map)

    # Route legend
    legend_html = """
    <div style="
        position: fixed;
        bottom: 35px;
        left: 35px;
        z-index: 9999;
        background: white;
        padding: 12px 16px;
        border: 1px solid #cccccc;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        font-family: Arial, sans-serif;
        font-size: 13px;
    ">
        <b>Urban-Pulse Route Legend</b><br><br>
        <span style="color: blue;">&#9632;</span>
        Shortest-distance route<br>
        <span style="color: green;">&#9632;</span>
        Fastest estimated-time route<br><br>
        <span style="color: #2878D0;">&#9679;</span>
        Origin<br>
        <span style="color: red;">&#9679;</span>
        Destination
    </div>
    """

    route_map.get_root().html.add_child(
        folium.Element(legend_html)
    )

    # Route comparison summary
    summary_html = f"""
    <div style="
        position: fixed;
        top: 15px;
        right: 15px;
        z-index: 9999;
        background: white;
        padding: 14px 18px;
        border: 1px solid #cccccc;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        font-family: Arial, sans-serif;
        font-size: 13px;
        min-width: 220px;
    ">
        <h4 style="margin: 0 0 10px 0;">Urban-Pulse</h4>

        <b style="color: blue;">Shortest Route</b><br>
        Distance: {shortest_km:.2f} km<br>
        Estimated time: {shortest_min:.1f} min

        <hr>

        <b style="color: green;">Fastest Route</b><br>
        Distance: {fastest_km:.2f} km<br>
        Estimated time: {fastest_min:.1f} min

        <hr>

        <small>Times are estimates, not live traffic.</small>
    </div>
    """

    route_map.get_root().html.add_child(
        folium.Element(summary_html)
    )

    # Save interactive map
    route_map.save(str(MAP_FILE))
    print(f"\nInteractive map saved to: {MAP_FILE}")

    return route_map


def main():
    graph = build_road_network(PLACE)

    # Example coordinates: Minneapolis city centre to the
    # University of Minnesota area. Coordinates are (latitude, longitude).
    origin = (44.9778, -93.2650)
    destination = (44.9396, -93.1660)

    shortest_route, fastest_route = find_routes(
        graph, origin, destination
    )

    print("Same route:", shortest_route == fastest_route)
    print("Shortest route nodes:", len(shortest_route))
    print("Fastest route nodes:", len(fastest_route))

    shortest_km, shortest_min = route_metrics(
        graph, shortest_route
    )
    fastest_km, fastest_min = route_metrics(
        graph, fastest_route
    )

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
        graph, shortest_route, fastest_route,
        origin, destination
    )


if __name__ == "__main__":
    main()
