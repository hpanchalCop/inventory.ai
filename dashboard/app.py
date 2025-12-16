"""Plotly Dash Admin Dashboard for inventory.ai."""
import dash
from dash import dcc, html, dash_table, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests
from datetime import datetime
from typing import List, Dict, Optional
import io
import base64
from PIL import Image
import json
from urllib.parse import urlencode

from shared.config import settings

# Initialize Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="Inventory.AI Dashboard",
    suppress_callback_exceptions=True,
    ##url_base_pathname='/dashboard/'
    url_base_pathname='/'
)

# API base URL
API_URL = f"http://localhost:{settings.api_port}"

# Auth0 Configuration
AUTH0_DOMAIN = settings.auth0_domain
AUTH0_CLIENT_ID = getattr(settings, 'auth0_client_id', 'pzavIBiATNt20mTgnqRSlAxQDh88uPgl')
AUTH0_CALLBACK_URL = f"http://localhost:{settings.dashboard_port}/callback"
AUTH0_AUDIENCE = settings.auth0_api_audience


def get_auth0_login_url() -> str:
    """Generate Auth0 login URL."""
    params = {
        'response_type': 'token',
        'client_id': AUTH0_CLIENT_ID,
        'redirect_uri': AUTH0_CALLBACK_URL,
        'scope': 'openid profile email',
        'audience': AUTH0_AUDIENCE
    }
    return f"https://{AUTH0_DOMAIN}/authorize?{urlencode(params)}"


def get_auth0_logout_url() -> str:
    """Generate Auth0 logout URL."""
    params = {
        'client_id': AUTH0_CLIENT_ID,
        'returnTo': f"http://localhost:{settings.dashboard_port}"
    }
    return f"https://{AUTH0_DOMAIN}/v2/logout?{urlencode(params)}"


def fetch_products() -> List[Dict]:
    """Fetch all products from API."""
    try:
        response = requests.get(f"{API_URL}/products")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error fetching products: {e}")
        return []


def fetch_api_stats() -> Dict:
    """Fetch API usage statistics."""
    try:
        response = requests.get(f"{API_URL}/admin/stats")
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return {}


def create_product_with_auth(data: Dict, token: str) -> requests.Response:
    """Create product with authentication."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.post(f"{API_URL}/products/text-only", json=data, headers=headers)


def delete_product_with_auth(product_id: int, token: str) -> requests.Response:
    """Delete product with authentication."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.delete(f"{API_URL}/products/{product_id}", headers=headers)


def create_product_table(products: List[Dict]) -> dash_table.DataTable:
    """Create product data table."""
    if not products:
        return dash_table.DataTable(
            id='product-table',
            columns=[],
            data=[],
            style_table={'overflowX': 'auto'}
        )
    
    df = pd.DataFrame(products)
    
    # Select and format columns
    display_columns = ['id', 'name', 'description', 'category', 'price', 'image_url']
    df = df[[col for col in display_columns if col in df.columns]]
    
    columns = [{"name": col.replace('_', ' ').title(), "id": col} for col in df.columns]
    
    return dash_table.DataTable(
        id='product-table',
        columns=columns,
        data=df.to_dict('records'),
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'whiteSpace': 'normal',
            'height': 'auto',
        },
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }
        ]
    )


def create_category_chart(products: List[Dict]) -> dcc.Graph:
    """Create category distribution chart."""
    if not products:
        return dcc.Graph(id='category-chart', figure={})
    
    df = pd.DataFrame(products)
    
    if 'category' not in df.columns or df['category'].isna().all():
        fig = go.Figure()
        fig.add_annotation(text="No category data available", showarrow=False)
        return dcc.Graph(id='category-chart', figure=fig)
    
    category_counts = df['category'].value_counts()
    
    fig = px.pie(
        values=category_counts.values,
        names=category_counts.index,
        title='Products by Category'
    )
    
    return dcc.Graph(id='category-chart', figure=fig)


def create_price_chart(products: List[Dict]) -> dcc.Graph:
    """Create price distribution chart."""
    if not products:
        return dcc.Graph(id='price-chart', figure={})
    
    df = pd.DataFrame(products)
    
    if 'price' not in df.columns or df['price'].isna().all():
        fig = go.Figure()
        fig.add_annotation(text="No price data available", showarrow=False)
        return dcc.Graph(id='price-chart', figure=fig)
    
    fig = px.histogram(
        df,
        x='price',
        title='Price Distribution',
        nbins=20
    )
    
    return dcc.Graph(id='price-chart', figure=fig)


# Layout
app.layout = dbc.Container([
    # URL Location for handling Auth0 callback
    dcc.Location(id='url', refresh=False),
    
    # Store for authentication token
    dcc.Store(id='auth-token-store', storage_type='session'),
    
    # Header with Auth
    dbc.Row([
        dbc.Col([
            html.H1("Inventory.AI Admin Dashboard", className="text-center my-4"),
        ], width=8),
        dbc.Col([
            html.Div(id='auth-status', className="text-end my-4")
        ], width=4),
    ]),
    html.Hr(),
    
    # Auth Alert
    html.Div(id='auth-alert'),
    
    # Statistics Row
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Total Products", className="card-title"),
                    html.H2(id="total-products", className="text-primary")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Categories", className="card-title"),
                    html.H2(id="total-categories", className="text-success")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Avg Price", className="card-title"),
                    html.H2(id="avg-price", className="text-info")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("With Images", className="card-title"),
                    html.H2(id="with-images", className="text-warning")
                ])
            ])
        ], width=3),
    ], className="mb-4"),
    
    # Add Product Form
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("Add New Product")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Product Name"),
                            dbc.Input(id="input-name", type="text", placeholder="Enter product name")
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Category"),
                            dbc.Input(id="input-category", type="text", placeholder="Enter category")
                        ], width=6),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Price"),
                            dbc.Input(id="input-price", type="number", placeholder="Enter price")
                        ], width=6),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Description"),
                            dbc.Textarea(id="input-description", placeholder="Enter product description", rows=3)
                        ])
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button("Add Product (Text Only)", id="btn-add-product", color="primary", className="me-2"),
                            html.Div(id="add-product-output", className="mt-2")
                        ])
                    ])
                ])
            ])
        ])
    ], className="mb-4"),
    
    # Charts Row
    dbc.Row([
        dbc.Col([
            html.Div(id="category-chart-container")
        ], width=6),
        dbc.Col([
            html.Div(id="price-chart-container")
        ], width=6),
    ], className="mb-4"),
    
    # Products Table
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H4("Product Inventory", className="d-inline"),
                    dbc.Button("Refresh", id="btn-refresh", color="secondary", size="sm", className="float-end")
                ]),
                dbc.CardBody([
                    html.Div(id="table-container")
                ])
            ])
        ])
    ], className="mb-4"),
    
    # API Usage Statistics Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H4("API Usage Statistics", className="d-inline"),
                    dbc.Button("Refresh Stats", id="btn-refresh-stats", color="info", size="sm", className="float-end")
                ]),
                dbc.CardBody([
                    html.Div(id="api-stats-container")
                ])
            ])
        ])
    ]),
    
    # Interval component for auto-refresh
    dcc.Interval(
        id='interval-component',
        interval=30*1000,  # 30 seconds
        n_intervals=0
    ),
    
    # Store component for product data
    dcc.Store(id='product-data-store')
    
], fluid=True)


# Callbacks

# Auth0 callback handler - extracts token from URL hash
app.clientside_callback(
    """
    function(href) {
        if (href && href.includes('access_token=')) {
            const hashParams = new URLSearchParams(href.split('#')[1]);
            const token = hashParams.get('access_token');
            if (token) {
                // Clear the URL hash
                window.history.replaceState({}, document.title, window.location.pathname);
                return token;
            }
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('auth-token-store', 'data'),
    Input('url', 'href')
)


@app.callback(
    Output('auth-status', 'children'),
    Input('auth-token-store', 'data')
)
def update_auth_status(token):
    """Update authentication status display."""
    if token:
        return html.Div([
            dbc.Badge("Authenticated", color="success", className="me-2"),
            dbc.Button("Logout", id="btn-logout", color="outline-danger", size="sm", href=get_auth0_logout_url())
        ])
    else:
        return dbc.Button("Login with Auth0", id="btn-login", color="primary", size="sm", href=get_auth0_login_url())


@app.callback(
    Output('auth-alert', 'children'),
    Input('auth-token-store', 'data')
)
def show_auth_alert(token):
    """Show alert about authentication status."""
    if not token:
        return dbc.Alert([
            html.I(className="bi bi-info-circle me-2"),
            "You are not logged in. ",
            html.A("Login", href=get_auth0_login_url(), className="alert-link"),
            " to add or delete products."
        ], color="info", dismissable=True, className="mb-3")
    return None


@app.callback(
    Output('product-data-store', 'data'),
    [Input('btn-refresh', 'n_clicks'),
     Input('interval-component', 'n_intervals'),
     Input('btn-add-product', 'n_clicks')],
    prevent_initial_call=False
)
def update_product_data(refresh_clicks, n_intervals, add_clicks):
    """Fetch and store product data."""
    products = fetch_products()
    return products


@app.callback(
    [Output('table-container', 'children'),
     Output('category-chart-container', 'children'),
     Output('price-chart-container', 'children'),
     Output('total-products', 'children'),
     Output('total-categories', 'children'),
     Output('avg-price', 'children'),
     Output('with-images', 'children')],
    Input('product-data-store', 'data')
)
def update_dashboard(products):
    """Update all dashboard components."""
    if not products:
        return (
            html.P("No products found"),
            dcc.Graph(figure={}),
            dcc.Graph(figure={}),
            "0",
            "0",
            "$0",
            "0"
        )
    
    df = pd.DataFrame(products)
    
    # Create components
    table = create_product_table(products)
    category_chart = create_category_chart(products)
    price_chart = create_price_chart(products)
    
    # Calculate statistics
    total_products = len(products)
    total_categories = df['category'].nunique() if 'category' in df.columns else 0
    avg_price = f"${df['price'].mean():.2f}" if 'price' in df.columns and not df['price'].isna().all() else "$0"
    with_images = df['image_url'].notna().sum() if 'image_url' in df.columns else 0
    
    return (
        table,
        category_chart,
        price_chart,
        str(total_products),
        str(total_categories),
        avg_price,
        str(with_images)
    )


@app.callback(
    Output('add-product-output', 'children'),
    Input('btn-add-product', 'n_clicks'),
    [State('input-name', 'value'),
     State('input-description', 'value'),
     State('input-category', 'value'),
     State('input-price', 'value'),
     State('auth-token-store', 'data')],
    prevent_initial_call=True
)
def add_product(n_clicks, name, description, category, price, token):
    """Add new product via API (requires authentication)."""
    if not token:
        return dbc.Alert([
            "Authentication required. Please ",
            html.A("login", href=get_auth0_login_url()),
            " to add products."
        ], color="warning")
    
    if not name or not description:
        return dbc.Alert("Name and description are required", color="danger")
    
    try:
        data = {
            "name": name,
            "description": description,
            "category": category,
            "price": float(price) if price else None
        }
        
        response = create_product_with_auth(data, token)
        
        if response.status_code == 200:
            return dbc.Alert("Product added successfully!", color="success")
        elif response.status_code == 401:
            return dbc.Alert("Authentication expired. Please login again.", color="warning")
        else:
            return dbc.Alert(f"Error: {response.text}", color="danger")
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger")


@app.callback(
    Output('api-stats-container', 'children'),
    [Input('btn-refresh-stats', 'n_clicks'),
     Input('interval-component', 'n_intervals')],
    prevent_initial_call=False
)
def update_api_stats(n_clicks, n_intervals):
    """Update API usage statistics display."""
    stats = fetch_api_stats()
    
    if not stats:
        return dbc.Alert("Could not fetch API statistics. Make sure the API is running.", color="warning")
    
    # Check if we have placeholder data
    if stats.get('note'):
        return dbc.Alert(stats['note'], color="info")
    
    total_requests = stats.get('total_requests', {})
    requests_by_endpoint = stats.get('requests_by_endpoint', {})
    requests_by_method = stats.get('requests_by_method', {})
    response_times = stats.get('response_times', {})
    errors = stats.get('errors', {})
    
    return html.Div([
        dbc.Row([
            # Request counts by time period
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Requests by Time Period"),
                    dbc.CardBody([
                        html.P([html.Strong("Last Hour: "), f"{total_requests.get('last_hour', 0)}"]),
                        html.P([html.Strong("Last 24 Hours: "), f"{total_requests.get('last_24_hours', 0)}"]),
                        html.P([html.Strong("Last 7 Days: "), f"{total_requests.get('last_7_days', 0)}"]),
                    ])
                ])
            ], width=4),
            
            # Response times
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Response Times"),
                    dbc.CardBody([
                        html.P([
                            html.Strong("Average: "), 
                            f"{response_times.get('average_ms', 0):.2f} ms" if isinstance(response_times.get('average_ms', 0), (int, float)) else str(response_times.get('average_ms', 'N/A'))
                        ]),
                        html.P([
                            html.Strong("Max: "), 
                            f"{response_times.get('max_ms', 0):.2f} ms" if isinstance(response_times.get('max_ms', 0), (int, float)) else str(response_times.get('max_ms', 'N/A'))
                        ]),
                        html.Small(response_times.get('note', ''), className="text-muted") if 'note' in response_times else None
                    ])
                ])
            ], width=4),
            
            # Error rates
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Errors (24h)"),
                    dbc.CardBody([
                        html.P([html.Strong("Error Count: "), f"{errors.get('count_24h', 0)}"]),
                        html.P([html.Strong("Error Rate: "), f"{errors.get('error_rate_percent', 0):.2f}%"]),
                    ])
                ])
            ], width=4),
        ], className="mb-3"),
        
        dbc.Row([
            # Requests by endpoint
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Requests by Endpoint"),
                    dbc.CardBody([
                        html.Ul([
                            html.Li(f"{endpoint}: {count}")
                            for endpoint, count in requests_by_endpoint.items()
                        ]) if requests_by_endpoint else html.P("No endpoint data available")
                    ])
                ])
            ], width=6),
            
            # Requests by HTTP method
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Requests by Method"),
                    dbc.CardBody([
                        html.Ul([
                            html.Li(f"{method}: {count}")
                            for method, count in requests_by_method.items()
                        ]) if requests_by_method else html.P("No method data available")
                    ])
                ])
            ], width=6),
        ]),
        
        html.Small(f"Generated at: {stats.get('generated_at', 'N/A')}", className="text-muted mt-2")
    ])


if __name__ == '__main__':
    app.run_server(
        host=settings.dashboard_host,
        port=settings.dashboard_port,
        debug=True
    )
