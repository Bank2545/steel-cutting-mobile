import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import copy

# --- ตั้งค่าหน้าเว็บ (Mobile Optimized) ---
st.set_page_config(page_title="ตัดเหล็ก (Mobile)", layout="wide", initial_sidebar_state="collapsed")

# --- CSS ปรับแต่งสำหรับมือถือ ---
st.markdown("""
<style>
    /* ปรับปุ่มให้ใหญ่ เต็มความกว้าง กดง่ายบนมือถือ */
    div.stButton > button:first-child { 
        font-size: 20px; 
        height: 3.5em; 
        width: 100%; 
        border-radius: 12px; 
        margin-top: 10px;
        margin-bottom: 10px;
    }
    /* ปรับขนาดตัวหนังสือหัวข้อ */
    h1 { font-size: 1.8rem; }
    h2 { font-size: 1.5rem; }
    h3 { font-size: 1.2rem; }
    
    /* ปรับตารางให้เลื่อนซ้ายขวาได้ง่าย */
    .stDataFrame { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- Helper Functions (เหมือนเดิม) ---
def get_color(id):
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    return colors[(id-1) % len(colors)]

def make_cube(x, y, z, dx, dy, dz, color, opacity=1.0, name=""):
    return go.Mesh3d(
        x=[x, x, x+dx, x+dx, x, x, x+dx, x+dx],
        y=[y, y+dy, y, y+dy, y, y+dy, y, y+dy],
        z=[z, z, z, z, z+dz, z+dz, z+dz, z+dz],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color=color, opacity=opacity, name=name, showscale=False, hoverinfo='text', text=name
    )

def get_cube_wireframe(x, y, z, dx, dy, dz, color='black', width=3):
    xl = [x, x+dx, x+dx, x, x,  x, x+dx, x+dx, x,    x,    x+dx, x+dx, x+dx, x+dx, x,    x]
    yl = [y, y,    y+dy, y+dy, y, y,    y,    y+dy, y+dy, y,    y,    y,    y+dy, y+dy, y+dy, y+dy]
    zl = [z, z,    z,    z,    z, z+dz, z+dz, z+dz, z+dz, z+dz, z+dz, z,    z,    z+dz, z+dz, z]
    return go.Scatter3d(x=xl, y=yl, z=zl, mode='lines', line=dict(color=color, width=width), hoverinfo='skip', showlegend=False)

def add_text_at_point(x, y, z, text, color='black', size=14, anchor="middle center"):
    return go.Scatter3d(
        x=[x], y=[y], z=[z],
        mode='text',
        text=[text],
        textposition=anchor,
        textfont=dict(size=size, color=color, family="Arial Black"),
        showlegend=False,
        hoverinfo='skip'
    )

# --- Session State ---
if 'parts' not in st.session_state: st.session_state.parts = []
if 'sim_step' not in st.session_state: st.session_state.sim_step = 0
if 'calculated_rows' not in st.session_state: st.session_state.calculated_rows = []
if 'last_action' not in st.session_state: st.session_state.last_action = ""

# --- Default Values (เพื่อไม่ให้ค่าหายเวลารีเฟรช) ---
if 'stock_w' not in st.session_state: st.session_state.stock_w = 400.0
if 'stock_l' not in st.session_state: st.session_state.stock_l = 500.0
if 'stock_h' not in st.session_state: st.session_state.stock_h = 300.0
if 'blade' not in st.session_state: st.session_state.blade = 2.0

# --- Logic ---
def pack_parts(parts_input, s_w, s_l, blade):
    parts = copy.deepcopy(parts_input)
    for p in parts:
        if p['width'] > p['length']:
            p['width'], p['length'] = p['length'], p['width']
            p['rotated'] = True
        else:
            p['rotated'] = False
    parts.sort(key=lambda x: x['length'], reverse=True)
    
    rows = []
    current_row = []
    current_row_w = 0
    current_row_max_l = 0
    
    for part in parts:
        needed_w = part['width']
        needed_l = part['length']
        gap = blade if len(current_row) > 0 else 0
        
        can_fit_normal = (current_row_w + gap + needed_w <= s_w)
        can_fit_rotated = (current_row_w + gap + needed_l <= s_w)
        
        final_w = needed_w
        final_l = needed_l
        is_rotated_in_row = False
        
        if not current_row: pass 
        else:
            diff_normal = abs(current_row_max_l - needed_l)
            diff_rotated = abs(current_row_max_l - needed_w)
            if can_fit_rotated and (diff_rotated < diff_normal):
                final_w = needed_l; final_l = needed_w; is_rotated_in_row = True
            elif not can_fit_normal and can_fit_rotated:
                final_w = needed_l; final_l = needed_w; is_rotated_in_row = True
                
        part['width'] = final_w; part['length'] = final_l
        if is_rotated_in_row: part['rotated'] = not part['rotated']
        
        if current_row_w + gap + final_w <= s_w:
            current_row.append(part); current_row_w += (gap + final_w)
            if final_l > current_row_max_l: current_row_max_l = final_l
        else:
            if current_row: rows.append({"items": current_row, "length": current_row_max_l})
            current_row = [part]; current_row_w = part['width']; current_row_max_l = part['length']
            
    if current_row: rows.append({"items": current_row, "length": current_row_max_l})
    return rows

# ==========================================
# ส่วนหน้าจอหลัก (Main UI) - ออกแบบสำหรับมือถือ
# ==========================================
st.title("📱 เครื่องมือตัดเหล็ก (Mobile)")

# --- 1. ส่วนตั้งค่า (พับเก็บได้ เพื่อไม่ให้รก) ---
with st.expander("⚙️ ตั้งค่าเหล็กก้อน & ใบมีด", expanded=False):
    st.caption("กำหนดขนาดเหล็กก้อนดิบและใบเลื่อยที่นี่")
    col_s1, col_s2 = st.columns(2)
    st.session_state.stock_w = col_s1.number_input("กว้าง (Stock)", value=st.session_state.stock_w)
    st.session_state.stock_l = col_s2.number_input("ยาว (Stock)", value=st.session_state.stock_l)
    
    col_s3, col_s4 = st.columns(2)
    st.session_state.stock_h = col_s3.number_input("หนา (Stock)", value=st.session_state.stock_h)
    st.session_state.blade = col_s4.number_input("ใบเลื่อย (mm)", value=st.session_state.blade)

# --- 2. ส่วนสั่งงาน (Input) ---
with st.expander("➕ เพิ่มรายการตัด (กดที่นี่)", expanded=True):
    c1, c2, c3 = st.columns(3)
    in_w = c1.number_input("กว้าง", value=150.0, step=10.0, key="in_w")
    in_l = c2.number_input("ยาว", value=400.0, step=10.0, key="in_l")
    in_h = c3.number_input("หนา", value=300.0, step=10.0, key="in_h")
    in_qty = st.number_input("จำนวน (ชิ้น)", min_value=1, value=1, step=1, key="in_qty")

    if st.button("บันทึกรายการ ✅"):
        new_ids = []
        for _ in range(in_qty):
            new_id = len(st.session_state.parts) + 1
            st.session_state.parts.append({
                "width": in_w, "length": in_l, "thickness": in_h, "id": new_id
            })
            new_ids.append(new_id)
        st.session_state.sim_step = 0
        st.session_state.last_action = f"✅ เพิ่ม {in_w:.0f}x{in_l:.0f} ({in_qty} ชิ้น)"

# --- แสดงสถานะแจ้งเตือน ---
if st.session_state.last_action:
    st.success(st.session_state.last_action)

# --- ตารางรายการ ---
if len(st.session_state.parts) > 0:
    st.write(f"📋 **รายการในตะกร้า: {len(st.session_state.parts)} ชิ้น**")
    df = pd.DataFrame(st.session_state.parts)[["id", "width", "length", "thickness"]]
    df.columns = ["ID", "กว้าง", "ยาว", "หนา"]
    st.dataframe(df, use_container_width=True, height=150)
    
    # ปุ่มคำนวณใหญ่ๆ
    if st.button("🚀 คำนวณแผนการตัด (Start)"):
        st.session_state.sim_step = 0
        rows = pack_parts(st.session_state.parts, st.session_state.stock_w, st.session_state.stock_l, st.session_state.blade)
        st.session_state.calculated_rows = rows
        st.session_state.last_action = ""
        st.rerun()

    if st.button("🗑️ ล้างทั้งหมด", type="secondary"):
        st.session_state.parts = []
        st.session_state.sim_step = 0
        st.session_state.calculated_rows = []
        st.session_state.last_action = ""
        st.rerun()

# --- 3. ส่วนแสดงผล (Results) ---
if len(st.session_state.calculated_rows) > 0:
    st.markdown("---")
    rows = st.session_state.calculated_rows
    total_steps = len(rows)
    
    # ใช้ Tabs แยกมุมมอง เพื่อให้ไม่รกหน้าจอมือถือ
    tab1, tab2 = st.tabs(["🖼️ ภาพ 3D", "📝 วิธีตัด"])
    
    # --- ปุ่มควบคุม (อยู่เหนือ Tabs จะได้กดง่าย) ---
    c_prev, c_stat, c_next = st.columns([1, 2, 1])
    with c_prev:
        if st.button("◀"):
            if st.session_state.sim_step > 0: st.session_state.sim_step -= 1
    with c_stat:
        st.markdown(f"<h4 style='text-align: center;'>ขั้นตอน {st.session_state.sim_step}/{total_steps}</h4>", unsafe_allow_html=True)
    with c_next:
        if st.button("▶"):
            if st.session_state.sim_step < total_steps: st.session_state.sim_step += 1

    # --- เตรียมข้อมูลกราฟ ---
    stock_w, stock_l, stock_h = st.session_state.stock_w, st.session_state.stock_l, st.session_state.stock_h
    blade_thickness = st.session_state.blade
    
    fig = go.Figure()
    max_dim = max(stock_w, stock_l, stock_h)
    fig.add_trace(get_cube_wireframe(0, 0, 0, stock_w, stock_l, stock_h, color='#ccc', width=1))
    current_y = 0 
    
    # Loop วาดกราฟ
    if st.session_state.sim_step == 0:
        fig.add_trace(make_cube(0, 0, 0, stock_w, stock_l, stock_h, 'gray', 0.05, "Stock"))
        fig.add_trace(add_text_at_point(stock_w/2, -20, 0, f"W:{stock_w:.0f}", color="black", size=14))
        fig.add_trace(add_text_at_point(-20, stock_l/2, 0, f"L:{stock_l:.0f}", color="black", size=14))

    for i in range(st.session_state.sim_step):
        row = rows[i]
        row_len = row['length']
        is_current = (i == st.session_state.sim_step - 1)
        
        # Main Cut
        fig.add_trace(make_cube(0, current_y + row_len, 0, stock_w, blade_thickness, stock_h, 'black', 1.0))
        
        curr_x = 0
        for item in row['items']:
            if curr_x > 0: fig.add_trace(make_cube(curr_x, current_y, 0, blade_thickness, row_len, stock_h, 'black', 1.0))
            curr_x += blade_thickness
            
            color = get_color(item['id'])
            opacity = 1.0 if is_current else 0.4
            
            fig.add_trace(make_cube(curr_x, current_y, 0, item['width'], item['length'], item['thickness'], color, opacity, f"ID {item['id']}"))
            fig.add_trace(get_cube_wireframe(curr_x, current_y, 0, item['width'], item['length'], item['thickness'], color='black', width=2))
            
            # Labels
            text_z = item['thickness'] + 10
            text_col = 'white' if is_current else 'black'
            fig.add_trace(add_text_at_point(curr_x + item['width']/2, current_y + item['length']/2, text_z, f"ID{item['id']}", color=text_col, size=16))
            if is_current:
                 fig.add_trace(add_text_at_point(curr_x + item['width']/2, current_y + item['length']/2, text_z-20, f"{item['width']:.0f}x{item['length']:.0f}", color=text_col, size=12))

            curr_x += item['width']
        
        if curr_x < stock_w:
            waste_w = stock_w - curr_x
            fig.add_trace(make_cube(curr_x, current_y, 0, waste_w, row_len, stock_h, 'red', 0.05))
            fig.add_trace(get_cube_wireframe(curr_x, current_y, 0, waste_w, row_len, stock_h, color='red', width=1))
            fig.add_trace(add_text_at_point(curr_x + waste_w/2, current_y + row_len/2, stock_h, f"เศษ {waste_w:.0f}", color="red", size=12))

        current_y += (row_len + blade_thickness)

    remain_l = stock_l - current_y
    if remain_l > 0:
        fig.add_trace(make_cube(0, current_y, 0, stock_w, remain_l, stock_h, 'blue', 0.05))
        fig.add_trace(get_cube_wireframe(0, current_y, 0, stock_w, remain_l, stock_h, color='blue', width=1))
        if st.session_state.sim_step == total_steps:
             fig.add_trace(add_text_at_point(stock_w/2, current_y + remain_l/2, stock_h, f"ท้าย {remain_l:.0f}", color="blue", size=16))

    # --- TAB 1: 3D GRAPH ---
    with tab1:
        view_mode = st.radio("มุมมอง:", ["2D (บน)", "3D (หมุน)"], horizontal=True, label_visibility="collapsed")
        
        if "2D" in view_mode:
            camera = dict(eye=dict(x=0, y=0, z=2.5), up=dict(x=0, y=1, z=0))
            proj = "orthographic"
            drag = "pan"
        else:
            camera = dict(eye=dict(x=1.2, y=1.2, z=1.2))
            proj = "perspective"
            drag = "turntable"

        fig.update_layout(
            scene=dict(
                xaxis=dict(title='X', range=[0, max_dim], showbackground=False),
                yaxis=dict(title='Y', range=[0, max_dim], showbackground=False),
                zaxis=dict(title='Z', range=[0, max_dim], showbackground=False),
                aspectmode='cube', camera=camera
            ), 
            height=450,  # ความสูงกำลังดีกับมือถือ
            margin=dict(r=0, l=0, b=0, t=0),
            dragmode=drag
        )
        fig.layout.scene.camera.projection.type = proj
        st.plotly_chart(fig, use_container_width=True)

    # --- TAB 2: TEXT INSTRUCTION ---
    with tab2:
        st.subheader("📝 รายละเอียดขั้นตอน")
        if st.session_state.sim_step == 0:
            st.info(f"เตรียมเหล็กก้อน: {stock_w:.0f}x{stock_l:.0f}x{stock_h:.0f}")
        else:
            # ย้อนดูประวัติขั้นตอน
            for i in range(st.session_state.sim_step):
                row = rows[i]
                row_len = row['length']
                is_curr = (i == st.session_state.sim_step - 1)
                
                # ถ้าเป็นขั้นตอนปัจจุบัน ให้ Highlight
                if is_curr:
                    st.success(f"📌 **ขั้นตอนที่ {i+1} (ปัจจุบัน)**")
                else:
                    st.write(f"🔹 **ขั้นตอนที่ {i+1}**")
                
                st.markdown(f"1. เลื่อนระยะตัดยาว: **{row_len:.1f} mm**")
                st.markdown(f"2. ซอยย่อยในแถวนี้:")
                for item in row['items']:
                    st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;- ID {item['id']}: ขนาด {item['width']:.0f}x{item['length']:.0f}")
                st.divider()