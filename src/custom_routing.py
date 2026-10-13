import networkx as nx

def make_cost(G, w_time=1.0, w_dist=0.0, w_signal=0.0):
    # nodes tagged as traffic signals in OSM
    signals = {n for n, d in G.nodes(data=True)
               if d.get("highway") == "traffic_signals"}

    def cost(u, v, edges):
        # MultiDiGraph passes all parallel edges, so take the cheapest
        best = float("inf")
        for a in edges.values():
            c = (w_time * a["travel_time"]            # seconds
                 + w_dist * a["length"] / 10          # ~10 m/s scaling
                 + w_signal * (20 if v in signals else 0))  # ~20 s per light
            best = min(best, c)
        return best
    return cost

def route_stats(G, route):
    signals = sum(1 for n in route[1:-1]
                  if G.nodes[n].get("highway") == "traffic_signals")
    time = dist = 0
    for u, v in zip(route[:-1], route[1:]):
        e = min(G[u][v].values(), key=lambda a: a["travel_time"])
        time += e["travel_time"]; dist += e["length"]
    return {"time_min": round(time/60, 1),
            "dist_km": round(dist/1000, 2),
            "signals": signals}

def custom_route(G, orig, dest, w_time, w_dist, w_signal):
    route = nx.shortest_path(G, orig, dest,
                             weight=make_cost(G, w_time, w_dist, w_signal))
    return route, route_stats(G, route)