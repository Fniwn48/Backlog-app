import numpy as np
import pandas as pd

def check_stock_availability(df, df1, kits_df, securoc_df):
    try:
        # 🚀 Nettoyage et validation des DataFrames
        df['Sales Document'] = df['Sales Document'].astype(str).str.strip()
        df1['Purchasing Document'] = df1['Purchasing Document'].astype(str).str.strip()

        # ✅ Vérification des colonnes essentielles
        required_columns = ['Statut', 'MRP Controller', 'Vendor PO #', 'Y Material',
                          'Sales Document', 'On Hand Qty', 'Qte_sales', 'Open Value', 'Created on', 'Type', 'DropShip']

        if not set(required_columns).issubset(df.columns):
            raise ValueError(f"❌ Colonnes manquantes dans df: {set(required_columns) - set(df.columns)}")

        # 🏗️ Création du DataFrame de sortie
        result_df = df.copy()
        result_df['Stock_Status'] = 'x'
        result_df['Remaining_Quantity'] = result_df['On Hand Qty']
        result_df['Sort_Order'] = 0
        result_df['Created on'] = pd.to_datetime(result_df['Created on'], format='%m/%d/%Y', errors='coerce')

        # 🏷️ Calcul de la valeur totale par Sales Document
        result_df['Total Value Order'] = result_df.groupby('Sales Document')['Open Value'].transform('sum')

        # ✅ Gestion des statuts
        completed_mask = result_df['Statut'] == 'Completed'
        result_df.loc[completed_mask, 'Stock_Status'] = 'Completed'
        result_df.loc[completed_mask, 'Sort_Order'] = -1

        block_mask = result_df['Statut'] == 'Block'
        blocked_sales_documents = result_df[block_mask]['Sales Document'].unique()

        # Mettre à jour le Stock_Status, Statut et Sort_Order pour les commandes bloquées
        for sales_doc in blocked_sales_documents:
            result_df.loc[result_df['Sales Document'] == sales_doc, ['Stock_Status', 'Statut', 'Sort_Order']] = ['Block', 'Block', -1]

        # Création du masque pour "No Block"
        no_block_mask = result_df['Statut'] == 'No Block'
        
        # Traitement des lignes No Block
        no_block_rows = result_df[no_block_mask].copy()
        
        for idx, row in no_block_rows.iterrows():
            vendor_po = str(row['Vendor PO #'])
            y_material = row['Y Material']
            
            # Vérification pour Vendor PO
            if vendor_po != '-':
                # Vérifier si Vendor PO existe dans df1["Purchasing Document"]
                vendor_exists = df1['Purchasing Document'].eq(vendor_po).any()
                
                if vendor_exists:
                    # Vérifier si Y Material correspond entre df et df1
                    material_match = df1[(df1['Purchasing Document'] == vendor_po) & 
                                         (df1['Y Material'] == y_material)].shape[0] > 0
                    
                    if material_match:
                        result_df.loc[idx, 'Stock_Status'] = 'Potentiellement dispo'
                        result_df.loc[idx, 'Remaining_Quantity'] = 0
                    else:
                        result_df.loc[idx, 'Stock_Status'] = 'Completed'
                else:
                    result_df.loc[idx, 'Stock_Status'] = 'Completed'
        
        # 🔒 Gestion des produits SECUROC (seulement pour ceux qui n'ont pas encore été traités)
        securoc_mask = no_block_mask & (result_df['Type'] == 'SECUROC') & (result_df['Stock_Status'] == 'x')
        securoc_materials = securoc_df['Y Material'].unique() if 'Y Material' in securoc_df.columns else []

        for idx, row in result_df[securoc_mask].iterrows():
            result_df.at[idx, 'Stock_Status'] = 'No dispo' if row['Y Material'] in securoc_materials else 'Dispo'

        # Tri des produits SECUROC avec Stock_Status = 'x'
        securoc_to_sort_mask = securoc_mask & (result_df['Stock_Status'] == 'x')
        for material, group in result_df[securoc_to_sort_mask].groupby('Y Material'):
            temp_group = group.copy()
            sort_order = 1  # Réinitialisation du compteur pour chaque groupe
            temp_group = temp_group.sort_values('Created on', ascending=True)

            # Tri par date
            for date, date_group in temp_group.groupby('Created on'):
                # Si plusieurs commandes à la même date
                if len(date_group) > 1:
                    all_rw = all(str(x).startswith("RW") for x in date_group['Sales Document'])
                    all_numeric = all(not str(x).startswith("RW") for x in date_group['Sales Document'])

                    if all_rw:
                        # Pour les commandes RW, trier par les 5 derniers chiffres
                        date_group['numeric_part'] = date_group['Sales Document'].apply(
                            lambda x: int(str(x)[-5:]) if str(x)[-5:].isdigit() else float('inf')
                        )
                        sorted_indices = date_group.sort_values('numeric_part', ascending=True).index
                    elif all_numeric:
                        # Pour les commandes numériques, tri simple
                        sorted_indices = date_group.sort_values('Sales Document', ascending=True).index
                    else:
                        # Si mélange de types, tri par valeur totale de commande
                        sorted_indices = date_group.sort_values('Total Value Order', ascending=False).index
                else:
                    sorted_indices = date_group.index

                # Attribution des Sort_Order pour ce groupe de date
                for idx in sorted_indices:
                    result_df.at[idx, 'Sort_Order'] = sort_order
                    sort_order += 1

        # 📌 Gestion des Produits No Block et non SECUROC (hors M80) qui n'ont pas encore été traités
        non_securoc_mask = (no_block_mask &
                          ~result_df['MRP Controller'].isin(['M80']) &
                          (result_df['Type'] != 'SECUROC') &
                          (result_df['Stock_Status'] == 'x'))

        for material, group in result_df[non_securoc_mask].groupby('Y Material'):
            temp_group = group.copy()
            sort_order = 1  # Réinitialisation du compteur pour chaque groupe
            remaining_quantity = temp_group.iloc[0]['On Hand Qty']
            temp_group = temp_group.sort_values('Created on', ascending=True)

            # Tri par date
            for date, date_group in temp_group.groupby('Created on'):
                # Si plusieurs commandes à la même date
                if len(date_group) > 1:
                    all_rw = all(str(x).startswith("RW") for x in date_group['Sales Document'])
                    all_numeric = all(not str(x).startswith("RW") for x in date_group['Sales Document'])

                    if all_rw:
                        # Pour les commandes RW, trier par les 5 derniers chiffres
                        date_group['numeric_part'] = date_group['Sales Document'].apply(
                            lambda x: int(str(x)[-5:]) if str(x)[-5:].isdigit() else float('inf')
                        )
                        sorted_indices = date_group.sort_values('numeric_part', ascending=True).index
                    elif all_numeric:
                        # Pour les commandes numériques, tri simple
                        sorted_indices = date_group.sort_values('Sales Document', ascending=True).index
                    else:
                        # Si mélange de types, tri par valeur totale de commande
                        sorted_indices = date_group.sort_values('Total Value Order', ascending=False).index
                else:
                    sorted_indices = date_group.index

                # Attribution des Sort_Order et calcul des disponibilités
                for idx in sorted_indices:
                    row = temp_group.loc[idx]
                    result_df.at[idx, 'Sort_Order'] = sort_order
                    sort_order += 1

                    if remaining_quantity > 0:
                        if remaining_quantity >= row['Qte_sales']:
                            result_df.at[idx, 'Stock_Status'] = 'Dispo'
                            remaining_quantity -= row['Qte_sales']
                        else:
                            result_df.at[idx, 'Stock_Status'] = 'No dispo'
                            remaining_quantity -= row['Qte_sales']
                    else:
                        result_df.at[idx, 'Stock_Status'] = 'No dispo'
                        remaining_quantity = -row['Qte_sales']

                    result_df.at[idx, 'Remaining_Quantity'] = remaining_quantity

        # 📦 Gestion des Kits (MRP Controller == M80)
        m80_mask = no_block_mask & (result_df['MRP Controller'] == 'M80') & (result_df['Stock_Status'] == 'x')
        for idx, row in result_df[m80_mask].iterrows():
            result_df.at[idx, 'Sort_Order'] = 0
            kit_number = row['Y Material']
            kit_components = kits_df[kits_df['Y Material'] == kit_number]

            all_available = True
            for _, kit_row in kit_components.iterrows():
                component_rows = result_df[
                    (result_df['Y Material'] == kit_row['Component']) &
                    (result_df['Sales Document'] == row['Sales Document'])
                ]

                if component_rows.empty or component_rows['Stock_Status'].values[0] != 'Dispo':
                    all_available = False
                    break

            result_df.at[idx, 'Stock_Status'] = 'Dispo' if all_available else 'No dispo'

        return result_df

    except Exception as e:
        print(f"Erreur détaillée: {str(e)}")  # Pour le debugging
        return f"🔴 Unexpected Error: {type(e).__name__}: {e}"
    


def update_stock_status(result_df, export_df, kits_df, securoc_df):
    """
    Met à jour les statuts de stock en fonction des commandes fournisseurs et des livraisons prévues.
    Version mise à jour: 
    - Traite uniquement les lignes No Block et No dispo
    - Exclut les MRP Controller M50 et M32
    - Les lignes déjà traitées dans df1 ne sont pas revues
    """
    try:
        # Convertir les dates pour éviter les erreurs
        result_df['Created on'] = pd.to_datetime(result_df['Created on'], format='%m/%d/%Y', errors='coerce')
        export_df['Delivery date'] = pd.to_datetime(export_df['Delivery date'], format='%m/%d/%Y', errors='coerce')

        # Ajouter les nouvelles colonnes
        result_df['Updated_Stock_Status'] = result_df['Stock_Status']
        result_df['Last_Delivery_Date'] = result_df['Created on']
        result_df['Updated_Remaining_Quantity'] = result_df['Remaining_Quantity']

        # 1. Garder les produits Completed, Block, Dispo et Potentiellement dispo inchangés
        completed_mask = result_df['Stock_Status'] == 'Completed'
        block_mask = result_df['Stock_Status'] == 'Block'
        dispo_mask = result_df['Stock_Status'] == 'Dispo'
        
        unchanged_mask = completed_mask | block_mask | dispo_mask
        result_df.loc[unchanged_mask, 'Updated_Stock_Status'] = result_df['Stock_Status']
        result_df.loc[unchanged_mask, 'Last_Delivery_Date'] = result_df['Created on']
        result_df.loc[unchanged_mask, 'Updated_Remaining_Quantity'] = result_df['Remaining_Quantity']

        potentiellement_dispo_mask = result_df['Stock_Status'] == 'Potentiellement dispo'
        
        for idx, row in result_df[potentiellement_dispo_mask].iterrows():
            vendor_po = str(row['Vendor PO #'])
            y_material = row['Y Material']
            
            if vendor_po != '-':
                # Trouver la ligne correspondante dans export_df
                for _, export_row in export_df.iterrows():
                    if (export_row['Purchasing Document'] == vendor_po and 
                        export_row['Y Material'] == y_material):
                        delivery_date = export_row['Delivery date']
                        result_df.loc[idx, 'Last_Delivery_Date'] = delivery_date
                        result_df.loc[idx, 'Updated_Stock_Status'] = 'Potentiellement dispo'

        # 2. Filtrer uniquement pour les produits No Block et No dispo, en excluant M50 et M32
        no_block_no_dispo_mask = (
            (result_df['Stock_Status'] == 'No dispo') & 
            (result_df['Statut'] == 'No Block') &
            (result_df['MRP Controller'] != 'M50') &
            (result_df['MRP Controller'] != 'M32')
        )
        
        # Créons une liste des combinaisons Vendor PO + Y Material déjà traitées
        already_processed = set()
        for idx, row in result_df[potentiellement_dispo_mask].iterrows():
            vendor_po = str(row['Vendor PO #'])
            y_material = row['Y Material']
            if vendor_po != '-':
                already_processed.add((vendor_po, y_material))
        
        # Filtrer les lignes d'export_df qui ont déjà été traitées
        filtered_export_df = export_df.copy()
        rows_to_drop = []
        
        for idx, row in filtered_export_df.iterrows():
            purchasing_doc = row['Purchasing Document']
            y_material = row['Y Material']
            if (purchasing_doc, y_material) in already_processed:
                rows_to_drop.append(idx)
        
        filtered_export_df = filtered_export_df.drop(rows_to_drop)
        
        # 2.1 Gérer les produits SECUROC
        securoc_mask = no_block_no_dispo_mask & (result_df['Type'] == 'SECUROC') & (result_df['MRP Controller'] != 'M80')

        # Obtenir tous les composants uniques de SECUROC
        all_components = securoc_df['Component'].unique()

        # Dictionnaire pour stocker le stock restant de chaque composant
        component_stock = {comp: 0 for comp in all_components}
        # Dictionnaire pour stocker l'index de livraison courant
        delivery_indexes = {comp: 0 for comp in all_components}
        # Dictionnaire pour stocker les livraisons de chaque composant
        component_deliveries = {}

        # Précharger toutes les livraisons de composants (en utilisant filtered_export_df)
        for component in all_components:
            component_deliveries[component] = filtered_export_df[
                filtered_export_df['Y Material'] == component
            ].sort_values('Delivery date').reset_index(drop=True)

        # Trier les YMaterials de SECUROC par date de création
        securoc_ymaterials = securoc_df['Y Material'].unique()
        securoc_products = result_df[
            securoc_mask & 
            result_df['Y Material'].isin(securoc_ymaterials)
        ].sort_values(by=['Created on']).reset_index()

        # Traiter chaque produit SECUROC dans l'ordre
        for idx, product in securoc_products.iterrows():
            ymaterial = product['Y Material']
            required_qty = abs(product['Qte_sales'])  # Utiliser Qte_sales au lieu de ATP QTY
            product_idx = product['index']  # Index original dans result_df
            
            # Obtenir tous les composants nécessaires pour ce YMaterial
            needed_components = securoc_df[securoc_df['Y Material'] == ymaterial]['Component'].unique()
            
            all_components_available = True
            component_status = {}
            latest_delivery_date = None
            
            # Vérifier et mettre à jour la disponibilité de chaque composant
            for component in needed_components:
                is_available = False
                delivery_date = None
                
                # Vérifier si le stock restant est suffisant
                if component_stock[component] >= required_qty:
                    is_available = True
                    # Utiliser la date de la dernière livraison utilisée
                    delivery_date = component_deliveries[component].iloc[delivery_indexes[component]-1]['Delivery date'] if delivery_indexes[component] > 0 else None
                else:
                    # Récupérer les livraisons de ce composant
                    comp_deliveries = component_deliveries[component]
                    total_deliveries = len(comp_deliveries)
                    current_idx = delivery_indexes[component]
                    
                    # Ajouter des livraisons jusqu'à couvrir la quantité requise
                    while current_idx < total_deliveries and component_stock[component] < required_qty:
                        delivery = comp_deliveries.iloc[current_idx]
                        component_stock[component] += delivery['Qty_Purchasing']
                        delivery_date = delivery['Delivery date']
                        current_idx += 1
                        
                        if component_stock[component] >= required_qty:
                            is_available = True
                            # Mettre à jour l'index pour la prochaine utilisation
                            delivery_indexes[component] = current_idx
                            break
                
                # Si le composant n'est pas disponible, le produit ne peut pas être disponible
                if not is_available:
                    all_components_available = False
                
                # Mettre à jour le statut du composant pour ce produit
                component_status[component] = {
                    'available': is_available,
                    'date': delivery_date
                }
                
                # Mettre à jour la date de livraison la plus tardive
                if is_available and delivery_date:
                    if latest_delivery_date is None or delivery_date > latest_delivery_date:
                        latest_delivery_date = delivery_date
            
            # Mettre à jour le statut du produit
            if all_components_available:
                result_df.loc[product_idx, 'Updated_Stock_Status'] = 'Potentiellement dispo'
                result_df.loc[product_idx, 'Last_Delivery_Date'] = latest_delivery_date
                
                # Déduire les quantités des stocks de composants
                for component in needed_components:
                    component_stock[component] -= required_qty
            else:
                result_df.loc[product_idx, 'Updated_Stock_Status'] = 'No dispo'
                result_df.loc[product_idx, 'Last_Delivery_Date'] = None

        # 2.2 Gérer les produits No Block (non SECUROC et non M80)
        no_kit_mask = (no_block_no_dispo_mask & 
                    (result_df['MRP Controller'] != 'M80') & 
                    (result_df['Type'] != 'SECUROC'))

        grouped_products = result_df[no_kit_mask].groupby('Y Material')
        # Utiliser filtered_export_df au lieu de export_df pour les livraisons
        grouped_deliveries = filtered_export_df.groupby('Y Material')

        for material, product_group in grouped_products:
            # Vérifier si le matériel a des livraisons
            if material not in grouped_deliveries.groups:
                # Pas de livraisons disponibles, tous les produits restent non disponibles
                for idx, prod_row in product_group.iterrows():
                    result_df.at[idx, 'Updated_Stock_Status'] = 'No dispo'
                    result_df.at[idx, 'Last_Delivery_Date'] = prod_row['Created on']
                    result_df.at[idx, 'Updated_Remaining_Quantity'] = prod_row['Remaining_Quantity']
                continue
            
            # Trier les produits par ordre de priorité et les livraisons par date
            product_group = product_group.sort_values(by=['Sort_Order'])
            delivery_group = grouped_deliveries.get_group(material).sort_values(by=['Delivery date'])
            
            # Calculer la somme totale des quantités de livraison disponibles
            total_delivery_qty = delivery_group['Qty_Purchasing'].sum()
            remaining_delivery_qty = total_delivery_qty  # Quantité de livraison restante
            
            # Initialiser les variables pour suivre les livraisons à travers les produits
            deliv_idx = 0
            qty_accumulated = 0
            last_delivery_date = None  # Stocke la date de la dernière livraison utilisée
            delivery_array = delivery_group.to_dict('records')
            
            # Parcourir chaque produit pour ce matériel
            for idx, prod_row in product_group.iterrows():
                current_remaining = prod_row['Remaining_Quantity']  # Déjà négatif par défaut
                needed_qty = abs(current_remaining)  # Quantité nécessaire (positive)
                
                # Vérifier si la quantité accumulée des livraisons précédentes peut déjà couvrir ce produit
                if qty_accumulated >= needed_qty:
                    # Ce produit peut être potentiellement disponible avec la quantité déjà accumulée
                    delivery_date = last_delivery_date
                    
                    # Mettre à jour les informations du produit
                    new_remaining = remaining_delivery_qty - needed_qty
                    result_df.at[idx, 'Updated_Stock_Status'] = 'Potentiellement dispo'
                    result_df.at[idx, 'Last_Delivery_Date'] = delivery_date
                    result_df.at[idx, 'Updated_Remaining_Quantity'] = new_remaining
                    
                    # Mettre à jour la quantité de livraison restante pour les produits suivants
                    remaining_delivery_qty = new_remaining
                    
                    # Soustraire la quantité nécessaire pour ce produit de la quantité accumulée
                    qty_accumulated -= needed_qty
                
                # Vérifier si la quantité restante de livraison peut couvrir ce produit
                elif remaining_delivery_qty >= needed_qty:
                    # Ce produit peut être potentiellement disponible
                    delivery_date = None
                    
                    # Continuer à parcourir les livraisons à partir du point où nous nous sommes arrêtés
                    while deliv_idx < len(delivery_array):
                        # Si la quantité accumulée est déjà suffisante pour ce produit
                        if qty_accumulated >= needed_qty:
                            delivery_date = delivery_array[deliv_idx - 1]['Delivery date']
                            break
                        
                        # Sinon, accumuler la quantité de la livraison actuelle
                        deliv_row = delivery_array[deliv_idx]
                        qty_accumulated += deliv_row['Qty_Purchasing']
                        last_delivery_date = deliv_row['Delivery date']  # Mettre à jour la dernière date de livraison
                        
                        # Si cette livraison nous fait dépasser le seuil
                        if qty_accumulated >= needed_qty:
                            delivery_date = deliv_row['Delivery date']
                            deliv_idx += 1
                            break
                        
                        deliv_idx += 1
                    
                    # Si nous avons parcouru toutes les livraisons sans trouver de date
                    if delivery_date is None and deliv_idx > 0:
                        delivery_date = delivery_array[deliv_idx - 1]['Delivery date']
                    
                    # Mettre à jour les informations du produit
                    new_remaining = remaining_delivery_qty - needed_qty
                    result_df.at[idx, 'Updated_Stock_Status'] = 'Potentiellement dispo'
                    result_df.at[idx, 'Last_Delivery_Date'] = delivery_date
                    result_df.at[idx, 'Updated_Remaining_Quantity'] = new_remaining
                    
                    # Mettre à jour la quantité de livraison restante pour les produits suivants
                    remaining_delivery_qty = new_remaining
                    
                    # Soustraire la quantité nécessaire pour ce produit de la quantité accumulée
                    qty_accumulated -= needed_qty
                else:
                    # Pas assez de quantité pour ce produit
                    new_remaining = remaining_delivery_qty - needed_qty  # Sera négatif
                    result_df.at[idx, 'Updated_Stock_Status'] = 'No dispo'
                    result_df.at[idx, 'Last_Delivery_Date'] = prod_row['Created on']
                    result_df.at[idx, 'Updated_Remaining_Quantity'] = new_remaining
            
            # Nous gardons la quantité accumulée pour les prochains produits même si celui-ci est "No dispo"
        # 2.3 Gérer les kits No Block et MRP Controller == M80
        m80_mask = no_block_no_dispo_mask & (result_df['MRP Controller'] == 'M80')
        for idx, row in result_df[m80_mask].iterrows():
            kit_number = row['Y Material']
            kit_components = kits_df[kits_df['Y Material'] == kit_number]
            all_available = True

            for _, kit_row in kit_components.iterrows():
                component_rows = result_df[(result_df['Y Material'] == kit_row['Component']) &
                                           (result_df['Sales Document'] == row['Sales Document'])]

                if component_rows.empty or component_rows['Updated_Stock_Status'].values[0] != 'Potentiellement dispo':
                    all_available = False
                    break

            result_df.at[idx, 'Updated_Stock_Status'] = 'Potentiellement dispo' if all_available else 'No dispo'

        return result_df

    except Exception as e:
        print(f"Erreur détaillée: {str(e)}")  # Pour le debugging
        return f"🔴 Unexpected Error: {type(e).__name__}: {e}"
