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
    return "Bot Bac Bo 'Smart Brain 10 Rondas' a operar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# Base de dados em memória para gerir as sessões em tempo real
user_sessions = {}

def cerebro_janela_dez(historico):
    """
    CÉREBRO INTELIGENTE (JANELA DE 10 RONDAS):
    - Analisa estritamente as últimas 10 rondas puras enviadas.
    - Avalia se há um padrão lógico de alternância ou desequilíbrio limpo.
    - Se a mesa estiver num antro de ruído/baits, fica em silêncio (retorna None).
    """
    puros = [x for x in historico if x in ['A', 'V']]
    
    # Exige o bloco completo de 10 rondas para começar a raciocinar com precisão
    if len(puros) < 10:
        return None
        
    # Isola estritamente as últimas 10 rondas
    dez_rondas = puros[-10:]
    
    # 1. Verificar se há Ping-Pong limpo e ativo no final das 10
    if dez_rondas[-1] != dez_rondas[-2] and dez_rondas[-2] != dez_rondas[-3] and dez_rondas[-3] != dez_rondas[-4]:
        # Segue a lógica do ping-pong legítimo
        return 'V' if dez_rondas[-1] == 'A' else 'A'
        
    # 2. Verificar desequilíbrio estatístico forte dentro destas 10 rondas
    total_a = dez_rondas.count('A')
    total_v = dez_rondas.count('V')
    
    # Se nas 10 rondas uma cor dominar fortemente (ex: 7 contra 3), o cérebro puxa a correção
    if total_a >= 7:
        return 'V'
    elif total_v >= 7:
        return 'A'
        
    # Se o cenário das 10 rondas estiver completamente misturado e sem lógica clara de tendência:
    return None

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
        "🤖 **BAC BO - SMART BRAIN (Janela 10 Rondas)** 🏆🔥💎\n\n"
        "• *Análise inteligente focada estritamente nas últimas 10 rondas*\n"
        "• *Gale controlado (até G2) + Proteção obrigatória no Empate (T)*\n\n"
        "📜 **Envia blocos de 10 resultados para o cérebro analisar e decidir a entrada!**"
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
        "📊 **Relatório de Desempenho (10 Rondas):** 📈\n\n"
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
                    f"Aposta principal devolvida pela mesa. A aguardar próximo bloco de 10...", 
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
                    f"Saiu `{resultado_real}` com leitura inteligente das 10 rondas!", 
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
                        f"🛑 Ciclo encerrado. Cérebro em pausa de proteção...", 
                        parse_mode="Markdown"
                    )
                    continue

    if sessao['cor_alvo'] is None:
        sugestao = cerebro_janela_dez(sessao['history'])
        
        if sugestao is None:
            resposta = (
                f"🧠 **Smart Brain (Janela de 10 Rondas)**\n"
                f"🛡️ *Mesa sem padrão limpo nas últimas 10. Em observação inteligente...*"
            )
        else:
            sessao['cor_alvo'] = sugestao
            sessao['fase_gale'] = 0
            cor_nome = "AZUL 🔵" if sugestao == 'A' else "VERMELHO 🔴"
            resposta = (
                f"🧠 **DIRETRIZ DAS 10 RONDAS** 🎲\n"
                f"🎯 **OPORTUNIDADE LÓGICA VALIDADA!**\n"
                f"👉 **Entrar no {cor_nome} + Proteger no T**"
            )
            
        bot.reply_to(message, resposta, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()
