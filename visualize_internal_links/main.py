import re
from xml.etree import ElementTree as ET
import networkx as nx
import plotly.graph_objects as go

# Constants
FILE_PATH = 'PUT_YOUR_WORDPRESS_EXPORT_FILE_HERE'
NAMESPACE = {'content': 'http://purl.org/rss/1.0/modules/content/'}
DOMAIN = "helpedbyanerd.com"

# Helper Functions
def get_text(element, path, default="No Title", namespace=None):
    """
    Extract text from an XML element with a given path and namespace.
    """
    return element.find(path, namespace).text if element.find(path, namespace) is not None else default

def is_internal_and_not_image(url):
    """
    Check if the URL is internal and not an image link.
    """
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4']
    return DOMAIN in url and not any(url.endswith(ext) for ext in image_extensions)

# Main Functions
def extract_content(tree):
    """
    Extracts articles, their internal links, and mappings from a WordPress export XML file.
    """
    root = tree.getroot()
    articles_internal_links = {}
    articles = {}

    for item in root.findall('.//item'):
        title = get_text(item, 'title')
        content = get_text(item, './/content:encoded', default="", namespace=NAMESPACE)
        link = get_text(item, 'link', default="No Link")

        # Process internal links
        urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
        internal_urls = [url for url in urls if is_internal_and_not_image(url) and "empfiehlt" not in url] # to remove affiliate links

        articles_internal_links[title] = internal_urls
        articles[link] = title

    return articles_internal_links, articles

def create_network_graph(data):
    """
    Create and visualize a network graph from given data.
    """
    G = nx.DiGraph()
    for article, urls in data.items():
        G.add_node(article, type='article')
        for url in urls:
            if url not in G:
                G.add_node(url, type='url')
            G.add_edge(article, url)

    # Visualization
    pos = nx.spring_layout(G)
    edge_trace, node_trace = build_traces(G, pos)
    fig = build_figure(edge_trace, node_trace)
    fig.show()

def build_traces(G, pos):
    """
    Build edge and node traces for Plotly visualization.
    """
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=0.5, color='#888'), hoverinfo='none', mode='lines')

    node_x, node_y, node_adjacencies, node_text = [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        adjacencies = list(G.adj[node])
        node_adjacencies.append(len(adjacencies))
        node_text.append(f'{node}<br># of connections: {len(adjacencies)}')

    node_trace = go.Scatter(x=node_x, y=node_y, mode='markers+text', text=node_text, hoverinfo='text', marker=dict(showscale=True, colorscale='YlGnBu', color=node_adjacencies, size=10, colorbar=dict(title='Number of Connections'), line_width=2))

    return edge_trace, node_trace

def generate_mermaid_diagram(internal_links, mapping):
    """
    Generates a Mermaid graph diagram from internal links.

    Parameters:
    - internal_links: A dictionary where keys are article titles and values are lists of internal links.
    - mapping: A dictionary where keys are article links and values are the titles to those articles.

    Returns:
    A string representing the Mermaid diagram.
    """
    mermaid_graph = "graph TD;\n"
    article_ids = {title: f"A{index}" for index, title in enumerate(internal_links.keys())}

    for title, links in internal_links.items():
        source_id = article_ids[title]
        for link in links:
            link_title = mapping.get(link, "Unknown Article")  # Defaults to "Unknown Article" if not found
            if link_title in article_ids:
                target_id = article_ids[link_title]
                mermaid_graph += f"  {source_id}[\"{title}\"] --> {target_id}[\"{link_title}\"];\n"
    
    return mermaid_graph


def build_figure(edge_trace, node_trace):
    """
    Build the Plotly figure for the network graph.
    """
    return go.Figure(data=[edge_trace, node_trace],
                     layout=go.Layout(
                         title='Network Graph of Articles and URLs',
                         showlegend=False,
                         hovermode='closest',
                         xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                         yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                     ))



# Parse the XML file
tree = ET.parse(FILE_PATH)

# Extract content and mappings
articles_internal_links, mapping = extract_content(tree)


# For demonstration, limit to the first 5 articles
limited_data = {k: articles_internal_links[k] for k in list(articles_internal_links)[:5]}

without_duplicates =  {k: list(set(v)) for k, v in articles_internal_links.items()}

# Create and visualize the network graph / or create a mermaid string
create_network_graph(without_duplicates)
print("---------------")
print(articles_internal_links)
print("---------------")
mermaid_diagram = generate_mermaid_diagram(without_duplicates, mapping)
print(mermaid_diagram)