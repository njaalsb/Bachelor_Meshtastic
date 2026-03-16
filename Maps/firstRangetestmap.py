import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="Node Mapper - Colored Senders")

# Configuration for available colors in Folium
COLORS = [
    'blue', 'green', 'purple', 'orange', 'darkred', 
    'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 
    'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray'
]

# Initialize session state
if 'stage' not in st.session_state:
    st.session_state.stage = 'UPLOAD'
if 'results' not in st.session_state:
    st.session_state.results = []
if 'main_node_pos' not in st.session_state:
    st.session_state.main_node_pos = None
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'id_colors' not in st.session_state:
    st.session_state.id_colors = {}

TRONDHEIM_CENTER = [63.4305, 10.3951]

st.title("📍 Colored Node Mapper")

# --- STAGE 1: UPLOAD ---
if st.session_state.stage == 'UPLOAD':
    st.header("1. Upload CSV File")
    uploaded_file = st.file_uploader("Choose your Meshtastic CSV", type="csv")
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        text_df = df[df['packet_type'] == 'TEXT'].reset_index(drop=True)
        
        # Assign a color to each unique sender
        unique_ids = text_df['from_id'].unique()
        for i, uid in enumerate(unique_ids):
            st.session_state.id_colors[uid] = COLORS[i % len(COLORS)]
            
        st.session_state.df = text_df
        st.session_state.stage = 'MAIN_NODE'
        st.rerun()

# --- STAGE 2: PLACE MAIN NODE ---
elif st.session_state.stage == 'MAIN_NODE':
    st.header("2. Place the Main Node (The Roof)")
    st.info("Click on the map where the base station was located.")
    
    m = folium.Map(location=TRONDHEIM_CENTER, zoom_start=13)
    map_data = st_folium(m, height=500, width=1000)
    
    if map_data and map_data['last_clicked']:
        pos = [map_data['last_clicked']['lat'], map_data['last_clicked']['lng']]
        st.session_state.main_node_pos = pos
        if st.button(f"Confirm Main Node Position at {pos}"):
            st.session_state.stage = 'PROCESSING'
            st.rerun()

# --- STAGE 3: PROCESS TEXT MESSAGES ---
elif st.session_state.stage == 'PROCESSING':
    df = st.session_state.df
    idx = st.session_state.current_index
    
    # Sidebar Legend
    st.sidebar.header("Node Legend")
    for uid, color in st.session_state.id_colors.items():
        st.sidebar.markdown(f"**Node {uid}:** {color}")

    if idx < len(df):
        row = df.iloc[idx]
        sender_id = row['from_id']
        sender_color = st.session_state.id_colors[sender_id]
        
        st.header(f"Placing Message {idx + 1} of {len(df)}")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.subheader(f"Message: {row['text']}")
            st.markdown(f"**From ID:** `{sender_id}`")
            st.markdown(f"**Assigned Color:** :{sender_color}[{sender_color.upper()}]")
            st.write(f"RSSI: {row['rssi']} | SNR: {row['snr']}")
            
            if st.button("🚫 Ignore / Skip"):
                st.session_state.results.append({'timestamp': row['timestamp'], 'from_id': sender_id, 'text': row['text'], 'status': 'IGNORED', 'pos': None, 'color': sender_color})
                st.session_state.current_index += 1
                st.rerun()
            
        with col2:
            m = folium.Map(location=st.session_state.main_node_pos, zoom_start=15)
            # Main Node always Red
            folium.Marker(st.session_state.main_node_pos, tooltip="BASE STATION", icon=folium.Icon(color='red', icon='home')).add_to(m)
            
            # Show previously placed markers with their specific colors
            for res in st.session_state.results:
                if res['status'] == 'PLACED':
                    folium.Marker(res['pos'], popup=res['text'], icon=folium.Icon(color=res['color'])).add_to(m)
            
            map_click = st_folium(m, height=500, width=800, key=f"map_{idx}")
            
            if map_click and map_click['last_clicked']:
                clicked_pos = [map_click['last_clicked']['lat'], map_click['last_clicked']['lng']]
                if st.button(f"Place marker for Node {sender_id} here"):
                    st.session_state.results.append({
                        'timestamp': row['timestamp'], 'from_id': sender_id, 'text': row['text'],
                        'status': 'PLACED', 'pos': clicked_pos, 'color': sender_color
                    })
                    st.session_state.current_index += 1
                    st.rerun()
    else:
        st.session_state.stage = 'EXPORT'
        st.rerun()

# --- STAGE 4: EXPORT ---
elif st.session_state.stage == 'EXPORT':
    st.header("Results Export")
    final_df = pd.DataFrame(st.session_state.results)
    final_df['lat'] = final_df['pos'].apply(lambda x: x[0] if x else None)
    final_df['lon'] = final_df['pos'].apply(lambda x: x[1] if x else None)
    
    st.dataframe(final_df.drop(columns=['pos']))
    csv = final_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Map Data CSV", csv, "meshtastic_map_results.csv", "text/csv")
    
    if st.button("Start Over"):
        st.session_state.clear()
        st.rerun()