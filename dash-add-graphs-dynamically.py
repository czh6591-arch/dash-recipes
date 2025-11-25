import dash
from dash.dependencies import Input, Output, State
from dash import html
from dash import dcc
import plotly.graph_objs as go
import json

app = dash.Dash()

app.layout = html.Div([
    # 图表管理操作区域
    html.Div([
        html.Button(id='add-graph-btn', n_clicks=0, children='新增图表'),
        html.Button(id='delete-graph-btn', n_clicks=0, children='删除当前选中图表'),
        html.Div(id='graph-count', children='当前图表数量: 0'),
    ], style={'marginBottom': '20px', 'display': 'flex', 'gap': '10px', 'alignItems': 'center'}),
    
    # 图表容器
    html.Div(id='container'),
    
    # 隐藏的元素用于存储状态
    html.Div(id='selected-graph', style={'display': 'none'}),
    html.Div(id='graph-data', style={'display': 'none'}, children=json.dumps([])),
    html.Div(id='filter-state', style={'display': 'none'}, children=json.dumps({})),
    html.Div(id='callback-history', style={'display': 'none'}, children=json.dumps([]))
])


@app.callback(
    [Output('container', 'children'),
     Output('graph-count', 'children'),
     Output('graph-data', 'children')],
    [Input('add-graph-btn', 'n_clicks'),
     Input('delete-graph-btn', 'n_clicks')],
    [State('container', 'children'),
     State('graph-data', 'children'),
     State('selected-graph', 'children')]
)
def manage_graphs(add_clicks, delete_clicks, current_graphs, graph_data_json, selected_graph):
    # 解析现有图表数据
    graph_data = json.loads(graph_data_json) if graph_data_json else []
    
    # 确定触发事件的按钮
    ctx = dash.callback_context
    if not ctx.triggered:
        return current_graphs, '当前图表数量: 0', json.dumps([])
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'add-graph-btn':
        # 添加新图表
        new_graph_id = f'graph-{len(graph_data)}'
        new_graph_data = {
            'id': new_graph_id,
            'x': [1, 2, 3, 4, 5],
            'y': [3, 1, 2, 5, 4],
            'title': f'Graph {len(graph_data)}'
        }
        graph_data.append(new_graph_data)
    
    elif button_id == 'delete-graph-btn' and selected_graph and graph_data:
        # 删除选中的图表
        graph_data = [g for g in graph_data if g['id'] != selected_graph]
        # 更新剩余图表的ID和标题
        for i, g in enumerate(graph_data):
            g['id'] = f'graph-{i}'
            g['title'] = f'Graph {i}'
    
    # 生成新的图表组件
    graphs = []
    for g in graph_data:
        # 为选中的图表添加高亮边框
        border_style = {'border': '3px solid #1f77b4'} if g['id'] == selected_graph else {}
        graphs.append(html.Div(
            dcc.Graph(
                id=g['id'],
                figure={
                    'data': [go.Scatter(x=g['x'], y=g['y'], mode='markers+lines')],
                    'layout': {
                        'title': g['title'],
                        'clickmode': 'event+select'
                    }
                }
            ),
            style=border_style
        ))
    
    # 更新图表数量显示
    graph_count = f'当前图表数量: {len(graph_data)}'
    
    return html.Div(graphs), graph_count, json.dumps(graph_data)


@app.callback(
    Output('selected-graph', 'children'),
    [Input('container', 'children')],  # 监听图表容器的变化
    [State('selected-graph', 'children')]
)
def update_selected_graph(container_children, current_selected):
    # 确定触发事件的图表
    ctx = dash.callback_context
    if not ctx.triggered:
        return current_selected
    
    # 检查触发事件是否来自图表的点击或选择
    triggered_prop = ctx.triggered[0]['prop_id']
    if '.clickData' in triggered_prop or '.selectedData' in triggered_prop:
        graph_id = triggered_prop.split('.')[0]
        return graph_id
    
    return current_selected


@app.callback(
    [Output('graph-data', 'children', allow_duplicate=True),
     Output('filter-state', 'children')],
    Input('container', 'children'),  # 监听图表容器的变化
    [State('graph-data', 'children'),
     State('filter-state', 'children'),
     State('callback-history', 'children')],
    prevent_initial_call=True
)
def update_graphs_on_relayout(container_children, graph_data_json, filter_state_json, callback_history_json):
    # 解析输入数据
    graph_data = json.loads(graph_data_json) if graph_data_json else []
    filter_state = json.loads(filter_state_json) if filter_state_json else {}
    callback_history = json.loads(callback_history_json) if callback_history_json else []
    
    if not graph_data:
        return json.dumps(graph_data), json.dumps(filter_state)
    
    # 确定触发事件的图表
    ctx = dash.callback_context
    if not ctx.triggered:
        return json.dumps(graph_data), json.dumps(filter_state)
    
    # 检查触发事件是否来自图表的relayoutData
    triggered_prop = ctx.triggered[0]['prop_id']
    if '.relayoutData' not in triggered_prop:
        return json.dumps(graph_data), json.dumps(filter_state)
    
    triggered_graph_id = triggered_prop.split('.')[0]
    relayout_data = ctx.triggered[0]['value']
    
    # 检查循环依赖
    if len(callback_history) >= 2 and callback_history[-1] == triggered_graph_id and callback_history[-2] == triggered_graph_id:
        # 检测到循环，降级为单向联动
        print(f'检测到循环依赖，已降级为单向联动模式。触发图表: {triggered_graph_id}')
        return json.dumps(graph_data), json.dumps(filter_state)
    
    # 更新回调历史
    callback_history.append(triggered_graph_id)
    if len(callback_history) > 2:
        callback_history.pop(0)  # 只保留最近两次回调
    
    # 提取筛选条件（这里假设是x轴范围）
    if 'xaxis.range[0]' in relayout_data and 'xaxis.range[1]' in relayout_data:
        x_range = [relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]']]
        filter_state[triggered_graph_id] = {'x_range': x_range}
        
        # 更新所有图表的数据范围
        for g in graph_data:
            if g['id'] != triggered_graph_id:
                # 过滤数据点
                filtered_x = []
                filtered_y = []
                for x, y in zip(g['x'], g['y']):
                    if x >= x_range[0] and x <= x_range[1]:
                        filtered_x.append(x)
                        filtered_y.append(y)
                g['x'] = filtered_x
                g['y'] = filtered_y
    
    return json.dumps(graph_data), json.dumps(filter_state)


if __name__ == '__main__':
    app.run(debug=True)
