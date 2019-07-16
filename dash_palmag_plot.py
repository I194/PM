# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table

import plotly.graph_objs as go

import pandas as pd
import numpy as np

import base64
import io
import os


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.config['suppress_callback_exceptions']=True

app.layout = html.Div([
    html.H4(children='Current data'),
    dcc.Upload(
        id = '  upload-data',
        children=html.Div([
            html.A('Select'),
            ' or drop file'
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
            multiple=False
    ),
    dcc.RadioItems(
        id = 'system-pm',
        options=[
            {'label': u'Geographic', 'value': 'new'},
            {'label': 'Stratigraphic', 'value': 'old'}
        ],
        value='new',
        labelStyle={'display': 'inline-block'}
    ),
    dash_table.DataTable(id = 'datatable-upload-container'),
    html.Div([dcc.Graph(id='polar-scatter-pm')],
             style={'width': '33%', 'display': 'inline-block'}),
    html.Div([dcc.Graph(id='MAG-scatter-pm')],
             style={'width': '33%', 'display': 'inline-block'}),
    html.Div([dcc.Graph(id='xyz-scatter-pm')],
             style={'width': '33%', 'display': 'inline-block'}),
    html.Div(id='output-datatable')
])


def column_cleaner(string):
    while len(string) and not (string[0] >= "0" and string[0] <= "9"):
        string = string[1:]
    return string


def transform_data(raw_table):
    tmp_data = raw_table
    tmp_data.to_csv("TMP")

    data = pd.read_csv("TMP", header=None)

    os.remove("TMP")

    i = 0
    while (data.iloc[i][1][:4] != " PAL"):
        i += 1
    a = []
    for j in range(i + 1):
        a.append(j)
    data.drop(a, axis=0, inplace=True)

    tmp_tb = []
    for i in data[1]:
        tmp_tb.append(i.split())

    data = pd.DataFrame(tmp_tb)

    test = data[0]

    Col1Measure = "T"

    if data[0][0][0] == "M":
        Col1Measure = "M"

    data[0] = list(map(column_cleaner, test))
    data.drop(len(data) - 1, axis=0, inplace=True)

    data.rename(
        columns={0: Col1Measure, 1: "X", 2: "Y", 3: "Z", 4: "MAG", 5: "D", 6: "I", 7: "D_old", 8: "I_old", 9: "a95"},
        inplace=True)

    for i in data.columns:
        data[i] = pd.to_numeric(data[i])

    return data, Col1Measure


def parse_contents_and_give_csv(contents, filename):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    return pd.read_csv(io.StringIO(decoded.decode('utf-8')))


def parse_contents_for_plot_dt(contents, filename):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    raw_df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    df, first_col_name=transform_data(raw_df)

    return html.Div([
        html.H5(filename),

        dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[{'name': i, 'id': i} for i in df.columns]
        ),

        html.Hr()
    ])


@app.callback(
    dash.dependencies.Output('datatable-upload-container', 'data'),
    [dash.dependencies.Input('upload-data', 'contents')],
    [dash.dependencies.State('upload-data', 'filename')]
)
def update_dt(contents, filename):
    if contents is None:
        return [{}]
    tmp_df = parse_contents_and_give_csv(contents, filename)
    df, coltmp = transform_data(tmp_df)
    return df.to_dict('records')


@app.callback(
    dash.dependencies.Output('polar-scatter-pm', 'figure'),
    [dash.dependencies.Input('system-pm', 'value'),
     dash.dependencies.Input('datatable-upload-container', 'data')]
)
def update_graph_polar_pm(system_name, data):
    df = pd.DataFrame(data)

    axdots_r = []
    axdots_a = []
    for i in [0, 90, 180, 270]:
        for j in range(10, 90, 10):
            axdots_r.append(j)
            axdots_a.append(i)

    if df.empty:
        df = pd.DataFrame({'T':[], 'X':[], 'Y':[], 'Z':[], 'MAG':[], 'D':[], 'I':[], 'D_old':[], 'I_old':[], 'a95':[]})
        return {
            'data': [
                go.Scatterpolar(
                    r=axdots_r,
                    theta=axdots_a,
                    mode="markers",
                    marker=dict(
                        color='black',
                        size=3
                    )
                ),
                go.Scatterpolar(
                    r=[0],
                    theta=[0],
                    mode="markers",
                    marker=dict(
                        color='black',
                        size=10,
                        symbol="cross-thin-open"
                    )
                )
            ],
            'layout': go.Layout(
                title="Polar plot",
                font=dict(
                    family="Times New Roman",
                    size=25,
                    color="black"
                ),
                width=550,
                height=550,
                showlegend=False,
                hovermode='closest',
                polar=dict(
                    angularaxis=dict(
                        tickfont=dict(
                            size=25,
                            family="Times New Roman"
                        ),
                        rotation=90,
                        direction="clockwise",
                        dtick=90,
                        tickmode="array",
                        tickvals=[0, 90, 180, 270],
                        ticktext=["N", "E", "S", "W"],
                        ticksuffix=0,
                        showgrid=False
                    ),
                    radialaxis=dict(
                        range=[0, 90],
                        visible=False
                    )
                )
            )
        }

    col_D = "D"
    col_I = "I"

    if system_name == "old":
        col_D = "D_old"
        col_I = "I_old"

    angles_neg = []
    angles_pos = []
    values_neg = []
    values_pos = []
    values_abs = list(abs(df[col_I]))
    angles_abs = list(abs(df[col_D]))

    for i in range(0, len(df[col_I]), 1):
        if df[col_I][i] < 0:
            values_neg.append(abs(df[col_I][i]))
            angles_neg.append(df[col_D][i])
        else:
            values_pos.append(df[col_I][i])
            angles_pos.append(df[col_D][i])

    return {
        'data': [
            go.Scatterpolar(
                r=axdots_r,
                theta=axdots_a,
                mode="markers",
                marker=dict(
                    color='black',
                    size=3
                )
            ),
            go.Scatterpolar(
                r=[0],
                theta=[0],
                mode="markers",
                marker=dict(
                    color='black',
                    size=10,
                    symbol="cross-thin-open"
                )
            ),
            go.Scatterpolar(
                r=values_abs,
                theta=angles_abs,
                mode='lines',
                line=dict(
                    color='black',
                    width=1
                )
            ),
            go.Scatterpolar(
                r=values_pos,
                theta=angles_pos,
                mode="markers",
                marker=dict(
                    color='black',
                    size=8,
                ),
            ),
            go.Scatterpolar(
                r=values_neg,
                theta=angles_neg,
                mode="markers",
                marker=dict(
                    color='white',
                    size=8,
                    line=dict(
                        color='black',
                        width=1
                    )
                )
            )
        ],
        'layout': go.Layout(
            title="Polar plot",
            font=dict(
                family="Times New Roman",
                size=25,
                color="black"
            ),
            width=550,
            height=550,
            showlegend=False,
            hovermode='closest',
            polar=dict(
                angularaxis=dict(
                    tickfont=dict(
                        size=25,
                        family="Times New Roman"
                    ),
                    rotation=90,
                    direction="clockwise",
                    dtick=90,
                    tickmode="array",
                    tickvals=[0, 90, 180, 270],
                    ticktext=["N", "E", "S", "W"],
                    ticksuffix=0,
                    showgrid=False
                ),
                radialaxis=dict(
                    range=[0, 90],
                    visible=False
                )
            )
        )
    }


@app.callback(
    dash.dependencies.Output('MAG-scatter-pm', 'figure'),
    [dash.dependencies.Input('datatable-upload-container', 'data')]
)
def update_graph_intensity(data):
    print("test1")
    df = pd.DataFrame(data)

    relative_mag = []
    first_col = []

    if df.empty:
        return {
            'data': [
                go.Scatter(
                    x=first_col,
                    y=relative_mag,
                    mode='lines',
                )
            ],
            'layout': go.Layout(
                title="Intensity plot",
                font=dict(
                    family="Times New Roman",
                    size=25,
                    color="black"
                ),
                showlegend=False,
            )
        }

    for i in df.MAG:
        relative_mag.append(i / max(df.MAG))

    first_col_name = "T"

    if "M" in data[0]:
        first_col_name = "M"

    for i in df[first_col_name]:
        first_col.append(i)

    return {
        'data': [
            go.Scatter(
                x=first_col,
                y=relative_mag,
                mode='lines',
                line=dict(
                    color='black',
                    width=1
                )
            ),
            go.Scatter(
                x=first_col,
                y=relative_mag,
                mode="markers",
                marker=dict(
                    color='white',
                    size=8,
                    line=dict(
                        color='black',
                        width=1
                    )
                )
            )
        ],
        'layout': go.Layout(
            title="Intensity plot",
            font=dict(
                family="Times New Roman",
                size=25,
                color="black"
            ),
            xaxis={'title': r'$^{\circ}C$'},
            yaxis={'title': r'$M/M_{max}, M_{max}=$' + str(max(df.MAG)) + ' A/m'},
            showlegend=False,
            grid=dict(
                xside='bottom plot',
                yside='left',
            )
        )
    }


@app.callback(
    dash.dependencies.Output('xyz-scatter-pm', 'figure'),
    [dash.dependencies.Input('datatable-upload-container', 'data')]
)
def update_graph_xyz(data):
    print("test2")
    df = pd.DataFrame(data)

    if df.empty:
        return {
            'data': [
                go.Scatter(
                    x=[0,0],
                    y=[0,0],
                    mode='lines'
                )
            ],
            'layout': go.Layout(
                title="Zyiderveld plot",
                font=dict(
                    family="Times New Roman",
                    size=25,
                    color="black"
                ),
                showlegend=False,
            )
        }

    left_x = df['X']
    left_y = df['Y']
    left_z = []

    right_x = df['X']
    right_y = []
    right_z = df['Z']

    for i in range(len(df['Z'])):
        left_z.append(0)
        right_y.append(0)

    return {
        'data': [
            go.Scatter(
                x=left_y,
                y=left_x ,
                mode="lines+markers",
                marker=dict(
                    color='white',
                    size = 8,
                    line = dict(
                        color='black',
                        width=1
                    )
                ),
                line = dict(
                    color = 'black',
                    width = 1
                )
            ),
            go.Scatter(
                x = right_z,
                y = right_x,
                mode = 'lines+markers',
                marker = dict(
                    color = 'black',
                    size = 8
                ),
                line=dict(
                    color = 'black',
                    width = 1
                )
            )
        ],
        'layout': go.Layout(
            title="Ziyderveld plot",
            font=dict(
                family="Times New Roman",
                size=25,
                color="black"
            ),
            showlegend=False
        )
    }


@app.callback(dash.dependencies.Output('output-datatable', 'children'),
              [dash.dependencies.Input('upload-data', 'contents')],
              [dash.dependencies.State('upload-data', 'filename')]
)
def update_output_datatable(list_of_contents, list_of_names):
    if list_of_contents is not None:
        children = [parse_contents_for_plot_dt(list_of_contents, list_of_names)]
        return children
    else:
        df = pd.DataFrame({'T': [], 'X': [], 'Y': [], 'Z': [], 'MAG': [], 'D': [], 'I': [], 'D_old': [], 'I_old': [], 'a95': []})
        return html.Div([
            dash_table.DataTable(
                data=df.to_dict('records'),
                columns=[{'name': i, 'id': i} for i in df.columns]
            )
        ])


if __name__ == '__main__':
    app.run_server(debug=True)