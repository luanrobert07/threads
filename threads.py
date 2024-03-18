import threading
import random
import time
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Conexão com o MongoDB
client = MongoClient('localhost', 27017)
db = client.bancoiot
collection = db.sensores

# Diretório para armazenar os documentos
DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), "documents_Temp")

# Verifica se a pasta "documents_Temp" já existe, se não existir, cria
if not os.path.exists(DOCUMENTS_DIR):
    os.makedirs(DOCUMENTS_DIR)
    print(f"Pasta 'documents_Temp' criada em {DOCUMENTS_DIR}")
else:
    print(f"A pasta 'documents_Temp' já existe em {DOCUMENTS_DIR}")

# Função para criar arquivos para cada sensor
def criar_arquivos_sensores():
    sensores = ["Temp1", "Temp2", "Temp3"]
    for sensor in sensores:
        arquivo_path = os.path.join(DOCUMENTS_DIR, f"{sensor}.txt")
        if not os.path.exists(arquivo_path):
            with open(arquivo_path, "w") as arquivo:
                arquivo.write(f"Informações do sensor {sensor}:\n\n")
                arquivo.write("Data/Hora        | Temperatura (°C) | Alarme\n")
                arquivo.write("-----------------------------------------\n")
            print(f"Arquivo para o sensor {sensor} criado em {arquivo_path}")
        else:
            print(f"O arquivo para o sensor {sensor} já existe em {arquivo_path}")

# Função para gerar a temperatura aleatória
def gerar_temperatura():
    while True:
        temperatura = random.uniform(30, 40)
        yield temperatura
        time.sleep(random.randint(1, 5))  # Intervalo de 1 a 5 segundos

# Função para atualizar o banco de dados e verificar alarmes
def atualizar_bd_e_verificar_alarme(nome_sensor, temperatura_generator):
    for temperatura in temperatura_generator:
        data_atual = datetime.now()
        document = {
            "nomeSensor": nome_sensor,
            "valorSensor": temperatura,
            "unidadeMedida": "C°",
            "sensorAlarmado": temperatura > 38,
            "timestamp": data_atual
        }
        collection.update_one({"nomeSensor": nome_sensor}, {"$set": document}, upsert=True)
        if temperatura > 38:
            print(f"Atenção! Temperatura muito alta! Verificar Sensor {nome_sensor}!")
            break
        else:
            print(f"Sensor {nome_sensor}: {temperatura:.2f}°C")

        # Salvar valores no arquivo do sensor
        arquivo_path = os.path.join(DOCUMENTS_DIR, f"{nome_sensor}.txt")
        with open(arquivo_path, "a") as arquivo:
            arquivo.write(f"{data_atual.strftime('%Y-%m-%d %H:%M:%S')} | {temperatura:.2f}°C | {temperatura > 38}\n")

# Função principal para criar threads para os sensores e para plotar o gráfico
def main():
    # Verificar se o MongoDB está disponível
    try:
        client.server_info()
    except Exception as e:
        print("Erro ao conectar ao MongoDB:", e)
        return

    # Criar documentos para cada sensor, se ainda não existirem
    sensores = ["Temp1", "Temp2", "Temp3"]
    for sensor in sensores:
        if not collection.find_one({"nomeSensor": sensor}):
            document = {
                "nomeSensor": sensor,
                "valorSensor": 0,
                "unidadeMedida": "C°",
                "sensorAlarmado": False,
                "timestamp": datetime.now()
            }
            collection.insert_one(document)

    # Criar três threads para os sensores
    threads = []
    for i in range(1, 4):
        nome_sensor = f"Temp{i}"
        temperatura_generator = gerar_temperatura()
        t = threading.Thread(target=atualizar_bd_e_verificar_alarme, args=(nome_sensor, temperatura_generator))
        threads.append(t)
        t.start()
    
    criar_arquivos_sensores()

    # Aguardar o término de todas as threads dos sensores
    for t in threads:
        t.join()

    # Plotar o gráfico dos últimos valores dos sensores na última hora
    plotar_grafico()

# Função para plotar o gráfico dos últimos valores dos sensores na última hora
def plotar_grafico():
    fig, axs = plt.subplots(3, 1, figsize=(10, 12), sharex=True)

    def animate(i):
        hora_anterior = datetime.now() - timedelta(hours=1)
        
        for idx, sensor in enumerate(["Temp1", "Temp2", "Temp3"]):
            data = []
            valores = []
            for sensor_data in collection.find({"nomeSensor": sensor, "timestamp": {"$gt": hora_anterior}}):
                data.append(sensor_data["timestamp"])
                valores.append(sensor_data["valorSensor"])

            axs[idx].clear()
            axs[idx].plot(data, valores)
            axs[idx].set_xlabel('Hora')
            axs[idx].set_ylabel('Temperatura (C°)')
            axs[idx].set_title(f'Valores do Sensor {sensor} na Última Hora')
            axs[idx].xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: datetime.fromtimestamp(x/1000).strftime('%H:%M:%S')))
            axs[idx].tick_params(rotation=45)

    ani = animation.FuncAnimation(fig, animate, interval=5000)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
