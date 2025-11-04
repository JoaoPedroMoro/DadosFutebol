from flask import Flask, render_template, request, redirect, url_for, flash
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from dotenv import load_dotenv
load_dotenv()

# Cria o app Flask
app = Flask(__name__)

API_TOKEN = os.getenv("API_TOKEN")
app.secret_key = os.getenv("FLASK_SECRET")

HEADERS = {"X-Auth-Token": API_TOKEN}  # cabeçalho obrigatório da API
BASE_URL = "https://api.football-data.org/v4"  # base da API

# Fuso horário local
LOCAL_ZONE = ZoneInfo("America/Sao_Paulo")

# Função para converter datas ISO da API para horário local legível
def iso_to_local_str(iso_str):
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))  # transforma string ISO em datetime
    dt_local = dt.astimezone(LOCAL_ZONE)  # converte para horário de São Paulo
    return dt_local.strftime("%d/%m/%Y %H:%M")  # formata para dd/mm/yyyy HH:MM

# Dicionário de ligas para popular o dropdown do filtro
ligas = {
    "WC": "FIFA World Cup",
    "CL": "UEFA Champions League",
    "BL1": "Bundesliga",
    "DED": "Eredivisie",
    "BSA": "Campeonato Brasileiro Série A",
    "PD": "Primera Division",
    "FL1": "Ligue 1",
    "ELC": "Championship",
    "PPL": "Primeira Liga",
    "EC": "European Championship",
    "SA": "Serie A",
    "PL": "Premier League"
}

# Rota principal: lista os jogos do dia
@app.route("/", methods=["GET"])
def index():
    # Pega os filtros enviados pelo usuário
    selected = request.args.get("league")  # liga selecionada
    data_selecionada = request.args.get("date") or datetime.now(LOCAL_ZONE).strftime("%Y-%m-%d")  # data selecionada ou hoje
    matches = []  # lista que vai receber todos os jogos

    # Define quais ligas buscar: se o usuário escolheu, só essa; senão, todas
    ligas_busca = [selected] if selected else ligas.keys()

    # Busca os jogos de cada liga
    for league_code in ligas_busca:
        url = f"{BASE_URL}/competitions/{league_code}/matches"
        params = {
            "dateFrom": data_selecionada,
            "dateTo": data_selecionada  # buscamos apenas um dia
        }

        resp = requests.get(url, headers=HEADERS, params=params)

        # Se der erro na API, mostra aviso se o usuário tinha escolhido uma liga
        if resp.status_code != 200:
            if selected:
                flash(f"Não foi possível buscar os jogos da competição {ligas[league_code]}.", "warning")
            continue  # pula para próxima liga

        data = resp.json()
        league_matches = data.get("matches", [])

        # Se não houver jogos na data selecionada, alerta o usuário
        if selected and len(league_matches) == 0:
            flash(f"A competição {ligas[selected]} não possui jogos na data selecionada.", "warning")

        # Processa cada partida: ajusta horário e adiciona nome da competição
        for m in league_matches:
            m["local_time"] = iso_to_local_str(m["utcDate"])
            m["competition_name"] = ligas[league_code]
            matches.append(m)

    # Ordena todas as partidas pelo horário
    matches = sorted(matches, key=lambda x: x["utcDate"])

    # Renderiza a página passando os dados para o template
    return render_template("index.html", ligas=ligas, selected=selected,
                           matches=matches, hoje=data_selecionada)

# Rota para exibir a classificação de uma competição
@app.route("/standings", methods=["GET"])
def standings():
    league_code = request.args.get("league")

    # Se não selecionou liga, volta para a página principal com aviso
    if not league_code:
        flash("Selecione uma competição antes de ver a classificação.", "warning")
        return redirect(url_for("index"))

    # Busca a classificação na API
    url = f"{BASE_URL}/competitions/{league_code}/standings"
    resp = requests.get(url, headers=HEADERS)

    if resp.status_code != 200:
        flash("Não foi possível buscar a classificação dessa competição.", "danger")
        return redirect(url_for("index"))

    data = resp.json()
    standings = []

    # A classificação vem em blocos; pegamos o bloco 'TOTAL'
    standings_blocks = data.get("standings", [])
    if standings_blocks:
        for block in standings_blocks:
            if block.get("type") == "TOTAL":
                standings = block.get("table", [])
                break

        # Se não encontrou tipo TOTAL, pega o primeiro disponível
        if not standings:
            standings = standings_blocks[0].get("table", [])

    # Renderiza o template da classificação
    return render_template("standings.html", standings=standings, league_code=league_code)

# Inicializa o servidor Flask
if __name__ == "__main__":
    app.run(debug=True)
