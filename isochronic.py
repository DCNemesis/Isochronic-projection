import osmnx as ox
import networkx as nx
import math
from tqdm import tqdm
from shapely.geometry import LineString
import geopandas as gpd
from numpy import inf


def main():
    lat = 45.50390
    lon = -73.57872
    dist = 15000
    cpus = 2
    pct_extremes = .025
    isos = 6
    iso_mins = 15
    iso_factor = 30
    node_size = 3
    output_loc = './images/mcgill_isochronic_map_walking_only.png'
    ox.config(log_console=True, use_cache=True, log_file='./isochronemap.log')
    G = ox.graph_from_point((lat, lon), dist=dist, network_type='walk')
    #gdf_nodes = ox.graph_to_gdfs(G, edges=False)
    #x, y = gdf_nodes['geometry'].unary_union.centroid.xy
    G = ox.project_graph(G)
    #points = gpd.points_from_xy([lon], [lat], crs=G.graph['crs'])
    #proj_points = points.to_crs(G.graph['crs'])
    #center_node = ox.distance.nearest_nodes(G, proj_points.x[0], proj_points.y[0])

    min_dist = inf
    for node in tqdm(list(G.nodes)):
        dist = math.sqrt((lat - G.nodes[node]['lat'])**2 + (lon - G.nodes[node]['lon'])**2)
        if dist < min_dist:
            min_dist = dist
            center_node = node

    hwy_speeds = {"footway": 4.5, "cycleway": 10, "residential": 35, "secondary": 50, "tertiary": 60}
    G = ox.add_edge_speeds(G, hwy_speeds)
    G = ox.add_edge_travel_times(G)

    node_distances = {}
    for node in tqdm(list(G.nodes)):
        route = ox.shortest_path(G, center_node, node, weight="travel_time", cpus=cpus)
        try:
            node_distances[node] = int(sum(ox.utils_graph.get_route_edge_attributes(G, route, "travel_time")))
        except:
            pass

    bird_distances = {}
    for node in tqdm(list(G.nodes)):
        bird_distances[node] = math.sqrt((G.nodes[center_node]['x'] - G.nodes[node]['x'])**2 + (G.nodes[center_node]['y'] - G.nodes[node]['y'])**2)

    bd_avg = sum(list(bird_distances.values()))/len(list(bird_distances.keys()))
    nd_avg = sum(list(node_distances.values()))/len(list(node_distances.keys()))
    scale_factor = bd_avg/nd_avg

    for node in tqdm(list(G.nodes)):
        if (node_distances.get(node) and G.nodes.get(node, None) is not None):
            #dlat = (G.nodes[center_node]['lat'] - G.nodes[node]['lat'])
            #dlon = (G.nodes[center_node]['lon'] - G.nodes[node]['lon'])
            dy = (G.nodes[center_node]['y'] - G.nodes[node]['y'])
            dx = (G.nodes[center_node]['x'] - G.nodes[node]['x'])
            scale = scale_factor * (node_distances.get(node)/bird_distances.get(node)) 
            new_x = G.nodes[center_node]['x']-(scale*dx)
            new_y = G.nodes[center_node]['y']-(scale*dy)
            #new_lat = G.nodes[center_node]['lat']+(scale*dlat)
            #new_lon = G.nodes[center_node]['lon']+(scale*dlon)
            G.nodes[node].update({ 
                                'street_count': G.nodes[node]['street_count'],
                                'x' : new_x,
                                'y' : new_y,
                                })
        elif node == center_node:
            continue
        else:
            G.remove_node(node)

    for edge in tqdm(list(G.edges)):
        t_dict = dict(G.edges[edge])
        x1 = G.nodes[edge[0]]['x']
        y1 = G.nodes[edge[0]]['y']
        x2 = G.nodes[edge[1]]['x']
        y2 = G.nodes[edge[1]]['y']
        t_dict['geometry'] = LineString([(x1,y1),(x2,y2)])
        G.edges[edge].update(t_dict)    

    cut = int(len(G.nodes)*pct_extremes)
    x_sort = [G.nodes[n]['x'] for n in G.nodes]
    x_sort.sort()
    y_sort = [G.nodes[n]['y'] for n in G.nodes]
    y_sort.sort()

    max_x = x_sort[min(-1,cut * -1)]
    min_x = x_sort[cut]
    max_y = y_sort[min(-1,cut * -1)]
    min_y = y_sort[cut]

    trip_times = [x * iso_factor * iso_mins for x in range(1, isos + 1)]
    iso_colors = ox.plot.get_colors(n=len(trip_times), cmap='plasma', start=0, return_hex=True)

    node_colors = {}
    for trip_time, color in zip(sorted(trip_times, reverse=True), iso_colors):
        subgraph = nx.ego_graph(G, center_node, radius=trip_time, distance='travel_time')
        for node in subgraph.nodes():
            node_colors[node] = color
    nc = [node_colors[node] if node in node_colors else 'none' for node in G.nodes()]

    fig, ax = ox.plot_graph(G, bgcolor='w', node_color=nc, node_size=node_size, node_alpha=0.8, node_zorder=2, edge_linewidth = 0.2, bbox = (max_y, min_y, max_x, min_x))

    fig.savefig(output_loc, dpi=300, bbox_inches='tight')
    

    

if __name__ == "__main__":
    main()