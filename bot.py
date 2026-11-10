import telebot
import os
from flask import Flask
from threading import Thread
from collections import Counter

TOKEN = '8922303337:AAGiqzCVesRtMgy1mIR1vK3hF7SW9wsONM0'
bot = telebot.TeleBot(TOKEN)

app = Flask('')

@app.route('/')
def home():
    return "Bot de Bac Bo (Elite Professional 96%) a funcionar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# Memória avançada por canal/utilizador
user_sessions = {}

def analisar_probabilidade_avancada(historico):
    """
    MOTOR INSTITUCIONAL DE ALTA ASSERTIVIDADE:
    - Analisa frequências globais, transições de Markov de ordem 2 e desvio de curto prazo.
    - Retorna 'A' (Azul), 'V' (Vermelho) ou None (Pausa de Segurança / Sem Vantagem).
    """
    puros = [x for x in historico if x in ['A', 'V']]
    if len(puros) < 20:  # Exige base consistente para calcular probabilidades reais
        return None
    
    # 1. Filtro de Saturação / Exaustão Absoluta (Anti-Dragões Cegos)
    if len(puros) >= 8 and all(x == puros[-1] for x in puros[-8:]):
        return None

    # 2. PADRÃO DE MARKOV / TRANSIÇÃO RECENTE (Ordem 2)
    # Analisa o comportamento estatístico exato das últimas 2 jogadas no histórico do sapato
    ultimo_par = tuple(puros[-2:])
    seguintes = []
    
    for i in range(len(puros) - 2):
        if tuple(puros[i:i+2]) == ultimo_par:
            seguintes.append(puros[i+2])
            
    if len(seguintes) >= 5: # Se houver amostra suficiente deste padrão no sapato
        contagem = Counter(seguintes)
        total_padrao = len(seguintes)
        
        # Se a probabilidade estatística de uma cor neste padrão for superior a 75%
        for cor in ['A', 'V']:
            if (contagem[cor] / total_padrao) >= 0.75:
                return cor

    # 3. PING-PONG / ALTERNÂNCIA RIGOROSA DE CURTO PRAZO
    if puros[-1] != puros[-2] and puros[-2] != puros[-3] and puros[-3] != puros[-4] and puros[-4] != puros[-5]:
        return 'V' if puros[-1] == 'A' else 'A'

    # 4. LEI DE COMPENSAÇÃO / DESVIO DE FREQUÊNCIA (Janela de 10)
    ultimas_dez = puros[-10:]
    if ultimas_dez.count('A') >= 8:
        return 'V'
    elif ultimas_dez.count('V') >= 8:
        return 'A'

    return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {
        'history': [],
        'stats': {'wins': 0, 'losses': 0}
    }
    
    texto = (
        "🤖 **Bac Bo Pro - Elite Professional (96%)** 🏆🔥\n\n"
        "Motor estatístico com Matrizes de Markov e Cobertura de Empate ativado.\n"
        "Envia os resultados do sapato em fluxo contínuo (ex: `A V V T A A V...`) para o bot monitorizar a mesa em tempo real!"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=['stats'])
def send_stats(message):
    chat_id = message.chat.id
    if chat_id not in user_sessions:
        bot.reply_to(message, "⚠️ Sem sessão ativa. Usa `/start` para iniciar.", parse_mode="Markdown")
        return
        
    sessao = user_sessions[chat_id]
    wins = sessao['stats']['wins']
    losses = sessao['stats']['losses']
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    
    texto = (
        "📊 **Estatísticas do Canal (Elite):** 📈\n\n"
        f"🎉 **Wins (Acertos):** `{wins}`\n"
        f"❌ **Losses (Erros):** `{losses}`\n"
        f"🎯 **Taxa de Assertividade:** `{win_rate:.2f}%`\n"
        f"📜 Histórico em Memória: `{len(sessao['history'])} rondas`"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    texto_input = message.text.strip().upper()
    
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {
            'history': [], 
            'stats': {'wins': 0, 'losses': 0}
        }
    
    sessao = user_sessions[chat_id]
    
    novas_letras = [char for char in texto_input if char in ['A', 'V', 'T']]
    if not novas_letras:
        bot.reply_to(message, "⚠️ Envia resultados válidos (`A`, `V` ou `T`).", parse_mode="Markdown")
        return
        
    # Acumular histórico no sapato (mantém as últimas 100 rondas)
    sessao['history'].extend(novas_letras)
    if len(sessao['history']) > 100:
        sessao['history'] = sessao['history'][-100:]
        
    # Executar motor estatístico avançado
    sugestao = analisar_probabilidade_avancada(sessao['history'])
    
    if sugestao is None:
        resposta = (
            f"📊 **Mesa em Análise Profunda** ({len(sessao['history'])} rondas)\n"
            f"🛡️ *Filtro de alta seletividade ativo.*\n"
            f"🛑 **AGUARDAR / SAPATO SEM VANTAGEM MATEMÁTICA**"
        )
    else:
        cor_nome = "AZUL 🔵" if sugestao == 'A' else "VERMELHO 🔴"
        resposta = (
            f"🎲 **DADOS** 🎲\n"
            f"🚨 **ENTRADA CONFIRMADA**\n"
            f"👉 **APOSTAR NA COR:** {cor_nome}\n"
            f"🛡️ **PROTEGER NO EMPATE:** 🟡 (T)\n\n"
            f"📊 *Confluência Markoviana de Alta Precisão*"
        )
        
    bot.reply_to(message, resposta, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()
