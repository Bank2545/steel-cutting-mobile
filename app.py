import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import copy

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="ตัดเหล็ก (3 ทางเลือก + รายงานละเอียด)", layout="wide", initial_sidebar_state="collapsed")

# --- 2. CSS ---
st.markdown("""
<style>
    div.stButton > button:first-child { 
        font-size: 20px; height: 3.5em; width: 100%; border-radius: 12px; margin: 10px 0;
    }
    h1 { font-size: 1.8rem; }
    h2 { font-size: 1.5rem; }
    .step-box {
        border: 1px solid #e0e0e0; border-radius: 10px; padding: 15px; margin-bottom: 15px; background-color: #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .cut-header {
        background-color: #f8f9fa; padding: 10px; border-radius: 8px; font-weight: bold; margin-bottom: 10px; border-left: 5px solid #333;
    }
    .waste-item { color: #d62728; font-size: 0.95em; }
    .part-item { color: #2ca02c; font-weight: bold; font-size: 1.05em; }
    .waste-label { background-color: #ffe6e6; padding: 2px 8px; border-radius: 4px; color: #d62728; font-size: 0.85em; font-weight: bold; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; flex-wrap: wrap; }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; flex-grow: 1; justify-content: center; background-color: #f1f3f4; border-radius: 8px; margin-bottom: 5px;
    }
    .stTabs [aria-selected="true"] { background-color: #e3f2fd; border: 2px solid #2196f3; color: #1565c0; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 3. Helper Functions ---
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
        x=[x], y=[y], z=[z], mode='text', text=[text], textposition=anchor,
        textfont=dict(size=size, color=color, family="Arial Black"), showlegend=False, hoverinfo='skip'
    )

# --- 4. Session State ---
if 'parts' not in st.session_state: st.session_state.parts = []
if 'scenarios' not in st.session_state: st.session_state.scenarios = {} 
if 'last_action' not in st.session_state: st.session_state.last_action = ""

# Defaults
if 'stock_w' not in st.session_state: st.session_state.stock_w = 400.0
if 'stock_l' not in st.session_state: st.session_state.stock_l = 500.0
if 'stock_h' not in st.session_state: st.session_state.stock_h = 300.0
if 'blade' not in st.session_state: st.session_state.blade = 2.0

# --- 5. Logic ---
def run_packing_algorithm(parts_input, s_w, s_l, blade, strategy="mixed"):
    parts = copy.deepcopy(parts_input)
    
    # 1. ปรับทิศทาง
    for p in parts:
        dim1, dim2 = sorted([p['width'], p['length']]) 
        if strategy == "vertical": 
            p['width'], p['length'] = dim1, dim2
            p['rotated'] = False
        elif strategy == "horizontal": 
            p['width'], p['length'] = dim2, dim1
            p['rotated'] = True
        else: 
            p['width'], p['length'] = dim1, dim2
            p['rotated'] = False

    # 2. เรียงลำดับ
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
        
        is_rotated_in_row = False
        if strategy == "mixed":
            rotated_w, rotated_l = needed_l, needed_w
            can_fit_rotated = (current_row_w + gap + rotated_w <= s_w)
            
            if not current_row:
                pass 
            else:
                diff_normal = abs(current_row_max_l - needed_l)
                diff_rotated = abs(current_row_max_l - rotated_l)
                if (can_fit_rotated and diff_rotated < diff_normal) or (not can_fit_normal and can_fit_rotated):
                    part['width'] = rotated_w; part['length'] = rotated_l
                    needed_w = rotated_w; needed_l = rotated_l
                    is_rotated_in_row = True
                    part['rotated'] = not part['rotated']

        if current_row_w + gap + needed_w <= s_w:
            current_row.append(part)
            current_row_w += (gap + needed_w)
            if needed_l > current_row_max_l: current_row_max_l = needed_l
        else:
            if current_row: rows.append({"items": current_row, "length": current_row_max_l})
            current_row = [part]; current_row_w = part['width']; current_row_max_l = part['length']
            
    if current_row: rows.append({"items": current_row, "length": current_row_max_l})
    return rows

# ================= 6. UI =================
st.title("📋 ตัดเหล็ก: วิเคราะห์ 3 ทางเลือก")

# [A] ตั้งค่า
with st.expander("⚙️ ตั้งค่า (Stock & Blade)", expanded=False):
    c1, c2 = st.columns(2)
    st.session_state.stock_w = c1.number_input("กว้าง (Stock)", value=st.session_state.stock_w)
    st.session_state.stock_l = c2.number_input("ยาว (Stock)", value=st.session_state.stock_l)
    c3, c4 = st.columns(2)
    st.session_state.stock_h = c3.number_input("หนา (Stock)", value=st.session_state.stock_h)
    st.session_state.blade = c4.number_input("ใบเลื่อย (mm)", value=st.session_state.blade)

# [B] เพิ่มรายการ
with st.expander("➕ เพิ่มรายการตัด", expanded=True):
    c1, c2, c3 = st.columns(3)
    in_w = c1.number_input("กว้าง", value=150.0, step=10.0, key="in_w")
    in_l = c2.number_input("ยาว", value=400.0, step=10.0, key="in_l")
    in_h = c3.number_input("หนา", value=300.0, step=10.0, key="in_h")
    in_qty = st.number_input("จำนวน", min_value=1, value=1, step=1, key="in_qty")

    if st.button("บันทึกรายการ ✅"):
        for _ in range(in_qty):
            new_id = len(st.session_state.parts) + 1
            st.session_state.parts.append({"width": in_w, "length": in_l, "thickness": in_h, "id": new_id})
        st.session_state.last_action = f"✅ เพิ่ม {in_w:.0f}x{in_l:.0f} ({in_qty} ชิ้น)"

if st.session_state.last_action: st.success(st.session_state.last_action)

# ตาราง
if len(st.session_state.parts) > 0:
    df = pd.DataFrame(st.session_state.parts)[["id", "width", "length", "thickness"]]
    df.columns = ["ID", "กว้าง", "ยาว", "หนา"]
    st.dataframe(df, use_container_width=True, height=150)
    
    col_btn1, col_btn2 = st.columns([2, 1])
    with col_btn1:
        if st.button("🚀 คำนวณ 3 แบบ (Analyze All)"):
            s_w, s_l, b = st.session_state.stock_w, st.session_state.stock_l, st.session_state.blade
            r_A = run_packing_algorithm(st.session_state.parts, s_w, s_l, b, strategy="vertical")
            r_B = run_packing_algorithm(st.session_state.parts, s_w, s_l, b, strategy="horizontal")
            r_C = run_packing_algorithm(st.session_state.parts, s_w, s_l, b, strategy="mixed")
            st.session_state.scenarios = {
                "แบบ A: ตัดตามยาว": r_A,
                "แบบ B: ตัดตามขวาง": r_B,
                "แบบ C: AI ผสม (แนะนำ)": r_C
            }
            st.rerun()
    with col_btn2:
        if st.button("🗑️ ล้าง", type="secondary"):
            st.session_state.parts = []; st.session_state.scenarios = {}; st.rerun()

# [C] ผลลัพธ์ (Tabs)
if st.session_state.scenarios:
    st.markdown("---")
    st.subheader("📊 ผลลัพธ์เปรียบเทียบ (กดเลือก Tab)")
    
    tab_names = list(st.session_state.scenarios.keys())
    tabs = st.tabs(tab_names)
    
    for i, tab_name in enumerate(tab_names):
        with tabs[i]:
            rows = st.session_state.scenarios[tab_name]
            
            # คำนวณความยาวรวม
            total_y_used = sum([r['length'] for r in rows]) + (len(rows) * st.session_state.blade)
            remain_total = st.session_state.stock_l - total_y_used
            
            if remain_total < 0:
                st.error(f"❌ ตัดไม่ได้! ยาวเกินก้อน {abs(remain_total):.1f} มม.")
            else:
                st.success(f"✅ ใช้ความยาว: {total_y_used:.1f} มม. | เหลือท้ายก้อน: {remain_total:.1f} มม.")
                
                # --- 3D Visualization ---
                stock_w, stock_l, stock_h = st.session_state.stock_w, st.session_state.stock_l, st.session_state.stock_h
                blade_thickness = st.session_state.blade
                
                fig = go.Figure()
                max_dim = max(stock_w, stock_l, stock_h)
                
                fig.add_trace(get_cube_wireframe(0, 0, 0, stock_w, stock_l, stock_h, color='#ccc', width=1))
                fig.add_trace(add_text_at_point(stock_w/2, -30, 0, f"W {stock_w:.0f}", color="black"))
                fig.add_trace(add_text_at_point(-30, stock_l/2, 0, f"L {stock_l:.0f}", color="black"))

                current_y = 0 
                for row in rows:
                    row_len = row['length']
                    fig.add_trace(make_cube(0, current_y + row_len, 0, stock_w, blade_thickness, stock_h, 'black', 1.0))
                    
                    curr_x = 0
                    for item in row['items']:
                        if curr_x > 0: fig.add_trace(make_cube(curr_x, current_y, 0, blade_thickness, row_len, stock_h, 'black', 1.0))
                        curr_x += blade_thickness
                        color = get_color(item['id'])
                        fig.add_trace(make_cube(curr_x, current_y, 0, item['width'], item['length'], item['thickness'], color, 0.8, f"ID {item['id']}"))
                        fig.add_trace(get_cube_wireframe(curr_x, current_y, 0, item['width'], item['length'], item['thickness'], color='black', width=2))
                        fig.add_trace(add_text_at_point(curr_x + item['width']/2, current_y + item['length']/2, item['thickness']+10, f"ID{item['id']}", color='black'))
                        curr_x += item['width']
                    
                    if curr_x < stock_w:
                        waste_w = stock_w - curr_x
                        fig.add_trace(make_cube(curr_x, current_y, 0, waste_w, row_len, stock_h, 'red', 0.1, "Waste"))
                        fig.add_trace(get_cube_wireframe(curr_x, current_y, 0, waste_w, row_len, stock_h, color='red', width=1))
                        fig.add_trace(add_text_at_point(curr_x + waste_w/2, current_y + row_len/2, stock_h, f"เศษ {waste_w:.0f}", color="red"))

                    current_y += (row_len + blade_thickness)

                if remain_total > 0:
                    fig.add_trace(make_cube(0, current_y, 0, stock_w, remain_total, stock_h, 'blue', 0.05))
                    fig.add_trace(get_cube_wireframe(0, current_y, 0, stock_w, remain_total, stock_h, color='blue', width=1))
                    fig.add_trace(add_text_at_point(stock_w/2, current_y + remain_total/2, stock_h, f"ท้าย {remain_total:.0f}", color="blue"))

                # ตั้งค่ากล้อง
                view_mode = st.radio(f"มุมมอง ({i}):", ["2D (บน)", "3D (หมุน)"], horizontal=True, label_visibility="collapsed", key=f"view_{i}")
                if "2D" in view_mode:
                    camera = dict(eye=dict(x=0, y=0, z=2.5), up=dict(x=0, y=1, z=0))
                    proj = "orthographic"
                else:
                    camera = dict(eye=dict(x=1.2, y=1.2, z=1.2))
                    proj = "perspective"

                fig.update_layout(
                    scene=dict(xaxis=dict(range=[0, max_dim], showbackground=False), yaxis=dict(range=[0, max_dim], showbackground=False), zaxis=dict(range=[0, max_dim], showbackground=False), aspectmode='cube', camera=camera), 
                    height=450, margin=dict(r=0, l=0, b=0, t=0), dragmode="turntable" if "3D" in view_mode else "pan"
                )
                fig.layout.scene.camera.projection.type = proj
                
                # --- แก้ไขตรงนี้: เพิ่ม key ให้ไม่ซ้ำกัน ---
                st.plotly_chart(fig, use_container_width=True, key=f"chart_{i}")

                # --- ใบสั่งงานละเอียด (Detailed Report) ---
                st.write("📝 **ใบสั่งงานและรายงานเศษ (Cut List)**")
                current_y_report = 0
                
                for k, row in enumerate(rows):
                    row_len = row['length']
                    cut_pos = current_y_report + row_len
                    
                    with st.container():
                        st.markdown(f'<div class="step-box">', unsafe_allow_html=True)
                        st.markdown(f'<div class="cut-header">✂️ ตัดครั้งที่ {k+1} (ระยะตัด {cut_pos:.1f} mm)</div>', unsafe_allow_html=True)
                        
                        c_left, c_right = st.columns(2)
                        used_w = 0
                        with c_left:
                            st.caption("✅ ชิ้นงาน:")
                            for idx, item in enumerate(row['items']):
                                used_w += item['width']
                                if idx > 0: used_w += blade_thickness
                                st.markdown(f"• <span class='part-item'>ID{item['id']}</span>: {item['width']:.0f}x{item['length']:.0f}x{item['thickness']:.0f}", unsafe_allow_html=True)
                                
                                # Top Waste
                                top_waste = stock_h - item['thickness']
                                if top_waste > 0:
                                    st.markdown(f"&nbsp;&nbsp;↳ <span class='waste-label'>เศษปาดหน้า</span>: {item['width']:.0f}x{item['length']:.0f}x<b>{top_waste:.0f}</b>", unsafe_allow_html=True)

                        with c_right:
                            st.caption("❌ เศษ:")
                            waste_w = stock_w - used_w
                            if waste_w > 0:
                                st.markdown(f"• <span class='waste-item'>เศษข้างแถว {k+1}</span>: <b>{waste_w:.1f}</b> x {row_len:.1f} x {stock_h:.0f}", unsafe_allow_html=True)
                            else:
                                st.write("- ไม่มีเศษข้าง")
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    current_y_report += (row_len + blade_thickness)
                
                if remain_total > 0:
                     st.markdown(f"""
                        <div class="step-box" style="border-left: 5px solid #2196f3; background-color: #f8fbff;">
                            <b>🔵 เศษท้ายก้อน (Remnant)</b><br>
                            ขนาด: กว้าง <b>{stock_w:.0f}</b> x ยาว <b>{remain_total:.1f}</b> x หนา <b>{stock_h:.0f}</b>
                        </div>
                     """, unsafe_allow_html=True)