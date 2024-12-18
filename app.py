from flask import Flask, render_template, jsonify, request
from flask_caching import Cache
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.utils
import json
from datetime import datetime
import requests
from io import StringIO
import os
from dotenv import load_dotenv
from datetime import timedelta

# Configuração do Flask e Cache
app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Configurações
CACHE_TIMEOUT = 3600  # 1 hora
LIGAS = {
    'Premier League (Inglaterra)': 'https://www.football-data.co.uk/mmz4281/2425/E0.csv',
    'Championship (Inglaterra)': 'https://www.football-data.co.uk/mmz4281/2425/E1.csv',
    'League One (Inglaterra)': 'https://www.football-data.co.uk/mmz4281/2425/E2.csv',
    'League Two (Inglaterra)': 'https://www.football-data.co.uk/mmz4281/2425/E3.csv',
    'La Liga (Espanha)': 'https://www.football-data.co.uk/mmz4281/2425/SP1.csv',
    'La Liga 2 (Espanha)': 'https://www.football-data.co.uk/mmz4281/2425/SP2.csv',
    'Serie A (Itália)': 'https://www.football-data.co.uk/mmz4281/2425/I1.csv',
    'Bundesliga (Alemanha)': 'https://www.football-data.co.uk/mmz4281/2425/D1.csv',
    'Scottish Premiership (Escócia)': 'https://www.football-data.co.uk/mmz4281/2425/SC0.csv',
    'Ligue 1 (França)': 'https://www.football-data.co.uk/mmz4281/2425/F1.csv',
    'Eredivisie (Holanda)': 'https://www.football-data.co.uk/mmz4281/2425/N1.csv',
    'Pro League (Bélgica)': 'https://www.football-data.co.uk/mmz4281/2425/B1.csv',
    'Primeira Liga (Portugal)': 'https://www.football-data.co.uk/mmz4281/2425/P1.csv',
    'Süper Lig (Turquia)': 'https://www.football-data.co.uk/mmz4281/2425/T1.csv',
    'Super League (Grécia)': 'https://www.football-data.co.uk/mmz4281/2425/G1.csv'
}

class EstatisticasCalculator:
    def __init__(self, df):
        self.df = df
        
    def calcular_over_under(self, gols, tipo='FT'):
        if tipo == 'HT':
            total_gols = self.df['HTHG'] + self.df['HTAG']
        else:
            total_gols = self.df['FTHG'] + self.df['FTAG']
        return len(self.df[total_gols > gols]) / len(self.df) * 100
    
    def calcular_btts(self):
        if 'FTR' in self.df.columns:
            ambos_marcam = ((self.df['FTHG'] > 0) & (self.df['FTAG'] > 0))
            return len(self.df[ambos_marcam]) / len(self.df) * 100
        return 0
    
    def calcular_media_gols(self):
        if 'FTR' in self.df.columns:
            total_gols = self.df['FTHG'] + self.df['FTAG']
            return total_gols.mean()
        return 0
    
@cache.memoize(timeout=300)
def baixar_dados(liga):
    url = LIGAS[liga]
    try:
        df = pd.read_csv(url)
        df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
        return df
    except Exception as e:
        print(f"Erro ao baixar dados: {e}")
        return None

def obter_times(liga):
    df = baixar_dados(liga)
    if df is None or df.empty:
        return []
    
    # Remover valores NaN e converter para string
    home_teams = set(df['HomeTeam'].dropna().astype(str))
    away_teams = set(df['AwayTeam'].dropna().astype(str))
    
    # Remover qualquer string 'nan' que possa ter sido criada
    times = sorted(list(home_teams | away_teams))
    times = [time for time in times if time.lower() != 'nan']
    
    return times

def filtrar_dados_time(df, time, local=None):
    """
    Filtra os dados do DataFrame para um time específico.
    
    Args:
        df: DataFrame com os dados
        time: Nome do time
        local: 'casa' para jogos em casa, 'fora' para jogos fora, None para todos os jogos
    """
    if local == 'casa':
        return df[df['HomeTeam'] == time]
    elif local == 'fora':
        return df[df['AwayTeam'] == time]
    else:
        return df[(df['HomeTeam'] == time) | (df['AwayTeam'] == time)]

def calcular_estatisticas(df, time, local=None):
    df_time = filtrar_dados_time(df, time, local)
    
    if len(df_time) == 0:
        return None
    
    # Inicializar calculadora
    calc = EstatisticasCalculator(df_time)
    
    # Estatísticas básicas
    jogos = len(df_time)
    vitorias = len(df_time[df_time['FTR'] == ('H' if local == 'casa' else 'A')])
    empates = len(df_time[df_time['FTR'] == 'D'])
    derrotas = jogos - vitorias - empates
    
    # Cálculo de gols
    if local == 'casa':
        gols_marcados = df_time['FTHG'].sum()
        gols_sofridos = df_time['FTAG'].sum()
        media_corners = (df_time['HC'] + df_time['AC']).mean()  # Total de escanteios por jogo
        corners_over_85 = len(df_time[df_time['HC'] + df_time['AC'] > 8]) / jogos * 100
        corners_over_95 = len(df_time[df_time['HC'] + df_time['AC'] > 9]) / jogos * 100
        corners_over_105 = len(df_time[df_time['HC'] + df_time['AC'] > 10]) / jogos * 100
        corners_over_115 = len(df_time[df_time['HC'] + df_time['AC'] > 11]) / jogos * 100
        corners_over_125 = len(df_time[df_time['HC'] + df_time['AC'] > 12]) / jogos * 100
        media_corners_favor = df_time['HC'].mean()
        media_corners_contra = df_time['AC'].mean()
    else:
        gols_marcados = df_time['FTAG'].sum()
        gols_sofridos = df_time['FTHG'].sum()
        media_corners = (df_time['HC'] + df_time['AC']).mean()  # Total de escanteios por jogo
        corners_over_85 = len(df_time[df_time['HC'] + df_time['AC'] > 8]) / jogos * 100
        corners_over_95 = len(df_time[df_time['HC'] + df_time['AC'] > 9]) / jogos * 100
        corners_over_105 = len(df_time[df_time['HC'] + df_time['AC'] > 10]) / jogos * 100
        corners_over_115 = len(df_time[df_time['HC'] + df_time['AC'] > 11]) / jogos * 100
        corners_over_125 = len(df_time[df_time['HC'] + df_time['AC'] > 12]) / jogos * 100
        media_corners_favor = df_time['AC'].mean()
        media_corners_contra = df_time['HC'].mean()
    
    # Calcular aproveitamento
    aproveitamento = (vitorias * 3 + empates) / (jogos * 3) * 100
    
    # Estatísticas de Over/Under
    stats = {
        'jogos': jogos,
        'vitorias': vitorias,
        'empates': empates,
        'derrotas': derrotas,
        'gols_marcados': int(gols_marcados),
        'gols_sofridos': int(gols_sofridos),
        'gols_por_jogo': round((gols_marcados + gols_sofridos) / jogos, 2),  # Média total de gols por jogo
        'gols_sofridos_por_jogo': round(gols_sofridos / jogos, 2),
        'aproveitamento': round(aproveitamento, 1),
        'ht_over_05': calc.calcular_over_under(0.5, 'HT'),
        'ht_over_15': calc.calcular_over_under(1.5, 'HT'),
        'ft_over_05': calc.calcular_over_under(0.5),
        'ft_over_15': calc.calcular_over_under(1.5),
        'ft_over_25': calc.calcular_over_under(2.5),
        'ft_over_35': calc.calcular_over_under(3.5),
        'btts': calc.calcular_btts(),
        'media_gols': calc.calcular_media_gols(),
        # Novas estatísticas de escanteios
        'media_corners': round(media_corners, 1),
        'media_corners_favor': round(media_corners_favor, 1),
        'media_corners_contra': round(media_corners_contra, 1),
        'corners_over_85': round(corners_over_85, 1),
        'corners_over_95': round(corners_over_95, 1),
        'corners_over_105': round(corners_over_105, 1),
        'corners_over_115': round(corners_over_115, 1),
        'corners_over_125': round(corners_over_125, 1)
    }
    
    return stats

def gerar_grafico_comparacao(stats1, stats2, time1, time2):
    categorias = ['Over 0.5 HT', 'Over 1.5 HT', 'Over 0.5 FT', 'Over 1.5 FT', 'Over 2.5 FT', 'Over 3.5 FT', 'BTTS']
    valores1 = [stats1[k] for k in ['ht_over_05', 'ht_over_15', 'ft_over_05', 'ft_over_15', 'ft_over_25', 'ft_over_35', 'btts']]
    valores2 = [stats2[k] for k in ['ht_over_05', 'ht_over_15', 'ft_over_05', 'ft_over_15', 'ft_over_25', 'ft_over_35', 'btts']]
    
    fig = go.Figure(data=[
        go.Bar(name=time1, x=categorias, y=valores1),
        go.Bar(name=time2, x=categorias, y=valores2)
    ])
    
    fig.update_layout(
        title=f'Comparação: {time1} vs {time2}',
        barmode='group',
        yaxis_title='Porcentagem (%)',
        template='plotly_dark'
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def gerar_dicas_apostas(time1_stats, time2_stats):
    dicas = []
    
    # Média de gols combinada
    media_gols = (time1_stats['media_gols'] + time2_stats['media_gols']) / 2
    
    # Análise BTTS (Ambas as equipes marcam)
    if time1_stats['btts'] >= 65 and time2_stats['btts'] >= 65:
        dicas.append({
            'tipo': 'Ambas Marcam: Sim',
            'confianca': 'Alta',
            'razao': f'Ambos os times têm alto % de BTTS: {time1_stats["btts"]:.1f}% e {time2_stats["btts"]:.1f}%'
        })
    
    # Análise de gols
    if (time1_stats['ft_over_15'] >= 75 and time2_stats['ft_over_15'] >= 75):
        dica_over = {
            'tipo': 'Over 1.5 Gols',
            'confianca': 'Alta',
            'razao': f'Média de {media_gols:.1f} gols por jogo. Over 1.5: {time1_stats["ft_over_15"]:.1f}% e {time2_stats["ft_over_15"]:.1f}%'
        }
        
        # Se over 2.5 também tem boa confiança, adiciona essa informação à razão
        if time1_stats['ft_over_25'] >= 60 and time2_stats['ft_over_25'] >= 60:
            dica_over['razao'] += f'. Over 2.5: {time1_stats["ft_over_25"]:.1f}% e {time2_stats["ft_over_25"]:.1f}%'
        
        dicas.append(dica_over)
    
    # Análise de gols no primeiro tempo
    if time1_stats['ht_over_05'] >= 70 and time2_stats['ht_over_05'] >= 70:
        dicas.append({
            'tipo': 'Over 0.5 Gols HT',
            'confianca': 'Alta',
            'razao': f'Alto % de gols no 1º tempo: {time1_stats["ht_over_05"]:.1f}% e {time2_stats["ht_over_05"]:.1f}%'
        })
    
    return dicas

def obter_tabela_classificacao(liga):
    df = baixar_dados(liga)
    
    # Criar dicionário para armazenar estatísticas dos times
    times = {}
    
    for _, jogo in df.iterrows():
        # Time da casa
        if jogo['HomeTeam'] not in times:
            times[jogo['HomeTeam']] = {'P': 0, 'J': 0, 'V': 0, 'E': 0, 'D': 0, 'GP': 0, 'GC': 0, 'SG': 0}
        # Time visitante
        if jogo['AwayTeam'] not in times:
            times[jogo['AwayTeam']] = {'P': 0, 'J': 0, 'V': 0, 'E': 0, 'D': 0, 'GP': 0, 'GC': 0, 'SG': 0}
        
        # Atualizar estatísticas
        home_goals = int(jogo['FTHG'])
        away_goals = int(jogo['FTAG'])
        
        # Time da casa
        times[jogo['HomeTeam']]['J'] += 1
        times[jogo['HomeTeam']]['GP'] += home_goals
        times[jogo['HomeTeam']]['GC'] += away_goals
        
        # Time visitante
        times[jogo['AwayTeam']]['J'] += 1
        times[jogo['AwayTeam']]['GP'] += away_goals
        times[jogo['AwayTeam']]['GC'] += home_goals
        
        if home_goals > away_goals:  # Vitória casa
            times[jogo['HomeTeam']]['V'] += 1
            times[jogo['HomeTeam']]['P'] += 3
            times[jogo['AwayTeam']]['D'] += 1
        elif home_goals < away_goals:  # Vitória visitante
            times[jogo['AwayTeam']]['V'] += 1
            times[jogo['AwayTeam']]['P'] += 3
            times[jogo['HomeTeam']]['D'] += 1
        else:  # Empate
            times[jogo['HomeTeam']]['E'] += 1
            times[jogo['HomeTeam']]['P'] += 1
            times[jogo['AwayTeam']]['E'] += 1
            times[jogo['AwayTeam']]['P'] += 1
    
    # Calcular saldo de gols
    for time in times:
        times[time]['SG'] = times[time]['GP'] - times[time]['GC']
    
    # Converter para DataFrame e ordenar
    tabela = pd.DataFrame.from_dict(times, orient='index')
    tabela = tabela.sort_values(['P', 'V', 'SG', 'GP'], ascending=[False, False, False, False])
    tabela = tabela.reset_index()
    tabela = tabela.rename(columns={'index': 'Time'})
    
    # Adicionar posição
    tabela.insert(0, 'Pos', range(1, len(tabela) + 1))
    
    return tabela.to_dict('records')

load_dotenv()

# IDs das ligas na API-Football
LEAGUE_IDS = {
    'Premier League': 39,
    'Championship': 40,
    'League One': 41,
    'League Two': 42,
    'La Liga': 140,
    'La Liga 2': 141,
    'Bundesliga': 78,
    'Bundesliga 2': 79,
    'Serie A': 135,
    'Serie B': 136,
    'Ligue 1': 61,
    'Ligue 2': 62,
    'Primeira Liga': 94,
    'Eredivisie': 88
}

def obter_proximos_jogos(liga, time=None):
    """
    Obtém os próximos jogos de uma liga ou de um time específico.
    Retorna os próximos 5 jogos.
    """
    api_key = os.getenv('FOOTBALL_API_KEY')
    if not api_key:
        return []

    headers = {
        'x-rapidapi-host': 'api-football-v1.p.rapidapi.com',
        'x-rapidapi-key': api_key
    }

    # Data atual e data limite (próximos 30 dias)
    data_atual = datetime.now().strftime('%Y-%m-%d')
    data_limite = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    # ID da liga
    league_id = LEAGUE_IDS.get(liga)
    if not league_id:
        return []

    # Montando a URL da API
    url = f'https://api-football-v1.p.rapidapi.com/v3/fixtures'
    params = {
        'league': league_id,
        'season': datetime.now().year,
        'from': data_atual,
        'to': data_limite
    }

    if time:
        params['team'] = time  # Precisaria mapear o nome do time para o ID da API

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            jogos = []
            
            for jogo in data['response'][:5]:  # Pegando apenas os próximos 5 jogos
                fixture = jogo['fixture']
                teams = jogo['teams']
                
                jogos.append({
                    'data': datetime.fromtimestamp(fixture['timestamp']).strftime('%d/%m/%Y'),
                    'hora': datetime.fromtimestamp(fixture['timestamp']).strftime('%H:%M'),
                    'casa': teams['home']['name'],
                    'fora': teams['away']['name'],
                    'estadio': fixture['venue']['name'] if fixture['venue'] else 'Não disponível'
                })
            
            return jogos
    except Exception as e:
        print(f"Erro ao buscar próximos jogos: {e}")
        return []

    return []

@app.route('/')
def index():
    times_premier = obter_times('Premier League (Inglaterra)')
    times_championship = obter_times('Championship (Inglaterra)')
    times_league_one = obter_times('League One (Inglaterra)')
    times_league_two = obter_times('League Two (Inglaterra)')
    times_laliga = obter_times('La Liga (Espanha)')
    times_laliga2 = obter_times('La Liga 2 (Espanha)')
    times_seriea = obter_times('Serie A (Itália)')
    times_bundesliga = obter_times('Bundesliga (Alemanha)')
    times_scotland = obter_times('Scottish Premiership (Escócia)')
    times_ligue1 = obter_times('Ligue 1 (França)')
    times_eredivisie = obter_times('Eredivisie (Holanda)')
    times_proleague = obter_times('Pro League (Bélgica)')
    times_portugal = obter_times('Primeira Liga (Portugal)')
    times_turkey = obter_times('Süper Lig (Turquia)')
    times_greece = obter_times('Super League (Grécia)')
    return render_template('index.html', 
                         times_premier=times_premier,
                         times_championship=times_championship,
                         times_league_one=times_league_one,
                         times_league_two=times_league_two,
                         times_laliga=times_laliga,
                         times_laliga2=times_laliga2,
                         times_seriea=times_seriea,
                         times_bundesliga=times_bundesliga,
                         times_scotland=times_scotland,
                         times_ligue1=times_ligue1,
                         times_eredivisie=times_eredivisie,
                         times_proleague=times_proleague,
                         times_portugal=times_portugal,
                         times_turkey=times_turkey,
                         times_greece=times_greece,
                         ligas=LIGAS)

@app.route('/estatisticas_time/<liga>/<time>')
def estatisticas_time(liga, time):
    df = baixar_dados(liga)
    if df is None:
        return jsonify({'error': 'Erro ao obter dados'})

    stats_geral = calcular_estatisticas(df, time)
    stats_casa = calcular_estatisticas(df, time, 'casa')
    stats_fora = calcular_estatisticas(df, time, 'fora')

    return jsonify({
        'geral': stats_geral,
        'casa': stats_casa,
        'fora': stats_fora
    })

@app.route('/comparar/<liga>/<time1>/<time2>')
def comparar_times(liga, time1, time2):
    try:
        df = baixar_dados(liga)
        if df is None:
            return jsonify({'error': 'Erro ao obter dados da liga'})
        
        # Calcular estatísticas dos times (time1 como mandante, time2 como visitante)
        time1_stats = calcular_estatisticas(df, time1, 'casa')
        time2_stats = calcular_estatisticas(df, time2, 'fora')
        
        # Gerar gráfico de comparação
        grafico = gerar_grafico_comparacao(time1_stats, time2_stats, f"{time1} (Casa)", f"{time2} (Fora)")
        
        # Gerar dicas de apostas
        dicas = gerar_dicas_apostas(time1_stats, time2_stats)
        
        # Obter tabela de classificação
        tabela = obter_tabela_classificacao(liga)
        
        return jsonify({
            'time1': time1_stats,
            'time2': time2_stats,
            'grafico': grafico,
            'dicas': dicas,
            'tabela': tabela,
            'times_comparados': [time1, time2]
        })
    except Exception as e:
        print(f"Erro na comparação: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/ultimos_jogos/<liga>/<time>')
def ultimos_jogos(liga, time):
    df = baixar_dados(liga)
    if df is None:
        return jsonify([])
    
    # Convertendo a coluna Date para datetime se ainda não estiver
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Filtrando jogos do time e ordenando por data (mais recente primeiro)
    jogos = df[(df['HomeTeam'] == time) | (df['AwayTeam'] == time)].sort_values('Date', ascending=False).head(5)
    
    resultados = []
    for _, jogo in jogos.iterrows():
        data = jogo['Date'].strftime('%d/%m/%Y')
        if jogo['HomeTeam'] == time:
            resultado = {
                'data': data,
                'casa': True,
                'adversario': jogo['AwayTeam'],
                'gols_favor': jogo['FTHG'],
                'gols_contra': jogo['FTAG']
            }
        else:
            resultado = {
                'data': data,
                'casa': False,
                'adversario': jogo['HomeTeam'],
                'gols_favor': jogo['FTAG'],
                'gols_contra': jogo['FTHG']
            }
        resultados.append(resultado)
    
    return jsonify(resultados)

@app.route('/proximos_jogos/<liga>/<time>')
def proximos_jogos(liga, time):
    jogos = obter_proximos_jogos(liga, time)
    return jsonify(jogos)

@app.route('/classificacao/<liga>')
def classificacao(liga):
    try:
        tabela = obter_tabela_classificacao(liga)
        return jsonify(tabela)
    except Exception as e:
        print(f"Erro ao obter classificação: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
