import dash
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import plotly.graph_objs as go
import json

app = dash.Dash()

# 全局变量用于跟踪图表状态
chart_count = 0
selected_chart = None
filter_state = {}
callback_history = []
MAX_HISTORY = 5  # 用于检测循环依赖的历史记录长度

app.layout = html.Div([
    # 图表管理操作区域
    html.Div([
        html.Button(id='add-chart-btn', n_clicks=0, children='新增图表', style={'marginRight': '10px'}),
        html.Button(id='delete-chart-btn', n_clicks=0, children='删除当前选中图表', style={'marginRight': '10px'}),
        html.Span(id='chart-count', children='当前图表数量: 0', style={'fontWeight': 'bold'})
    ], style={'marginBottom': '20px', 'padding': '10px', 'backgroundColor': '#f0f0f0', 'borderRadius': '5px'}),
    
    # 图表容器
    html.Div(id='chart-container'),
    
    # 隐藏的存储组件，用于跟踪图表状态
    dcc.Store(id='chart-state', data={'charts': [], 'selected_chart': None, 'filter_state': {}}),
    
    # 隐藏的空图表，用于获取默认的图表配置
    html.Div(dcc.Graph(id='empty-graph', figure={'data': []}), style={'display': 'none'})
])

# 生成新图表的函数
def generate_chart(chart_id, title, x_data=None, y_data=None):
    if x_data is None:
        x_data = [1, 2, 3, 4, 5]
    if y_data is None:
        y_data = [5, 3, 4, 2, 6]
    
    return dcc.Graph(
        id=chart_id,
        figure={
            'data': [go.Scatter(x=x_data, y=y_data, mode='lines+markers', name='Data')],
            'layout': {
                'title': title,
                'clickmode': 'event+select',
                'dragmode': 'select',
                'selectdirection': 'h',
                'margin': {'l': 40, 'r': 10, 't': 40, 'b': 40}
            }
        },
        style={'width': '48%', 'display': 'inline-block', 'margin': '1%', 'border': '1px solid #e0e0e0', 'borderRadius': '5px'}
    )

# 新增图表回调
@app.callback(
    Output('chart-state', 'data'),
    [Input('add-chart-btn', 'n_clicks')],
    [State('chart-state', 'data')]
)
def add_chart(n_clicks, current_state):
    if n_clicks == 0:
        return current_state
    
    # 更新图表状态
    new_state = current_state.copy()
    chart_id = f'chart-{len(new_state["charts"])}'
    new_state['charts'].append(chart_id)
    
    # 更新筛选状态
    new_state['filter_state'][chart_id] = {'x_range': None, 'y_range': None}
    
    return new_state

# 删除当前选中图表回调
@app.callback(
    Output('chart-state', 'data', allow_duplicate=True),
    [Input('delete-chart-btn', 'n_clicks')],
    [State('chart-state', 'data')],
    prevent_initial_call=True
)
def delete_chart(n_clicks, current_state):
    if n_clicks == 0 or not current_state['selected_chart']:
        return current_state
    
    # 更新图表状态
    new_state = current_state.copy()
    selected_id = new_state['selected_chart']
    
    # 删除选中的图表
    if selected_id in new_state['charts']:
        new_state['charts'].remove(selected_id)
        del new_state['filter_state'][selected_id]
        
    # 重置选中图表
    new_state['selected_chart'] = None if not new_state['charts'] else new_state['charts'][0]
    
    return new_state

# 渲染图表回调
@app.callback(
    Output('chart-container', 'children'),
    [Input('chart-state', 'data')]
)
def render_charts(state):
    if not state['charts']:
        return html.Div('暂无图表，请点击"新增图表"按钮添加。', style={'textAlign': 'center', 'padding': '50px', 'color': '#999'})
    
    charts = []
    for chart_id in state['charts']:
        # 检查是否有筛选状态
        filter_data = state['filter_state'].get(chart_id, {})
        x_range = filter_data.get('x_range')
        y_range = filter_data.get('y_range')
        
        # 生成图表数据
        x_data = [1, 2, 3, 4, 5]
        y_data = [5, 3, 4, 2, 6]
        
        # 根据筛选状态调整数据
        if x_range:
            x_data = [x for x in x_data if x_range[0] <= x <= x_range[1]]
            y_data = y_data[:len(x_data)]
        if y_range:
            # 这里简化处理，实际应该根据y值筛选
            pass
        
        chart = generate_chart(chart_id, f'图表 {chart_id.split("-")[1]}', x_data, y_data)
        charts.append(chart)
    
    return html.Div(charts)

# 更新图表数量显示回调
@app.callback(
    Output('chart-count', 'children'),
    [Input('chart-state', 'data')]
)
def update_chart_count(state):
    return f'当前图表数量: {len(state["charts"])}'

# 处理图表选择回调
@app.callback(
    Output('chart-state', 'data', allow_duplicate=True),
    [Input({'type': 'chart', 'index': dash.dependencies.ALL}, 'selectedData')],
    [State('chart-state', 'data')],
    prevent_initial_call=True
)
def handle_chart_selection(selected_data_list, current_state):
    global callback_history
    
    # 记录回调历史
    callback_history.append('handle_chart_selection')
    if len(callback_history) > MAX_HISTORY:
        callback_history.pop(0)
    
    # 检测循环依赖
    if callback_history.count('handle_chart_selection') > 2:
        print('检测到循环依赖，已自动降级为单向联动模式')
        return current_state
    
    # 找到触发选择的图表
    ctx = dash.callback_context
    if not ctx.triggered:
        return current_state
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # 更新选中图表
    new_state = current_state.copy()
    new_state['selected_chart'] = trigger_id
    
    # 获取选择的数据范围
    selected_data = next((d for d in selected_data_list if d is not None), None)
    if selected_data and 'range' in selected_data:
        x_range = selected_data['range']['x']
        new_state['filter_state'][trigger_id] = {'x_range': x_range, 'y_range': None}
        
        # 同步更新其他图表的筛选状态
        for chart_id in new_state['charts']:
            if chart_id != trigger_id:
                new_state['filter_state'][chart_id] = {'x_range': x_range, 'y_range': None}
    
    return new_state

# 处理图表点击回调（用于选择图表）
@app.callback(
    Output('chart-state', 'data', allow_duplicate=True),
    [Input({'type': 'chart', 'index': dash.dependencies.ALL}, 'clickData')],
    [State('chart-state', 'data')],
    prevent_initial_call=True
)
def handle_chart_click(click_data_list, current_state):
    # 找到触发点击的图表
    ctx = dash.callback_context
    if not ctx.triggered:
        return current_state
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # 更新选中图表
    new_state = current_state.copy()
    new_state['selected_chart'] = trigger_id
    
    return new_state

if __name__ == '__main__':
    app.run(debug=True, port=8050)
