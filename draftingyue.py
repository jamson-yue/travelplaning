#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import requests
import json
import pandas as pd
from itertools import permutations
import streamlit as st
import folium
from streamlit_folium import folium_static
import sys

#根据地址获取经纬度
def get_location(address):
    url_loc = f"https://restapi.amap.com/v3/geocode/geo?key=a9a6da6bad351dfa3785d21807291b30&address={address}"
    response_loc = requests.get(url_loc)
    data_loc = json.loads(response_loc.text)
    return data_loc['geocodes'][0]['location']

#根据两点之间的经纬度获取路径距离
def get_distance(origin, destination,straegy):
    url_dist = 'https://restapi.amap.com/v3/direction/driving'
    parameters_dist = {
        'key': 'a9a6da6bad351dfa3785d21807291b30',
        'origin': get_location(origin),
        'destination':  get_location(destination),
        'strategy':straegy,
        'extensions':'base'
    }
    response_dist = requests.get(url_dist, params=parameters_dist)
    data_dist = response_dist.json()
    distance = int(data_dist['route']['paths'][0]['distance'])
    rts=''
    for i in range(len(data_dist['route']['paths'][0]['steps'])):
        rts=rts + data_dist['route']['paths'][0]['steps'][i]['polyline']+';'
    rts=rts[:-1]
    rts=rts[:-1].split(';')
    # 使用列表推导式将分割后的字符串转换为浮点数
    rts= [[float(x) for x in item.split(',')] for item in rts]
    return distance,rts

#穷举法取得最短路径距离及路径顺序
def tsp(locations):
    min_distance_tsp = float('inf')
    min_path_tsp = None
    min_order_tsp = None
    for path in permutations(locations):
        distance_tsp = 0
        for i in range(len(path) - 1):
            distance_tsp += df_dist.loc[path[i], path[i + 1]]
        distance_tsp += df_dist.loc[path[-1], path[0]]
        if distance_tsp < min_distance_tsp:
            min_distance_tsp = distance_tsp
            min_path_tsp = path
            min_order_tsp = list(path)
    return min_order_tsp, min_distance_tsp

#输入距离矩阵，通过Held-Karp算法取得最短路径距离及路径顺序
def held_karp(df_values):
    n = len(df_values)
    memo = {}

    def dp(mask, cur):
        if mask == (1 << n) - 1 and cur != 0:
            return df_values[cur][0], [0]  # 已经经过所有节点，返回回到起点的距离和路径
        if (mask, cur) in memo:
            return memo[(mask, cur)]

        min_cost_hk = sys.maxsize
        min_path_hk = []
        for i in range(n):
            if not (mask >> i) & 1:
                new_mask = mask | (1 << i)
                cost_hk, path_hk = dp(new_mask, i)
                cost_hk += df_values[cur][i]
                if cost_hk < min_cost_hk:
                    min_cost_hk = cost_hk
                    min_path_hk =  [i] + path_hk  # 修改此处

        memo[(mask, cur)] = (min_cost_hk, min_path_hk)
        return  min_cost_hk,min_path_hk

    return dp(1, 0)
#经度纬度互换位置
def swap_coordinates(coord):
    return (coord[1], coord[0])

#通过高德地图生成途经地点顺序及路线
route_plt=list()
path_lst=list()
def plot_route(route_plt,path_lst):
    center=swap_coordinates(route_plt[0])
    #tiles='http://webrd02.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7&x={x}&y={y}&z={z}'# 高德街道图
    tiles='http://webst02.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}' # 高德卫星图
    map_m=folium.Map(location=center,zoom_start=15,
                    #tiles='http://webrd02.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7&x={x}&y={y}&z={z}',
                    tiles=tiles,attr = 'default')
    da=list(map(swap_coordinates,route_plt))
    folium.PolyLine(locations=da, color="red").add_to(map_m)
    for i in range(len(path_lst[:-1])):
        marker=folium.Marker(location=swap_coordinates(get_location(path_lst[i]).split(',')),icon=folium.Icon(icon="info-sign",color='blue'),popup=str(i+1))
        marker.add_to(map_m)
    return map_m
# 高德地图行政区划API的URL和参数
url = "https://restapi.amap.com/v3/config/district"
params = {
    "key": "a9a6da6bad351dfa3785d21807291b30",
    "keywords": "中国",
    "subdistrict": 3,
    "extensions": "base"
}
# 发送HTTP请求并获取响应
response = requests.get(url, params=params)
data = json.loads(response.text)
# 初始化字典
location_dict = {}

# 遍历省份
for province in data["districts"][0]["districts"]:
    province_name = province["name"]
    location_dict[province_name] = {}

# 遍历城市
    for city in province["districts"]:
        city_name = city["name"]
        location_dict[province_name][city_name] = []

# 遍历县区
        for county in city["districts"]:
            county_name = county["name"]
            location_dict[province_name][city_name].append(county_name)


#获取出发点、途经地点信息，生成起点、途经点矩阵（dataframe)

if __name__ == "__main__":
    st.title("自驾路线规划")
    st.markdown('<span style="font-family: Arial; font-size: 20px;">注：如需在地图上查看规划的路线，请使用手机浏览器打开本链接。</span>', unsafe_allow_html=True)
    st.write("请输入出发点：")    
    column1,column2,column3=st.columns(3)
    
    
    if 'start_prov' not in st.session_state:
        st.session_state.start_prov = '浙江省'
        st.session_state.start_city = '温州市'
        st.session_state.start_county = '鹿城区'

    start_prov = column1.selectbox('省份', list(location_dict.keys()), key='start_prov')
    start_city=column2.selectbox("城市", list(location_dict[start_prov].keys()),key='start_city')
    start_county=column3.selectbox("区县", location_dict[start_prov][start_city],key='start_county')
    start_spec=st.text_input("详细地址：",key=start_prov + start_city + start_county)
    start = start_prov + start_city + start_county + start_spec
    locations = [start]
    strategy = st.number_input("请输入驾车策略（0：速度优先；1：费用优先；2：距离优先；4：躲避拥堵。)：", min_value=0, max_value=4, step=1)
    num = st.number_input("请输入途经地点数量：", min_value=1, step=1)
    for i in range(num):
            if 'wp_prov' not in st.session_state:
                st.session_state.wp_prov = '浙江省'
                st.session_state.wp_city = '温州市'
                
            column4,column5,column6=st.columns(3)
            wp_prov=column4.selectbox("省份", list(location_dict.keys()),key='wp_prov'+str(i))
            wp_city=column5.selectbox("城市", list(location_dict[wp_prov].keys()),key="wp_city"+str(i))
            wp_county=column6.selectbox("区县", location_dict[wp_prov][wp_city],key='wp_county'+str(i))
            wp_spec=st.text_input("详细地址：",key='wp_prov + wp_city + wp_county'+str(i))
            wp = wp_prov + wp_city + wp_county + wp_spec
            locations.append(wp)
 
    # 创建一个名为“路程规划”的按钮
    if st.button('路程规划'):
        container = st.empty()
        container.write("计算中，请稍候。。。。。。")
        orig = locations
        dest = locations
        df_dist = pd.DataFrame(index=orig, columns=dest)
        df_rts = pd.DataFrame(index=orig, columns=dest)
        for i in locations:
            for j in locations:
                df_dist.loc[i, j],df_rts.loc[i,j]= get_distance(i, j, strategy)
        if num < 6:
            min_path, min_cost = tsp(locations)
            min_path.append(locations[0])
            min_cost = min_cost + df_dist.loc[min_path[-1], start]
        else:
            df_dist_value = df_dist.values
            shortest_distance, shortest_path = held_karp(df_dist_value)
            temp_dist = df_dist_value[0, [shortest_path[0]]]
            min_cost = (shortest_distance + temp_dist)
            min_path = [locations[i] for i in shortest_path]
            min_path.insert(0, locations[0])
        
        container.write("计算完成，地图加载中")
        
        st.write("最佳路程距离：", round(int(min_cost) / 1000,2), "公里")
        st.write("最佳路程顺序：", min_path)

        rts_final =list()
        for x in range(len(min_path)-1):
            rts_temp=df_rts.loc[min_path[x],min_path[x+1]]
            rts_final=rts_final+rts_temp
        start_poi=rts_final[0]
        end_poi=rts_final[-1]
        m = plot_route(rts_final,min_path)
        folium_static(m)
        
        container.write("地图加载完成，请稍后。。。")

# In[ ]: