import streamlit as st
import numpy as np
import plotly.graph_objects as go

# Configuración de página
st.set_page_config(page_title="Curva Polar Blanik L-13", layout="wide")

st.title("✈️ Análisis Dinámico de Curva Polar -Blanik L-13 ")
st.markdown("Generador interactivo para clase magistral.")

class BlanikPolar:
    def __init__(self):
        # Parámetros base del Blanik L-13
        self.W_ref = 472.0  # kg
        self.V_min_sink = 73.5  # km/h
        self.Vz_min_sink = 0.82  # m/s
        self.V_stall_base = 60.0  # km/h
        self.V_NE = 253.0  # km/h
        
        # Constante de la parábola base calculada analíticamente
        self.a = 0.000303957
        
    def get_stall_speed(self, weight, bank_angle_deg):
        """Calcula la velocidad de pérdida dinámica"""
        n = 1.0 / np.cos(np.radians(bank_angle_deg))
        k = np.sqrt((weight * n) / self.W_ref)
        return self.V_stall_base * k
        
    def base_polar(self, V):
        """Calcula la tasa de caída base (m/s) dada la velocidad indicada (km/h)"""
        return self.a * (V - self.V_min_sink)**2 + self.Vz_min_sink
        
    def dynamic_polar(self, V, weight, bank_angle_deg, v_air):
        """Calcula la tasa de caída dinámica afectada por las condiciones"""
        # Factor de carga por ángulo de banqueo
        n = 1.0 / np.cos(np.radians(bank_angle_deg))
        W_eff = weight * n
        
        # Factor de peso
        k = np.sqrt(W_eff / self.W_ref)
        
        # Velocidad equivalente para la curva base
        V_base = V / k
        Vz_base = self.base_polar(V_base)
        
        # Nueva tasa de caída corregida por peso y banqueo
        Vz = k * Vz_base
        
        # Efecto de la masa de aire (v_air > 0 significa ascendente, reduce la tasa de caída neta)
        Vz_net = Vz - v_air
        return Vz_net

    def get_optimal_point(self, weight, bank_angle_deg, v_air, v_headwind):
        """Busca el punto de planeo óptimo (MacCready) numéricamente"""
        v_stall = self.get_stall_speed(weight, bank_angle_deg)
        V_test = np.linspace(v_stall, self.V_NE, 2000)
        Vz_net = self.dynamic_polar(V_test, weight, bank_angle_deg, v_air)
        
        # Velocidad respecto al suelo
        V_ground = V_test - v_headwind
        
        # Evitar valores negativos de avance
        valid = V_ground > 5
        if not np.any(valid): 
            return 90, 1.0
            
        V_test = V_test[valid]
        Vz_net = Vz_net[valid]
        V_ground = V_ground[valid]
        
        # Si la ascendente es tan fuerte que la tasa de caída neta es <= 0 en algún punto,
        # la teoría MacCready indica que la velocidad óptima de planeo es la de mínima caída.
        # Además, geométricamente la tangente desde el origen no existe.
        if np.any(Vz_net <= 0):
            idx_opt = np.argmin(Vz_net)
            return V_test[idx_opt], Vz_net[idx_opt]
            
        # Minimizamos la razón (Tasa de caída / Avance en ruta) para encontrar la tangente
        ratio = Vz_net / V_ground
        idx_opt = np.argmin(ratio)
        return V_test[idx_opt], Vz_net[idx_opt]

    def get_min_sink_point(self, weight, bank_angle_deg, v_air):
        """Busca el punto de mínima caída numéricamente"""
        v_stall = self.get_stall_speed(weight, bank_angle_deg)
        V_test = np.linspace(v_stall, min(150, self.V_NE), 1000)
        Vz_net = self.dynamic_polar(V_test, weight, bank_angle_deg, v_air)
        idx_min = np.argmin(Vz_net)
        return V_test[idx_min], Vz_net[idx_min]

# Instancia del modelo
polar = BlanikPolar()

# --- SIDEBAR: CONTROLES ---
with st.sidebar:
    st.header("Parámetros de Vuelo")
    weight = st.slider("Peso Total (kg)", 292, 500, 472)
    bank_angle = st.slider("Ángulo de Inclinación (°)", 0, 60, 0)
    v_headwind = st.slider("Viento Frente/Cola (km/h) [>0 Frente]", -50, 50, 0)
    v_air = st.slider("Masa de Aire (m/s) [>0 Ascendente]", -5.0, 5.0, 0.0, step=0.1)

# --- PESTAÑAS ---
tab1, tab2 = st.tabs(["Gráfico 2D Dinámico", "Análisis 3D de Superficie"])

with tab1:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Generar datos de la curva recortados en los límites operacionales
        v_stall = polar.get_stall_speed(weight, bank_angle)
        V = np.linspace(v_stall, polar.V_NE, 1000)
        Vz = polar.dynamic_polar(V, weight, bank_angle, v_air)
        
        # Puntos característicos
        v_opt, vz_opt = polar.get_optimal_point(weight, bank_angle, v_air, v_headwind)
        v_min, vz_min = polar.get_min_sink_point(weight, bank_angle, v_air)
        
        fig = go.Figure()
        
        # Curva polar
        fig.add_trace(go.Scatter(x=V, y=Vz, mode='lines', name='Curva Polar L-13', line=dict(color='blue', width=2.5)))
        
        # Punto de mínima caída
        fig.add_trace(go.Scatter(x=[v_min], y=[vz_min], mode='markers+text', name='Mínima Caída',
                                 text=['Vz min'], textposition="top center",
                                 marker=dict(color='green', size=12)))
        
        # Punto de planeo óptimo (Max L/D)
        fig.add_trace(go.Scatter(x=[v_opt], y=[vz_opt], mode='markers+text', name='Planeo Óptimo (L/D max)',
                                 text=['Planeo Óptimo'], textposition="bottom right",
                                 marker=dict(color='red', size=12)))
        
        # Tangente MacCready
        # Si vz_opt es > 0, dibujamos la tangente desde el punto de origen de MacCready
        if vz_opt > 0:
            m = vz_opt / (v_opt - v_headwind)
            v_end = v_opt + 30
            vz_end = vz_opt + m * 30
            fig.add_trace(go.Scatter(x=[v_headwind, v_opt, v_end], 
                                     y=[0, vz_opt, vz_end], 
                                     mode='lines', name='Tangente MacCready', 
                                     line=dict(color='red', width=1.5, dash='dash')))
                                 
        fig.update_layout(
            title="Curva Polar de Velocidades - LET L-13 Blaník",
            xaxis_title="Velocidad Horizontal (km/h)",
            yaxis_title="Tasa de Caída Neta (m/s)",
            xaxis=dict(range=[0, 260], gridcolor='lightgray', zerolinecolor='lightgray'),
            yaxis=dict(autorange="reversed", range=[10, -1], gridcolor='lightgray', zerolinecolor='lightgray'),
            plot_bgcolor='white',
            height=600,
            hovermode="x unified"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.subheader("Resultados")
        st.metric("Vel. Mínima Caída", f"{v_min:.1f} km/h", f"{vz_min:.2f} m/s", delta_color="inverse")
        st.metric("Vel. Planeo Óptimo", f"{v_opt:.1f} km/h", f"{vz_opt:.2f} m/s", delta_color="inverse")
        
        if vz_opt > 0:
            ld_ratio = (v_opt - v_headwind) / 3.6 / vz_opt
            ld_text = f"{ld_ratio:.1f}"
        else:
            ld_text = "∞ (Ascenso)"
            
        st.metric("L/D Máximo Efectivo", ld_text)

with tab2:
    st.subheader("Visualización 3D: Tasa de Caída")
    st.markdown("Observa cómo varía la curva polar a lo largo de un tercer eje. Selecciona la variable que deseas explorar.")
    
    z_var = st.selectbox("Variable independiente (Eje Y del plot 3D):", 
                         ["Peso (kg)", "Ángulo de Inclinación (°)", "Masa de Aire Vertical (m/s)"])
    
    # El rango X base. Como el v_stall es dinámico según la variable Z, lo filtraremos durante la generación de Z.
    v_range = np.linspace(50, polar.V_NE, 40)
    
    if z_var == "Peso (kg)":
        y_range = np.linspace(292, 500, 40)
        X, Y = np.meshgrid(v_range, y_range)
        Z = np.zeros_like(X)
        for i in range(X.shape[0]):
            v_stall_row = polar.get_stall_speed(y_range[i], bank_angle)
            for j in range(X.shape[1]):
                if X[i, j] < v_stall_row:
                    Z[i, j] = np.nan # No renderizar puntos por debajo de la pérdida
                else:
                    Z[i, j] = polar.dynamic_polar(X[i, j], Y[i, j], bank_angle, v_air)
        y_title = "Peso (kg)"
        
    elif z_var == "Ángulo de Inclinación (°)":
        y_range = np.linspace(0, 60, 40)
        X, Y = np.meshgrid(v_range, y_range)
        Z = np.zeros_like(X)
        for i in range(X.shape[0]):
            v_stall_row = polar.get_stall_speed(weight, y_range[i])
            for j in range(X.shape[1]):
                if X[i, j] < v_stall_row:
                    Z[i, j] = np.nan
                else:
                    Z[i, j] = polar.dynamic_polar(X[i, j], weight, Y[i, j], v_air)
        y_title = "Inclinación (°)"
        
    else: # Masa de Aire Vertical
        y_range = np.linspace(-5, 5, 40)
        X, Y = np.meshgrid(v_range, y_range)
        Z = np.zeros_like(X)
        v_stall = polar.get_stall_speed(weight, bank_angle)
        for i in range(X.shape[0]):
            for j in range(X.shape[1]):
                if X[i, j] < v_stall:
                    Z[i, j] = np.nan
                else:
                    Z[i, j] = polar.dynamic_polar(X[i, j], weight, bank_angle, Y[i, j])
        y_title = "Masa de Aire (m/s)"

    # Plot 3D interactivo
    fig3d = go.Figure(data=[go.Surface(z=Z, x=X, y=Y, colorscale='Viridis')])
    
    fig3d.update_layout(
        title=f"Superficie Dinámica: Tasa de Caída vs Velocidad y {y_title}",
        scene=dict(
            xaxis_title="Vel. Ind. (km/h)",
            yaxis_title=y_title,
            zaxis_title="Tasa de Caída (m/s)",
            zaxis=dict(autorange="reversed") # Invertido para intuición de hundimiento
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        height=700
    )
    
    st.plotly_chart(fig3d, use_container_width=True)
