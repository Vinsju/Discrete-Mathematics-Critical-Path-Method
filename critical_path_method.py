import pandas as pd
import numpy as np

def loadAndPrepare(filepath):
    df = pd.read_csv(filepath)
    df['prasyarat'] = df['prasyarat'].fillna('')
    df['durasi_jam'] = df['durasi_jam'].astype(float)
    df['deadline_jam'] = df['deadline_hari'].astype(float)*24
    df['release_time_jam'] = df['release_time_hari'].astype(float)*24

    df['ES'] = 0.0
    df['EF'] = 0.0
    df['LS'] = 0.0
    df['LF'] = 0.0

    return df

def topologicalSort(df):
    adjList = {}
    for _, row in df.iterrows():
        preds = [p.strip() for p in str(row['prasyarat']).split(';') if p.strip()]
        adjList[row['id']] = preds

    visited = set()
    stack = []

    def dfs(node):
        visited.add(node)

        successors = df[df['prasyarat'].str.contains(r'(^|;)' + node + r'(;|$)', regex=True, na=False)]['id'].tolist()
        for successor in successors:
            if successor not in visited:
                dfs(successor)
        stack.insert(0, node)

    dfs('START')
    return stack

def forwardPass(df, order):
    taskDict = df.set_index('id').to_dict('index')
    for node in order:
        if node == 'START':
            taskDict[node]['ES'] = 0.0
            taskDict[node]['EF'] = 0.0
        else:
            preds = [p.strip() for p in str(taskDict[node]['prasyarat']).split(';') if p.strip()]
            maxPredEF = max([taskDict[p]['EF'] for p in preds]) if preds else 0.0
            
            # Rumus modifikasi
            taskDict[node]['ES'] = max(maxPredEF, taskDict[node]['release_time_jam'])
            taskDict[node]['EF'] = taskDict[node]['ES'] + taskDict[node]['durasi_jam']

    return pd.DataFrame.from_dict(taskDict,orient='index').reset_index().rename(columns={'index':'id'})
            
def backwardPass(df, order):
    taskDict = df.set_index('id').to_dict('index')
    reverseOrder = list(reversed(order))

    for node in reverseOrder:
        if node == 'FINISH':
            taskDict[node]['LF'] = taskDict[node]['EF']
            taskDict[node]['LS'] = taskDict[node]['LF'] - taskDict[node]['durasi_jam']
        else:
            successors = df[df['prasyarat'].str.contains(r'(^|;)' + node + r'(;|$)', regex=True, na=False)]['id'].tolist()
            if successors:
                minSuccLS = min([taskDict[s]['LS'] for s in successors])
            else:
                minSuccLS = taskDict['FINISH']['LS']
            # Rumus modifikasi
            taskDict[node]['LF'] = min(minSuccLS,taskDict[node]['deadline_jam'])
            taskDict[node]['LS'] = taskDict[node]['LF'] - taskDict[node]['durasi_jam']

    return pd.DataFrame.from_dict(taskDict, orient='index').reset_index().rename(columns={'index':'id'})

def calculateSlackAndStatus(df):
    df['slack'] = df['LS'] - df['ES']
    
    def calculateSlack(row):
        if row['slack'] < 0:
            status = 'Jadwal Mustahil (Minus)'
        elif row['slack'] == 0:
            status = 'Kritis'
        else:
            status = 'Santai'
        return status
    df['status'] = df.apply(calculateSlack, axis = 1)
    return df

import networkx as nx
import matplotlib.pyplot as plt

def visualisasikan_graf(df):
    # 1. Inisialisasi Graf Berarah (DiGraph)
    G = nx.DiGraph()
    
    color_map = []
    labels = {}
    
    # 2. Iterasi untuk membuat Simpul (Nodes) beserta Bobot & Labelnya
    for _, row in df.iterrows():
        node_id = row['id']
        G.add_node(node_id)
        
        # BOBOT DI DALAM SIMPUL: Gabungkan ID Tugas dan Durasi Jam (h = hours)
        if node_id in ['START', 'FINISH']:
            labels[node_id] = f"{node_id}\n(0h)"
        else:
            labels[node_id] = f"{node_id}\n({int(row['durasi_jam'])}h)" 
        
        if node_id in ['START', 'FINISH']:
            color_map.append('#FFD700')      
        elif row['status'] == 'Kritis':
            color_map.append('#FF6347')       
        elif row['status'] == 'Jadwal Mustahil (Minus)':
            color_map.append('#DC143C')       
        else:
            color_map.append('#87CEEB')      
            
    # 3. Iterasi untuk membuat Sisi/Garis Berarah (Edges)
    for _, row in df.iterrows():
        node_id = row['id']
        preds = [p.strip() for p in str(row['prasyarat']).split(';') if p.strip()]
        for pred in preds:
            # Menggambar arah dari Prasyarat -> Tugas Selanjutnya
            G.add_edge(pred, node_id)
            
    # 4. Pengaturan Layout Tampilan Graf
    plt.figure(figsize=(16, 9))
    
    # Menggunakan kamus posisi (layout) agar graf menyebar secara proporsional
    pos = nx.spring_layout(G, seed=42, k=0.6) 
    
    # 5. Proses Menggambar Elemen Graf Berarah
    nx.draw_networkx_nodes(G, pos, node_color=color_map, node_size=1500, edgecolors='black', linewidths=1.2)
    
    # Menggambar PANAH BERARAH (Dipertegas dengan arrowstyle dan arrowsize)
    nx.draw_networkx_edges(
        G, pos, 
        arrowstyle='-|>',         
        arrowsize=18,          
        edge_color='#666666',      
        width=1.5,                
        node_size=1500             
    )
    
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8, font_weight='bold', font_family='sans-serif')
    
    # 6. Finalisasi Tampilan
    plt.title("Jaringan Kerja CPM Berarah & Berbobot (AON - Activity on Node)", fontsize=14, fontweight='bold', pad=20)
    plt.axis('off')  
    plt.show()
    
if __name__ == "__main__":
    filename = 'data matkul.csv'

    dfInit = loadAndPrepare(filename)
    urutanGraf = topologicalSort(dfInit)
    dfForward = forwardPass(dfInit, urutanGraf)
    dfBackward = backwardPass(dfForward,urutanGraf)
    dfFinal = calculateSlackAndStatus(dfBackward)
    

    kolom_tampil = ['id', 'mata_kuliah', 'nama_tugas', 'durasi_jam', 'ES', 'EF', 'LS', 'LF', 'slack', 'status']
    print("\n" + "="*40 + " HASIL KALKULASI CPM AKADEMIK " + "="*40)
    print(dfFinal[kolom_tampil].to_string(index=False))
    print("="*110)
    
    # Cetak rangkuman tugas kritis
    tugas_kritis = dfFinal[dfFinal['status'] == 'Kritis']['id'].tolist()
    tugas_minus = dfFinal[dfFinal['status'] == 'Jadwal Mustahil (Minus)']['id'].tolist()
    print(f"\n Tugas di Jalur Kritis (Toleransi 0 Jam): {', '.join(tugas_kritis)}")
    print(f"Tugas Berstatus Mustahil/Overdue: {', '.join(tugas_minus) if tugas_minus else 'Tidak ada'}")
    visualisasikan_graf(dfFinal)



