import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
import calendar
import io
import plotly.graph_objects as go
from backlog import check_stock_availability, update_stock_status

# Configuration des couleurs et du thème
COLORS = {
    "primary": "#3498db",       # Bleu principal
    "secondary": "#2ecc71",     # Vert secondaire
    "accent": "#e74c3c",        # Rouge accent
    "warning": "#f39c12",       # Orange assvertissement
    "info": "#9b59b6",          # Violet information
    "background": "#f8f9fa",    # Fond clair
    "text": "#2c3e50"           # Texte foncé
}

# Palette de couleurs pour les graphiques
CHART_COLORS = ["#3498db", "#2ecc71", "#e74c3c", "#f39c12", "#9b59b6"]

# Configuration de la page
st.set_page_config(
    layout="wide", 
    page_title="Gestion de Backlog 🗼",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# CSS amélioré pour masquer tous les éléments Streamlit non désirés
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stDeployButton {display:none;}
            .githubLink {display:none;}
            div[data-testid="stToolbar"] {visibility: hidden;}
            div[data-testid="stDecoration"] {visibility: hidden;}
            div[data-testid="stStatusWidget"] {visibility: hidden;}
            #stPathSelection {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
# Ajout de CSS personnalisé
st.markdown(f"""
<style>
    /* Style général */
    .main .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
    }}
    
    /* Style pour les titres */
    h1, h2, h3 {{
        color: {COLORS["primary"]};
        font-weight: bold;
        text-align: center;
        margin-top: 2rem;
        margin-bottom: 1.5rem;
    }}
    
    /* Style pour les sous-titres */
    h4, h5, h6 {{
        color: {COLORS["secondary"]};
        font-weight: 600;
        font-size: 1rem;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }}
    
    /* Style pour les métriques */
    .metric-container {{
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        border-left: 4px solid {COLORS["primary"]};
        margin-bottom: 2rem;
    }}
    
    /* Style pour les tableaux */
    .dataframe-container {{
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        padding: 15px;
        margin-bottom: 30px;
    }}
    
    /* Style pour les séparateurs */
    .custom-separator {{
        height: 2px;
        background-color: {COLORS["primary"] + "33"};
        margin: 2rem auto;
        width: 30%;
    }}
    
    /* Style des badges spécifiques */
    .badge {{
        padding: 6px 12px;
        border-radius: 4px;
        font-weight: bold;
        display: inline-block;
        text-align: center;
        margin-bottom: 15px;
    }}
    .badge-dispo {{
        background-color: {COLORS["secondary"]};
        color: white;
    }}
    .badge-pot-dispo {{
        background-color: {COLORS["warning"]};
        color: white;
    }}
    .badge-no-dispo {{
        background-color: {COLORS["accent"]};
        color: white;
    }}
    .badge-block {{
        background-color: {COLORS["text"]};
        color: white;
    }}
    .badge-completed {{
        background-color: {COLORS["info"]};
        color: white;
    }}
    
    /* Espacement supplémentaire entre les sections */
    .section-container {{
        margin-bottom: 40px;
    }}
    
    /* Style pour les sélecteurs de mois */
    .month-selector {{
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }}
    
    /* Style pour les résumés mensuels */
    .month-summary {{
        padding: 20px;
        background-color: {COLORS['background']};
        border-radius: 10px;
        border-left: 4px solid {COLORS['primary']};
        margin-bottom: 30px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }}
    
    /* Style pour les cartes de type de commande */
    .order-type-card {{
        text-align: center;
        padding: 15px;
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin: 10px;
    }}
    
    /* Style pour centrer les métriques */
    .stMetric {{
        text-align: center !important;
    }}
    
    /* Style pour enlever la marge supérieure des métriques */
    .stMetric div[data-testid="stMetricLabel"] {{
        margin-top: 0 !important;
    }}
    
    /* Style pour le positionnement des métriques */
    .stMetric div[data-testid="stMetricValue"] {{
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }}
    
    /* Style pour enlever la marge inférieure des métriques */
    .stMetric div[data-testid="stMetricDelta"] {{
        margin-bottom: 0 !important;
    }}
    
    /* Réduction de la largeur des conteneurs bleus */
    .order-metrics-section {{
        width: 85%;
        margin: 0 auto;
    }}
    
    /* Style pour corriger l'alignement des métriques */
    .metrics-row {{
        display: flex;
        justify-content: space-between;
    }}
    
    .metrics-row .metric-item {{
        flex: 1;
        text-align: center;
    }}
</style>
""", unsafe_allow_html=True)

# Ajouter le dictionnaire des mois en français
MOIS_FR = {
    1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
    5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
    9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
}

def format_currency(value):
    return f"{value:,.2f} €"

# Fonction pour créer un badge HTML coloré selon le type de commande
def get_order_type_badge(order_type):
    if order_type == "Dispo":
        return f'<span class="badge badge-dispo">Dispo</span>'
    elif order_type == "Potentiellement dispo":
        return f'<span class="badge badge-pot-dispo">Pot. dispo</span>'
    elif order_type == "No dispo":
        return f'<span class="badge badge-no-dispo">No dispo</span>'
    elif order_type == "Block":
        return f'<span class="badge badge-block">Block</span>'
    elif order_type == "Completed":
        return f'<span class="badge badge-completed">Completed</span>'
    return order_type

def create_order_metrics(merged_df):
    st.markdown('<div class="section-container order-metrics-section">', unsafe_allow_html=True)
    st.markdown("### 📊 Résumé des commandes", unsafe_allow_html=True)
    
    # Calcul des métriques
    total_orders = len(merged_df['Sales Document'].unique())
    total_value_all = merged_df['Open Value'].sum()
    
    # Calcul du nombre et de la valeur des commandes dispo jusqu'à la fin du mois en cours
    today = date.today()
    last_day_of_month = (date(today.year, today.month + 1, 1) if today.month < 12 else date(today.year + 1, 1, 1)) - timedelta(days=1)
    
    # Commandes dispo et potentiellement dispo jusqu'à la fin du mois en cours
    current_month_available = merged_df[
        ((merged_df['Order_Type'] == 'Dispo') | (merged_df['Order_Type'] == 'Potentiellement dispo')) & 
        (pd.to_datetime(merged_df['Last_Delivery_Date']).dt.date <= last_day_of_month)
    ]

    # Nombre de commandes uniques pour le mois en cours
    current_month_available_count = len(current_month_available['Sales Document'].unique())

    # Valeur totale pour le mois en cours
    current_month_available_value = current_month_available['Open Value'].sum()
    
    # Commandes dispo et potentiellement dispo jusqu'à aujourd'hui
    today_available = merged_df[
        ((merged_df['Order_Type'] == 'Dispo') | (merged_df['Order_Type'] == 'Potentiellement dispo')) & 
        (pd.to_datetime(merged_df['Last_Delivery_Date']).dt.date <= today)
    ]
    
    # Nombre de commandes uniques jusqu'à aujourd'hui
    today_available_count = len(today_available['Sales Document'].unique())
    
    # Valeur totale jusqu'à aujourd'hui
    today_available_value = today_available['Open Value'].sum()
    
    # Afficher les métriques principales avec HTML personnalisé pour éviter le décalage
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    
    # Utiliser HTML personnalisé pour créer les métriques alignées
    st.markdown(f'''
    <div class="metrics-row">
        <div class="metric-item">
            <div style="font-size: 0.9rem; font-weight: 600; color: rgba(38, 39, 48, 0.9);">Total des commandes</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: rgb(38, 39, 48);">{total_orders}</div>
            <div style="font-size: 0.9rem; color: rgb(38, 39, 48);">Valeur: {format_currency(total_value_all)}</div>
        </div>
        <div class="metric-item">
            <div style="font-size: 0.9rem; font-weight: 600; color: rgba(38, 39, 48, 0.9);">Dispo + Pot. dispo jusqu'à aujourd'hui</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: rgb(38, 39, 48);">{today_available_count}</div>
            <div style="font-size: 0.9rem; color: rgb(38, 39, 48);">Valeur: {format_currency(today_available_value)}</div>
        </div>
        <div class="metric-item">
            <div style="font-size: 0.9rem; font-weight: 600; color: rgba(38, 39, 48, 0.9);">Dispo + Pot. dispo jusqu'à fin {MOIS_FR[today.month]} {today.year}</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: rgb(38, 39, 48);">{current_month_available_count}</div>
            <div style="font-size: 0.9rem; color: rgb(38, 39, 48);">Valeur: {format_currency(current_month_available_value)}</div>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Séparateur avec largeur réduite
    st.markdown('<div class="custom-separator"></div>', unsafe_allow_html=True)
    
    # Métriques par type de commande avec styles améliorés
    order_types = {
        'Completed': merged_df[merged_df['Order_Type'] == 'Completed'],
        'Dispo': merged_df[merged_df['Order_Type'] == 'Dispo'],
        'Potentiellement dispo': merged_df[merged_df['Order_Type'] == 'Potentiellement dispo'],
        'No Dispo': merged_df[merged_df['Order_Type'] == 'No dispo'],
        'Block': merged_df[merged_df['Order_Type'] == 'Block']
    }
    
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    cols = st.columns(5)
    for i, (type_name, orders) in enumerate(order_types.items()):
        with cols[i]:
            unique_orders = len(orders['Sales Document'].unique())
            total_value = orders['Open Value'].sum()
            
            # Afficher le badge directement avec st.markdown pour un meilleur positionnement
            badge_label = "Pot. dispo" if type_name == "Potentiellement dispo" else type_name.replace("No Dispo", "No dispo")
            badge_class = "badge-completed" if type_name == "Completed" else \
                         "badge-dispo" if type_name == "Dispo" else \
                         "badge-pot-dispo" if type_name == "Potentiellement dispo" else \
                         "badge-no-dispo" if type_name == "No Dispo" else "badge-block"
            
            st.markdown(f'''
            <div style="text-align: center;">
                <span class="badge {badge_class}">{badge_label}</span>
            </div>
            ''', unsafe_allow_html=True)
            
            # Afficher la valeur et le montant
            st.markdown(f'''
            <div style="text-align: center;">
                <p style="font-size: 1.8rem; font-weight: bold; margin-bottom: 0.2rem;">{unique_orders}</p>
                <p style="color: {'green' if type_name != 'No Dispo' and type_name != 'Block' else 'red'}; margin-top: 0;">
                    ↑ {format_currency(total_value)}
                </p>
            </div>
            ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def plot_dispo_orders(merged_df):
    # Inclure à la fois les commandes dispo et potentiellement dispo
    dispo_orders = merged_df[(merged_df['Order_Type'] == 'Dispo') | (merged_df['Order_Type'] == 'Potentiellement dispo')]
    
    daily_orders = (
        dispo_orders.groupby(['Last_Delivery_Date', 'Sales Document', 'Order_Type'])
        .size()
        .reset_index()
    )
    
    # Créer un dataframe pour le graphique
    daily_summary = daily_orders.groupby(['Last_Delivery_Date', 'Order_Type']).size().reset_index()
    daily_summary.columns = ['Date', 'Type de commande', 'Nombre de commandes']
    
    # Créer le graphique avec des couleurs améliorées
    color_map = {
        'Dispo': COLORS["secondary"],
        'Potentiellement dispo': COLORS["warning"]
    }
    
    fig = px.line(
        daily_summary, 
        x='Date', 
        y='Nombre de commandes', 
        color='Type de commande',
        title="Répartition des commandes Dispo et Potentiellement dispo par Date de Disponibilité", 
        markers=True,
        color_discrete_map=color_map
    )
    
    fig.update_layout(
        xaxis_title="Date de Disponibilité",
        yaxis_title="Nombre de commandes",
        plot_bgcolor=COLORS["background"],
        paper_bgcolor=COLORS["background"],
        font=dict(color=COLORS["text"]),
        title={
            'text': "<b>Répartition des commandes Dispo et Potentiellement dispo par Date de Disponibilité</b>",
            'y': 0.95,
            'x': 0.0,
            'xanchor': 'left',
            'yanchor': 'top',
            'font': dict(color=COLORS["primary"], size=16)  # Couleur et taille pour le titre
        },
        legend_title_font=dict(color=COLORS["primary"]),
        legend=dict(
            bgcolor=COLORS["background"],
            bordercolor=COLORS["primary"]
        ),
        margin=dict(l=20, r=20, t=80, b=40)
    )
    
    return fig

def plot_dispo_orders_value(merged_df):
    # Inclure à la fois les commandes dispo et potentiellement dispo
    dispo_orders = merged_df[(merged_df['Order_Type'] == 'Dispo') | (merged_df['Order_Type'] == 'Potentiellement dispo')]
    
    # Grouper par date, numéro de commande et type pour obtenir la valeur
    daily_values = (
        dispo_orders.groupby(['Last_Delivery_Date', 'Order_Type'])['Open Value']
        .sum()
        .reset_index()
    )
    
    daily_values.columns = ['Date', 'Type de commande', 'Valeur des commandes']
    
    # Créer le graphique avec des couleurs améliorées
    color_map = {
        'Dispo': COLORS["secondary"],
        'Potentiellement dispo': COLORS["warning"]
    }
    
    fig = px.line(
        daily_values, 
        x='Date', 
        y='Valeur des commandes', 
        color='Type de commande',
        title="Valeur des commandes Dispo et Potentiellement dispo par Date de Disponibilité", 
        markers=True,
        color_discrete_map=color_map
    )
    
    fig.update_layout(
        xaxis_title="Date de Disponibilité",
        yaxis_title="Valeur des commandes (€)",
        plot_bgcolor=COLORS["background"],
        paper_bgcolor=COLORS["background"],
        font=dict(color=COLORS["text"]),
        title={
            'text': "<b>Valeur des commandes Dispo et Potentiellement dispo par Date de Disponibilité</b>",
            'y': 0.95,
            'x': 0.0,
            'xanchor': 'left',
            'yanchor': 'top',
            'font': dict(color=COLORS["primary"], size=16)  # Couleur et taille pour le titre
        },
        legend_title_font=dict(color=COLORS["primary"]),
        legend=dict(
            bgcolor=COLORS["background"],
            bordercolor=COLORS["primary"]
        ),
        margin=dict(l=20, r=20, t=80, b=40)
    )
    
    # Formatage des valeurs sur l'axe Y pour inclure le symbole €
    fig.update_yaxes(tickprefix="", ticksuffix=" €")
    
    return fig

def display_dispo_charts(merged_df):
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.markdown("### 📈 Analyse des commandes disponibles et Pot.dispo", unsafe_allow_html=True)
    
    # Afficher le premier graphique dans un conteneur stylisé
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    fig1 = plot_dispo_orders(merged_df)
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Ajouter un espace entre les graphiques
    #st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="custom-separator"></div>', unsafe_allow_html=True)
    
    # Afficher le second graphique dans un conteneur stylisé
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    fig2 = plot_dispo_orders_value(merged_df)
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def display_dispo_tables(merged_df):
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.markdown("### 📦 Commandes Dispo et Potentiellement dispo", unsafe_allow_html=True)
    today = date.today()
    start_of_month = date(today.year, today.month, 1)
    last_day_of_month = (date(today.year, today.month + 1, 1) if today.month < 12 else date(today.year + 1, 1, 1)) - timedelta(days=1)
    
    # Définir des styles pour les badges de type de commande
    st.markdown("""
    <style>
    .badge-dispo {
        background-color: #28a745;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    .badge-potentiellement-dispo {
        background-color: #ffc107;
        color: black;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Fonction pour obtenir la couleur selon le type de commande
    def get_order_type_badge(order_type):
        if order_type == 'Dispo':
            return "Dispo"
        elif order_type == 'Potentiellement dispo':
            return "Potentiellement dispo"
        else:
            return order_type
    
    # Fonction pour styliser l'affichage des tableaux
    def display_styled_table(df, title, total_value):
        st.markdown(f"##### {title}", unsafe_allow_html=True)
        st.markdown(f"**Total: <span style='color:{COLORS['accent']};'>{format_currency(total_value)}</span>**", unsafe_allow_html=True)
        
        if len(df) > 0:
            st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
            
            # Préparer le dataframe pour l'affichage
            display_df = df.copy()
            
            # Créer une fonction pour le formatage HTML dans st.dataframe
            def format_order_type(val):
                if val == 'Dispo':
                    return "🟢 Dispo"
                elif val == 'Potentiellement dispo':
                    return "🟡 Potentiellement dispo"
                else:
                    return val
            
            # Appliquer le formatage si la colonne Order_Type existe
            if 'Order_Type' in display_df.columns:
                display_df['Order_Type'] = display_df['Order_Type'].apply(format_order_type)
            
            st.dataframe(
                display_df, 
                hide_index=True, 
                column_config={
                    'Sales Document': st.column_config.TextColumn('N° Commande', help="Numéro de la commande"),
                    'Created on': st.column_config.DateColumn('Date création', format="DD/MM/YYYY"),
                    'Last_Delivery_Date': st.column_config.DateColumn('Date disponibilité', format="DD/MM/YYYY"),
                    'Order_Type': st.column_config.Column('Type de commande', help="Statut de disponibilité"),
                    'Total Value Order': st.column_config.NumberColumn('Valeur', format="%.2f €")
                },
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Aucune commande disponible pour cette période")
    
    # AJOUT: Tables supplémentaires avec style amélioré
    col1, col2 = st.columns(2)
    
    with col1:
        # Table de commandes dispo ce mois en fonction de la date de création
        current_month_dispo_creation = merged_df[(merged_df['Order_Type'] == 'Dispo') & 
                                              (pd.to_datetime(merged_df['Created on']).dt.date >= start_of_month) & 
                                              (pd.to_datetime(merged_df['Created on']).dt.date <= last_day_of_month)]
        
        current_month_dispo_unique = current_month_dispo_creation.drop_duplicates('Sales Document')[
            ['Sales Document', 'Created on', 'Last_Delivery_Date', 'Total Value Order']
        ].sort_values('Created on')
        
        # Ajouter la colonne Order_Type pour toutes les tables
        current_month_dispo_unique['Order_Type'] = 'Dispo'
        
        display_styled_table(
            current_month_dispo_unique,
            f"Commandes dispo du mois de {MOIS_FR[today.month]} {today.year}",
            current_month_dispo_creation['Open Value'].sum()
        )
    
    with col2:
        # Table de commandes dispo et potentiellement dispo en fonction de la date de livraison
        current_month_dispo_delivery = merged_df[
            ((merged_df['Order_Type'] == 'Dispo') | (merged_df['Order_Type'] == 'Potentiellement dispo')) & 
            (pd.to_datetime(merged_df['Last_Delivery_Date']).dt.date >= start_of_month) & 
            (pd.to_datetime(merged_df['Last_Delivery_Date']).dt.date <= last_day_of_month)
        ]
        
        current_month_all_dispo_unique = current_month_dispo_delivery.drop_duplicates('Sales Document')[
            ['Sales Document', 'Created on', 'Last_Delivery_Date', 'Order_Type', 'Total Value Order']
        ].sort_values('Last_Delivery_Date')
        
        display_styled_table(
            current_month_all_dispo_unique,
            f"Commandes dispo et potentiellement dispo du mois de {MOIS_FR[today.month]} {today.year}",
            current_month_dispo_delivery['Open Value'].sum()
        )
    
    # NOUVELLES TABLES avec style amélioré
    #st.markdown("---")
    st.markdown('<div class="custom-separator"></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        # Table pour toutes les commandes dispo et potentiellement dispo jusqu'à aujourd'hui
        dispo_until_today = merged_df[
            ((merged_df['Order_Type'] == 'Dispo') | (merged_df['Order_Type'] == 'Potentiellement dispo')) & 
            (pd.to_datetime(merged_df['Last_Delivery_Date']).dt.date <= today)
        ]
        
        dispo_until_today_unique = dispo_until_today.drop_duplicates('Sales Document')[
            ['Sales Document', 'Created on', 'Last_Delivery_Date', 'Order_Type', 'Total Value Order']
        ].sort_values('Last_Delivery_Date')
        
        display_styled_table(
            dispo_until_today_unique,
            f"Commandes dispo et potentiellement dispo jusqu'à aujourd'hui ({today})",
            dispo_until_today['Open Value'].sum()
        )
    
    with col2:
        # Table pour toutes les commandes dispo et potentiellement dispo jusqu'à la fin du mois en cours
        dispo_until_end_of_month = merged_df[
            ((merged_df['Order_Type'] == 'Dispo') | (merged_df['Order_Type'] == 'Potentiellement dispo')) & 
            (pd.to_datetime(merged_df['Last_Delivery_Date']).dt.date <= last_day_of_month)
        ]
        
        dispo_until_end_of_month_unique = dispo_until_end_of_month.drop_duplicates('Sales Document')[
            ['Sales Document', 'Created on', 'Last_Delivery_Date', 'Order_Type', 'Total Value Order']
        ].sort_values('Last_Delivery_Date')
        
        display_styled_table(
            dispo_until_end_of_month_unique,
            f"Commandes dispo et potentiellement dispo jusqu'à fin {MOIS_FR[today.month]} {today.year}",
            dispo_until_end_of_month['Open Value'].sum()
        )
    st.markdown('</div>', unsafe_allow_html=True)

def display_monthly_filter(merged_df):
    # CSS personnalisé pour améliorer la densité tout en gardant un peu d'espace
    st.markdown("""
    <style>
        /* Espacement modéré pour les sections */
        .section-container {
            padding: 0.75rem 0 !important;
            margin: 0.5rem 0 !important;
        }
        
        /* Cartes avec espacement modéré */
        .order-type-card {
            padding: 1rem !important;
            margin-bottom: 0.75rem !important;
            border-radius: 0.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        /* Badges avec taille modérée */
        .badge {
            padding: 0.3rem 0.6rem !important;
            border-radius: 0.25rem;
            font-size: 0.85rem;
            font-weight: bold;
            display: inline-block;
        }
        
        /* Styles spécifiques pour les badges */
        .badge-dispo {
            background-color: #28a745;
            color: white;
        }
        
        .badge-pot-dispo {
            background-color: #ffc107;
            color: black;
        }
        
        /* Espace modéré pour les en-têtes */
        h3, h4, h5 {
            margin: 0.75rem 0 !important;
            padding: 0 !important;
        }
        
        /* Espacement modéré pour les conteneurs de métriques */
        .metric-container {
            padding: 0.75rem 0 !important;
            margin: 0.5rem 0 !important;
        }
        
        /* Sélecteur de mois avec espacement modéré */
        .month-selector {
            padding: 0.5rem 0 !important;
            margin-bottom: 0.75rem !important;
        }
        
        /* Espace modéré pour les tableaux */
        .dataframe-container {
            margin: 0.75rem 0 !important;
        }
        
        /* Ajuster la taille des Select Box */
        .stSelectbox {
            margin-bottom: 0.75rem !important;
        }
    
        /* Espace modéré autour du tableau */
        [data-testid="stDataFrame"] {
            margin: 0.5rem 0 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Fonction auxiliaire pour créer les badges avec emoji
    def get_order_type_badge(order_type):
        if order_type == "Dispo":
            return '<span class="badge badge-dispo">🟢 Dispo</span>'
        elif order_type == "Potentiellement dispo":
            return '<span class="badge badge-pot-dispo">🟡 Potentiellement dispo</span>'
        else:
            return f'<span class="badge">{order_type}</span>'
    
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.markdown("### 📅 Commandes Dispo et Potentiellement dispo par mois", unsafe_allow_html=True)
    
    df_work = merged_df.copy()
    df_work['Last_Delivery_Date'] = pd.to_datetime(df_work['Last_Delivery_Date'], errors='coerce')
    
    # Inclure à la fois les commandes dispo et potentiellement dispo
    dispo_orders = df_work[
        ((df_work['Order_Type'] == 'Dispo') | (df_work['Order_Type'] == 'Potentiellement dispo')) & 
        (df_work['Last_Delivery_Date'].notna())
    ].copy()
    
    if len(dispo_orders) == 0:
        st.warning("Aucune commande Dispo ou Potentiellement dispo trouvée dans les données.")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    dispo_orders['Month_Year'] = dispo_orders['Last_Delivery_Date'].dt.strftime('%Y-%m')
    months = sorted(dispo_orders['Month_Year'].unique().tolist())
    
    if not months:
        st.error("Aucune donnée valide après le filtrage des dates.")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    if 'selected_month' not in st.session_state:
        st.session_state.selected_month = months[0]
    
    # Améliorer l'interface du sélecteur de mois
    st.markdown('<div class="month-selector">', unsafe_allow_html=True)
    st.markdown("##### Sélectionner un mois de disponibilité", unsafe_allow_html=True)
    selected_month = st.selectbox(
        "", 
        months, 
        index=months.index(st.session_state.selected_month),
        format_func=lambda x: f"{x[:4]} - {MOIS_FR[int(x[5:7])]}"  # Formater l'affichage
    )
    st.markdown('</div>', unsafe_allow_html=True)
    st.session_state.selected_month = selected_month
    
    filtered_orders = dispo_orders[dispo_orders['Month_Year'] == selected_month]
    
    if len(filtered_orders) == 0:
        st.info(f"Aucune commande trouvée pour {selected_month}")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    total_value = filtered_orders['Open Value'].sum()
    
    # Grouper par type de commande pour afficher les détails
    grouped_orders = filtered_orders.groupby('Order_Type').agg({
        'Open Value': 'sum',
        'Sales Document': lambda x: len(pd.unique(x))
    }).reset_index()
    
    # Afficher le résumé mensuel avec un style amélioré et compact
    st.markdown('<div class="month-summary">', unsafe_allow_html=True)
    year_month = selected_month.split('-')
    formatted_date = f"{MOIS_FR[int(year_month[1])]} {year_month[0]}"
    
    st.markdown(f"""
    <h4 style="color: {COLORS['primary']}; text-align: center; margin-bottom: 12px;">
        Résumé pour {formatted_date}
    </h4>
    <h3 style="color: {COLORS['accent']}; text-align: center; margin-top: 0;">
        Valeur totale: {format_currency(total_value)}
    </h3>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Afficher les détails des types de commande avec des cartes plus compactes
    st.markdown('<div class="metric-container" style="padding: 0.5rem 0;">', unsafe_allow_html=True)
    cols = st.columns(len(grouped_orders))
    
    for i, (_, row) in enumerate(grouped_orders.iterrows()):
        with cols[i]:
            order_type = row['Order_Type']
            badge_class = ""
            badge_emoji = ""
            badge_color = ""
            
            if order_type == "Dispo":
                badge_class = "badge-dispo"
                badge_color = COLORS["secondary"]
                badge_emoji = "🟢"
            elif order_type == "Potentiellement dispo":
                badge_class = "badge-pot-dispo"
                badge_color = COLORS["warning"]
                badge_emoji = "🟡"
            else:
                badge_color = COLORS["text"]
                badge_emoji = "⚪"
                
            st.markdown(f"""
            <div class="order-type-card" style="border-top: 3px solid {badge_color};">
                <span class="badge {badge_class}">{badge_emoji} {order_type}</span>
                <h3 style="margin-top: 8px; color: {COLORS['text']};">{row['Sales Document']}</h3>
                <p style="margin: 4px 0;">commandes</p>
                <h4 style="margin-top: 12px; color: {COLORS['accent']};">{format_currency(row['Open Value'])}</h4>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Détails des commandes avec un style compact
    st.markdown("##### Détails des commandes", unsafe_allow_html=True)
    
    # Préparer les données pour l'affichage
    unique_orders = filtered_orders.drop_duplicates(subset=['Sales Document'])[
        ['Sales Document', 'Created on', 'Last_Delivery_Date', 'Order_Type', 'Total Value Order']
    ].sort_values('Last_Delivery_Date')

    # Avant d'afficher le dataframe, ajoutez les émojis à la colonne Order_Type
    unique_orders['Order_Type'] = unique_orders['Order_Type'].apply(lambda x: 
        f"🟢 {x}" if x == "Dispo" else 
        f"🟡 {x}" if x == "Potentiellement dispo" else x
    )
        
    # Afficher directement le DataFrame avec la bonne configuration de colonnes
    st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
    st.dataframe(
        unique_orders, 
        hide_index=True, 
        column_config={
            'Sales Document': st.column_config.TextColumn('N° Commande', help="Numéro de la commande"),
            'Created on': st.column_config.DateColumn('Date création', format="DD/MM/YYYY"),
            'Last_Delivery_Date': st.column_config.DateColumn('Date disponibilité', format="DD/MM/YYYY"),
            'Order_Type': st.column_config.Column('Type de commande', help="Statut de disponibilité"),
            'Total Value Order': st.column_config.NumberColumn('Valeur', format="%.2f €")
        },
        use_container_width=True
    )
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def display_completed_orders(merged_df):
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.markdown("### ✅ Commandes Completed et Block", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    # Fonction pour afficher une table stylisée
    def display_styled_order_table(df, title, total_value):
        st.markdown(f"##### {title}", unsafe_allow_html=True)
        st.markdown(
            f"""<div style="padding: 15px; background-color: {COLORS['background']}; 
            border-radius: 10px; border-left: 4px solid {COLORS['info'] if title == 'Commandes Completed' else COLORS['text']}; 
            margin-bottom: 20px;">
            <p>Total: <span style="color: {COLORS['accent']}; font-weight: bold;">{format_currency(total_value)}</span></p>
            </div>""",
            unsafe_allow_html=True
        )
        
        if len(df) > 0:
            st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
            st.dataframe(
                df, 
                hide_index=True, 
                column_config={
                    'Sales Document': st.column_config.TextColumn('N° Commande', help="Numéro de la commande"),
                    'Created on': st.column_config.DateColumn('Date création', format="DD/MM/YYYY"),
                    'Total Value Order': st.column_config.NumberColumn('Valeur', format="%.2f €")
                },
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info(f"Aucune commande de type {title} trouvée")
    
    with col1:
        # Affichage des commandes Completed avec style
        completed_orders = merged_df[merged_df['Order_Type'] == 'Completed']
        completed_unique = completed_orders.drop_duplicates('Sales Document')[
            ['Sales Document', 'Created on', 'Total Value Order']
        ].sort_values('Created on')
        
        display_styled_order_table(
            completed_unique, 
            "Commandes Completed", 
            completed_orders['Open Value'].sum()
        )
    
    with col2:
        # Affichage des commandes Block avec style
        block_orders = merged_df[merged_df['Order_Type'] == 'Block']
        block_unique = block_orders.drop_duplicates('Sales Document')[
            ['Sales Document', 'Created on', 'Total Value Order']
        ].sort_values('Created on')
        
        display_styled_order_table(
            block_unique, 
            "Commandes Block", 
            block_orders['Open Value'].sum()
        )
    st.markdown('</div>', unsafe_allow_html=True)

def display_no_dispo_orders(merged_df):
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.markdown("### ❌ Commandes No Dispo", unsafe_allow_html=True)
    
    no_dispo_orders = merged_df[merged_df['Order_Type'] == 'No dispo']
    total_value = no_dispo_orders['Open Value'].sum()
    
    # Afficher des métriques résumées dans un conteneur stylisé
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        # Application d'un style CSS personnalisé pour aligner le texte
        st.markdown(
            f"""
            <div style="text-align: left;">
                <p style="margin-bottom: 0;">Nombre de commandes No Dispo</p>
                <p style="font-size: 2.5rem; font-weight: bold; margin-top: 0;">{len(no_dispo_orders['Sales Document'].unique())}</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"""
            <div style="text-align: left;">
                <p style="margin-bottom: 0;">Valeur totale No Dispo</p>
                <p style="font-size: 2.5rem; font-weight: bold; margin-top: 0;">{format_currency(total_value)}</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("##### Liste des commandes non disponibles", unsafe_allow_html=True)
    no_dispo_products = no_dispo_orders[no_dispo_orders['Updated_Stock_Status'] == 'No dispo']
    
    if len(no_dispo_products) > 0:
        # Regrouper les données par commande
        no_dispo_summary = no_dispo_products.groupby('Sales Document').agg({
            'Created on': 'first',
            'Y Material': lambda x: ', '.join(str(item) for item in x),
            'Type': lambda x: ', '.join(str(item) for item in x),
            'MRP Controller': lambda x: ', '.join(str(item) for item in x),
            'Updated_Remaining_Quantity': lambda x: ', '.join(map(str, x)),
            'Total Value Order': 'first'
        }).reset_index()
        
        # Afficher la table avec un style cohérent
        st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
        #st.markdown('<div class="custom-separator"></div>', unsafe_allow_html=True)
        st.dataframe(
            no_dispo_summary, 
            hide_index=True, 
            column_config={
                'Sales Document': st.column_config.TextColumn('N° Commande', help="Numéro de la commande"),
                'Created on': st.column_config.DateColumn('Date création', format="DD/MM/YYYY"),
                'Y Material': st.column_config.TextColumn('Produits no dispo', help="Produits non disponibles"),
                'Type': st.column_config.TextColumn('Type', help="Type de produit"),
                'MRP Controller': st.column_config.TextColumn('MRP Controller', help="Contrôleur MRP"),
                'Updated_Remaining_Quantity': st.column_config.TextColumn('Quantité manquante', help="Quantité de produits non disponibles"),
                'Total Value Order': st.column_config.NumberColumn('Valeur', format="%.2f €")
            },
            use_container_width=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Aucune commande de type 'No dispo' trouvée dans les données.")
    
    st.markdown('</div>', unsafe_allow_html=True)


def process_backlog_data(backlog, salesUOM, export, Puom, kit, MRP, securoc_df):
    try:
        # Convertir tous les Sales Document en chaînes de caractères
        backlog['Sales Document'] = backlog['Sales Document'].astype(str)
        backlog = backlog.iloc[1:]


        # Préparer le fichier Securoc
        securoc_df = securoc_df[['Material', 'Pegged reqmt']]
        securoc_df = securoc_df.rename(columns={'Material': 'Component', 'Pegged reqmt': 'Y Material'})

        # Vérifier les colonnes requises dans le fichier backlog
        required_columns = ['Y Material', 'Sales Document', 'Created on', 'Open Value']
        missing_columns = [col for col in required_columns if col not in backlog.columns]
        if missing_columns:
            raise ValueError(f"Colonnes manquantes dans le fichier backlog: {missing_columns}")

        # Nettoyer le fichier Kit
        kit = kit.rename(columns={'Header': 'Y Material'})
        kit = kit[['Y Material', 'Header MRP Controller', 'Component']]

        # Prétraitement des fichiers
        backlog = backlog.replace('pak', 'pac')
        backlog = backlog[backlog['Y Material'] != 'Y4963053']

        # Sélection des colonnes nécessaires
        colonnes = [
            'Created on', 'Sales Document', 'Requested Delivery Date', 'Sales UOM', 'Base UOM',
            'Header Delivery Block', 'Line Delivery Block', 'Y Material', 'MRP Controller',
            'MRP Group', 'Vendor PO #', 'Open Value', 'Open Order Quantity', 'On Hand Quantity',
            'Delivery Qty - Complete', 'ATP QTY','DropShip'
        ]
        missing_cols = [col for col in colonnes if col not in backlog.columns]
        if missing_cols:
            raise ValueError(f"Colonnes manquantes dans le fichier backlog: {missing_cols}")
        backlog = backlog[colonnes].copy()

        # Créer un identifiant unique pour chaque ligne du backlog
        backlog['original_index'] = backlog.index

        # Fusion avec MRP pour obtenir les types
        if 'MRP Controller' not in MRP.columns or 'Type' not in MRP.columns:
            raise ValueError("Le fichier MRP doit contenir les colonnes 'MRP Controller' et 'Type'")
        MRP = MRP[['MRP Controller', 'Type']]
        mrp_dict = MRP.set_index('MRP Controller')['Type'].to_dict()
        backlog['Type'] = backlog['MRP Controller'].map(mrp_dict)

        # Traitement des types spéciaux
        backlog.loc[(backlog['MRP Controller'] == 'M70') & (backlog['Y Material'] == 'Y4950101'), 'Type'] = 'SECUROC'
        backlog.loc[(backlog['MRP Controller'] == 'M70') & (backlog['Y Material'] == 'Y4950100'), 'Type'] = 'BUY'

        # Préparer le fichier Sales UOM
        salesUOM = salesUOM.rename(columns={'Étiquettes de lignes': 'Y Material'})
        salesUOM = salesUOM.drop('Alternative Unit of Measure', axis=1)

        # Vérifier les colonnes requises dans le fichier Sales UOM
        required_sales_cols = ['Y Material', 'Counter']
        if not all(col in salesUOM.columns for col in required_sales_cols):
            raise ValueError("Le fichier Sales UOM doit contenir les colonnes 'Y Material' et 'Counter'")
        backlog = pd.merge(backlog, salesUOM, on='Y Material', how='left')

        # Remplacer les valeurs NaN dans Counter par 1 (pour les matériels qui ne sont pas dans salesUOM)
        backlog['Counter'] = backlog['Counter'].fillna(1)

        # Préparer le fichier Export
        required_export_cols = ['Purchasing Document', 'Delivery date', 'Y Material', 'Order Unit', 'Sch Opn Qty']
        export = export.rename(columns={'Material': 'Y Material'})
        export = export[required_export_cols]

        # Initialiser et calculer Qte_sales
        backlog['Qte_sales'] = 0.0
        try:
            backlog.loc[(backlog['Sales UOM'] == 'EA') & (backlog['Base UOM'] == 'PC'), 'Qte_sales'] = backlog['Open Order Quantity'].astype(float)
            backlog.loc[(backlog['Sales UOM'] == 'PC') & (backlog['Base UOM'] == 'EA'), 'Qte_sales'] = backlog['Open Order Quantity'].astype(float)
            backlog.loc[backlog['Sales UOM'] == backlog['Base UOM'], 'Qte_sales'] = backlog['Open Order Quantity'].astype(float)
            backlog.loc[backlog['Sales UOM'] != backlog['Base UOM'], 'Qte_sales'] = (backlog['Open Order Quantity'] * backlog['Counter']).astype(float)
        except Exception as e:
            raise ValueError(f"Erreur lors du calcul de Qte_sales: {str(e)}")

        # Préparer le fichier PUOM
        required_puom_cols = ['Material', 'Order Unit', 'PUOM', 'Base UOM']
        if not all(col in Puom.columns for col in required_puom_cols):
            raise ValueError(f"Colonnes manquantes dans le fichier Puom: {[col for col in required_puom_cols if col not in Puom.columns]}")
        Puom = Puom.rename(columns={'Material': 'Y Material'})
        Puom = Puom[['Y Material', 'Order Unit', 'PUOM', 'Base UOM']]

        # Fusionner Export et PUOM
        SuppOrder = pd.merge(export, Puom, on='Y Material', how='left')
        SuppOrder['Order Unit_y'] = SuppOrder['Order Unit_y'].fillna('PC')
        SuppOrder['Base UOM'] = SuppOrder['Base UOM'].fillna('PC')
        SuppOrder['PUOM'] = SuppOrder['PUOM'].fillna(1)
        SuppOrder['Qty_Purchasing'] = SuppOrder['PUOM'] * SuppOrder['Sch Opn Qty']
        colonneSuppOrder = ['Purchasing Document', 'Y Material', 'Delivery date', 'Base UOM', 'Qty_Purchasing']
        SuppOrder = SuppOrder[colonneSuppOrder]

        # Déterminer le statut des lignes backlog
        backlog.loc[(backlog['Open Order Quantity'] == backlog['Delivery Qty - Complete']), 'Statut'] = 'Completed'
        backlog.loc[(backlog['Open Order Quantity'] != backlog['Delivery Qty - Complete']) &
                    (backlog['Header Delivery Block'] == 'No Block') &
                    (backlog['Line Delivery Block'] == 'No Block'), 'Statut'] = 'No Block'
        backlog.loc[backlog['Statut'].isnull(), 'Statut'] = 'Block'

        # Vérifier la disponibilité des stocks
        resultat = check_stock_availability(backlog, SuppOrder, kit, securoc_df)
        if isinstance(resultat, str):
            raise ValueError(f"Erreur dans check_stock_availability: {resultat}")

        # Mettre à jour les statuts des stocks
        merged_df = update_stock_status(resultat, SuppOrder, kit, securoc_df)
        if isinstance(merged_df, str):
            raise ValueError(f"Erreur dans update_stock_status: {merged_df}")


        # Finalisation du traitement
        merged_df['Sales Document'] = merged_df['Sales Document'].astype(str)
        merged_df['Total Value Order'] = merged_df.groupby('Sales Document')['Open Value'].transform('sum')

         # Fonction pour déterminer le type de commande
        def determine_order_type(group):
            statuses = set(group)
            
            # Block si au moins une ligne est Block
            if 'Block' in statuses:
                return 'Block'
            
            # No dispo si au moins une ligne est No dispo
            elif 'No dispo' in statuses:
                return 'No dispo'
            
            # Completed si toutes les lignes sont Completed
            elif statuses == {'Completed'}:
                return 'Completed'
            
            # Dispo si toutes les lignes sont Dispo ou (on trouve Dispo et Completed)
            elif statuses == {'Dispo'} or statuses == {'Dispo', 'Completed'}:
                return 'Dispo'
            
            # Potentiellement dispo dans plusieurs cas
            elif (statuses == {'Potentiellement dispo'} or  # toutes potentiellement dispo
                statuses == {'Potentiellement dispo', 'Dispo'} or  # potentiellement dispo et dispo
                statuses == {'Potentiellement dispo', 'Completed'} or  # potentiellement dispo et completed
                statuses == {'Potentiellement dispo', 'Dispo', 'Completed'}):  # les trois types
                return 'Potentiellement dispo'
            
            # Autres cas
            else:
                return 'Others'

        # Application de la logique de type de commande mise à jour
        merged_df['Order_Type'] = merged_df.groupby('Sales Document')['Updated_Stock_Status'].transform(
            lambda x: determine_order_type(x)
        )

        merged_df['Last_Delivery_Date'] = merged_df.groupby('Sales Document')['Last_Delivery_Date'].transform('max')


        # Nettoyage final
        merged_df = merged_df.sort_values('original_index')
        merged_df = merged_df.drop('original_index', axis=1)

        return merged_df

    except Exception as e:
        print(f"Erreur détaillée dans process_backlog_data: {str(e)}")
        raise Exception(f"Erreur lors du traitement des données: {str(e)}")

def main():
    with st.sidebar:
        # Image en tout haut sans marge
        st.markdown('<div style="margin-top:-2rem;">', unsafe_allow_html=True)
        st.image("signalImage.png", width=230)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Titre avec espacement minimal
        st.markdown('<h3 style="margin-top:-1rem; margin-bottom:0.5rem;">Gestion de Backlog 🗼</h3>', unsafe_allow_html=True)
        
        # Import des fichiers directement sous le titre
        st.markdown('<p style="color:black; margin-top:0; margin-bottom:0.3rem; font-weight:bold;">📂 Import des fichiers</p>', unsafe_allow_html=True)
        
        # File uploaders avec noms visibles
        files = {
            "Backlog": st.file_uploader("Fichier Backlog", type=["xlsx"], key="backlog"),
            "Sales UOM": st.file_uploader("Fichier Sales UOM", type=["xlsx"], key="sales"),
            "Orders": st.file_uploader("Fichier Orders To Suppliers ZMM13", type=["xlsx","XLSX"], key="orders"),
            "PUOM": st.file_uploader("Fichier PUOM", type=["xlsx"], key="puom"),
            "Kits": st.file_uploader("Fichier Kits", type=["xlsx"], key="kits"),
            "MRP": st.file_uploader("Fichier MRP", type=["xlsx"], key="mrp"),
            "Securoc": st.file_uploader("Fichier Securoc No Dispo", type=["xlsx"], key="securoc")
        }

    # Le reste du code reste inchangé
    if all(files.values()):
        if 'merged_df' not in st.session_state:
            with st.spinner("Traitement en cours..."):
                df_dict = {name: pd.read_excel(file) for name, file in files.items()}
                merged_df = process_backlog_data(
                    df_dict["Backlog"], df_dict["Sales UOM"], df_dict["Orders"],
                    df_dict["PUOM"], df_dict["Kits"], df_dict["MRP"], df_dict["Securoc"]
                )
                st.session_state.merged_df = merged_df
        else:
            merged_df = st.session_state.merged_df

        # Afficher les composants
        create_order_metrics(merged_df)
        display_dispo_charts(merged_df)
        display_dispo_tables(merged_df)
        display_monthly_filter(merged_df)
        display_completed_orders(merged_df)
        display_no_dispo_orders(merged_df)
        
        # Export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            merged_df.to_excel(writer, index=False, sheet_name='Données_Complètes')
        
        st.sidebar.download_button(
            label="📥 Télécharger le rapport",
            data=output.getvalue(),
            file_name="Rapport_Backlog.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.info("👈 Veuillez importer tous les fichiers nécessaires dans le menu latéral pour commencer l'analyse.")

if __name__ == "__main__":
    main()
