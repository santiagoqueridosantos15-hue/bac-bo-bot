import telebot
import os
from flask import Flask
from threading import Thread

# Configuração do Bot de Telegram
TOKEN = '8922303337:AAGiqzCVesRtMgy1mIR1vK3hF7SW9wsONM0'
bot = telebot.TeleBot(TOKEN)

# Servidor Web integrado para manter o bot ativo 24/7 (Render / UptimeRobot)
app = Flask('')

@app.route('/')
def home():
    return "Bot Bac Bo 'Master Professional' a operar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# Base de dados em memória para gerir as sessões em tempo real
user_sessions = {}

def motor_profissional_autonomo(historico):
    """
    MOTOR PROFISSIONAL AUTÓNOMO:
    - Analisa o histórico enviado (lê a macro e a micro do sapato).
    - Tem lógica própria de raciocínio estatístico humano, sem ficar bloqueado em silêncios.
    - Retorna sempre uma decisão clara ('A' ou 'V').
    """
    puros = [x for x in historico if x in ['A', 'V']]
    
    # Se houver pouquíssimas jogadas, exige o mínimo de base
    if len(puros) < 6:
        return 'A' if len(puros) % 2 == 0 else 'V'
    
    # Avaliação macro (últimas 30 ou o total disponível) e micro (últimas 6)
    macro = puros[-30:]
    micro = puros[-6:]
    
    total_a_macro = macro.count('A')
    total_v_macro = macro.count('V')
    
    # Raciocínio de Trader Profissional:
    # 1. Se a micro recente estiver a desequilibrar fortemente para um lado, o profissional antecipa o ressalto/correção.
    # 2. Se o balanço macro estiver inclinado, o motor acompanha a lógica natural do sapato.
    last_val = micro[-1]
    
    if micro.count(last_val) >= 3:
        # Se fez um pequeno bloco de 3, o profissional aposta na quebra ou no seguimento inteligente
        # No Bac Bo, o raciocínio profissional equilibra o sapato:
        return 'V' if last_val == 'A' else 'A'
    
    # Balanço geral das últimas rondas
    if total_a_macro > total_v_macro:
        # Sapato com mais Azul globalmente -> O motor equilibra puxando Vermelho ou seguindo se houver força
        return 'V' if micro[-1] == 'A' else 'A'
    else:
        return 'A' if micro[-1] == 'V' else 'V'

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {
        'history': [],
        'fase_gale': 0,
        'cor_alvo': None,
        'stats': {'wins': 0, 'losses': 0}
    }
    
    texto = (
        "🤖 **BAC BO - MASTER PROFESSIONAL (Modo Autónomo)** 🏆🔥💎\n\n"
        "• *Cérebro profissional ativado: sem silêncios vazios, com raciocínio lógico*\n"
        "• *Gale controlado (até G2) + Proteção obrigatória no Empate (T) em todos os sinais*\n\n"
        "📜 **Envia o fluxo de resultados do sapato para o profissional analisar e dar a entrada!**"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=['stats'])
def send_stats(message):
    chat_id = message.chat.id
    if chat_id not in user_sessions:
        bot.reply_to(message, "⚠️ Nenhuma sessão ativa detetada. Usa o comando `/start`.", parse_mode="Markdown")
        return
        
    sessao = user_sessions[chat_id]
    wins = sessao['stats']['wins']
    losses = sessao['stats']['losses']
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    
    texto = (
        "📊 **Relatório de Desempenho (Professional):** 📈\n\n"
        f"🎉 **Wins (Acertos Totais):** `{wins}`\n"
        f"❌ **Losses (Erros Finais):** `{losses}`\n"
        f"🎯 **Taxa de Assertividade:** `{win_rate:.2f}%`\n"
        f"📜 Tamanho do Histórico Ativo: `{len(sessao['history'])} rondas`"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    texto_input = message.text.strip().upper()
    
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {
            'history': [], 
            'fase_gale': 0,
            'cor_alvo': None,
            'stats': {'wins': 0, 'losses': 0}
        }
    
    sessao = user_sessions[chat_id]
    
    novas_letras = [char for char in texto_input if char in ['A', 'V', 'T']]
    if not novas_letras:
        bot.reply_to(message, "⚠️ Formato inválido. Envia apenas letras de resultado (`A`, `V` ou `T`).", parse_mode="Markdown")
        return
        
    for resultado_real in novas_letras:
        sessao['history'].append(resultado_real)
        if len(sessao['history']) > 250:
            sessao['history'] = sessao['history'][-250:]
            
        if sessao['cor_alvo'] is not None:
            cor_esperada = sessao['cor_alvo']
            
            if resultado_real == 'T':
                sessao['stats']['wins'] += 1
                sessao['cor_alvo'] = None
                sessao['fase_gale'] = 0
                bot.reply_to(
                    message, 
                    f"🟢 **PROTEÇÃO NO EMPATE (T) COBERTA COM SUCESSO!** 🟡\n"
                    f"Aposta principal devolvida pela mesa. A calcular o próximo passo profissional...", 
                    parse_mode="Markdown"
                )
                continue
                
            elif resultado_real == cor_esperada:
                sessao['stats']['wins'] += 1
                sessao['cor_alvo'] = None
                sessao['fase_gale'] = 0
                bot.reply_to(
                    message, 
                    f"🎉 **GREEN / VITÓRIA CONFIRMADA!** 🟢✨\n"
                    f"Saiu `{resultado_real}` com leitura analítica perfeita!", 
                    parse_mode="Markdown"
                )
                continue
                
            else:
                if sessao['fase_gale'] == 0:
                    sessao['fase_gale'] = 1 
                    cor_nome = "AZUL 🔵" if cor_esperada == 'A' else "VERMELHO 🔴"
                    bot.reply_to(
                        message, 
                        f"⚠️ **Loss na Entrada Principal (Saiu {resultado_real})**\n\n"
                        f"🔄 **GALE 1 (G1) OBRIGATÓRIO** 🚨\n"
                        f"👉 **Entrar no {cor_nome} + Proteger no T**", 
                        parse_mode="Markdown"
                    )
                    continue
                elif sessao['fase_gale'] == 1:
                    sessao['fase_gale'] = 2 
                    cor_nome = "AZUL 🔵" if cor_esperada == 'A' else "VERMELHO 🔴"
                    bot.reply_to(
                        message, 
                        f"⚠️ **Loss no Gale 1 (Saiu {resultado_real})**\n\n"
                        f"🔄 **GALE 2 (G2 - ÚLTIMO NÍVEL) OBRIGATÓRIO** 🚨\n"
                        f"👉 **Entrar no {cor_nome} + Proteger no T**", 
                        parse_mode="Markdown"
                    )
                    continue
                else:
                    sessao['stats']['losses'] += 1
                    sessao['cor_alvo'] = None
                    sessao['fase_gale'] = 0
                    bot.reply_to(
                        message, 
                        f"❌ **LOSS FINAL (Ciclo G2 Esgotado - Saiu {resultado_real})**\n"
                        f"🛑 Ciclo encerrado com gestão rigorosa de risco.", 
                        parse_mode="Markdown"
                    )
                    continue

    # Se não houver alvo ativo, o motor profissional processa imediatamente o histórico e dá a entrada
    if sessao['cor_alvo'] is None:
        sugestao = motor_profissional_autonomo(sessao['history'])
        
        if sugestao is not None:
            sessao['cor_alvo'] = sugestao
            sessao['fase_gale'] = 0
            cor_nome = "AZUL 🔵" if sugestao == 'A' else "VERMELHO 🔴"
            resposta = (
                f"🎩 **ANÁLISE PROFISSIONAL MASTER** 🎲\n"
                f"🎯 **DIRETRIZ CALCULADA!**\n"
                f"👉 **Entrar no {cor_nome} + Proteger no T**"
            )
            bot.reply_to(message, resposta, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()
