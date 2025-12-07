"""Plotly Dash Admin Dashboard for inventory.ai."""
import dash
from dash import dcc, html, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests
from datetime import datetime
from typing import List, Dict
import io
import base64
from PIL import Image

from shared.config import settings

# Initialize Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="Inventory.AI Dashboard"
)

# API base URL
API_URL = f"http://localhost:{settings.api_port}"


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
    dbc.Row([
        dbc.Col([
            html.H1("Inventory.AI Admin Dashboard", className="text-center my-4"),
            html.Hr()
        ])
    ]),
    
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
     State('input-price', 'value')],
    prevent_initial_call=True
)
def add_product(n_clicks, name, description, category, price):
    """Add new product via API."""
    if not name or not description:
        return dbc.Alert("Name and description are required", color="danger")
    
    try:
        data = {
            "name": name,
            "description": description,
            "category": category,
            "price": float(price) if price else None
        }
        
        response = requests.post(f"{API_URL}/products/text-only", json=data)
        
        if response.status_code == 200:
            return dbc.Alert("Product added successfully!", color="success")
        else:
            return dbc.Alert(f"Error: {response.text}", color="danger")
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger")


if __name__ == '__main__':
    app.run_server(
        host=settings.dashboard_host,
        port=settings.dashboard_port,
        debug=True
    )
