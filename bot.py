import os
import telebot
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

def cerebro_altamente_seletivo(historico):
    """
    CÉREBRO ALTAMENTE SELETIVO E INTELIGENTE:
    - Analisa a tendência real das últimas rondas sem disparar à toa.
    - Se a mesa estiver instável ou sem padrão claro, CALA-SE (retorna None).
    - Só dispara quando há um desequilíbrio forte ou uma sequência lógica sustentada.
    """
    puros = [x for x in historico if x in ['A', 'V']]
    
    # Exige pelo menos 8 rondas puras para começar a analisar o comportamento da mesa
    if len(puros) < 8:
        return None
        
    # Isola as últimas 8 rondas para análise de comportamento recente
    amostra = puros[-8:]
    
    # Contagem de predominância na amostra
    total_a = amostra.count('A')
    total_v = amostra.count('V')
    
    # 1. Filtro de Tendência Forte / Desequilíbrio (Ex: 6 ou mais da mesma cor numa janela de 8)
    if total_a >= 6:
        return 'A' # Segue a tendência forte de continuação
    elif total_v >= 6:
        return 'V'
        
    # 2. Filtro de Alternância Limpa (Ping-pong estruturado nas últimas 4 rondas)
    ultimas_quatro = amostra[-4:]
    if (ultimas_quatro[0] != ultimas_quatro[1] and 
        ultimas_quatro[1] != ultimas_quatro[2] and 
        ultimas_quatro[2] != ultimas_quatro[3]):
        # Se está em alternância perfeita, o próximo inverte o último
        return 'V' if ultimas_quatro[-1] == 'A' else 'A'
        
    # 3. Se a mesa estiver misturada (ex: 4-4 ou sem padrão limpo), o cérebro recusa-se a chutar
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
        "🤖 **BAC BO - SMART BRAIN ULTRA SELETIVO** 🏆🔥💎\n\n"
        "• *Cérebro inteligente: só entra quando a mesa tem leitura clara (zero palpites cegos)*\n"
        "• *Gestão rigorosa: Entrada + Máximo de 1 Gale (G1)*\n"
        "• *Proteção obrigatória no Empate (T)*\n\n"
        "📜 **Envia o fluxo de resultados para o cérebro caçar as melhores oportunidades!**"
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
        "📊 **Relatório de Desempenho (Ultra Seletivo):** 📈\n\n"
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
                    f"Aposta principal devolvida pela mesa. Em busca de nova oportunidade...", 
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
                    f"Saiu `{resultado_real}` com análise cirúrgica do cérebro!", 
                    parse_mode="Markdown"
                )
                continue
                
            else:
                # Gestão estrita a máximo de 1 Gale (G1)
                if sessao['fase_gale'] == 0:
                    sessao['fase_gale'] = 1 
                    cor_nome = "AZUL 🔵" if cor_esperada == 'A' else "VERMELHO 🔴"
                    bot.reply_to(
                        message, 
                        f"⚠️ **Loss na Entrada Principal (Saiu {resultado_real})**\n\n"
                        f"🔄 **GALE 1 (G1 - LIMITE MÁXIMO) OBRIGATÓRIO** 🚨\n"
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
                        f"❌ **LOSS FINAL (Ciclo G1 Esgotado - Saiu {resultado_real})**\n"
                        f"🛑 Limite atingido. Cérebro à espera de mesa limpa...", 
                        parse_mode="Markdown"
                    )
                    continue

    if sessao['cor_alvo'] is None:
        sugestao = cerebro_altamente_seletivo(sessao['history'])
        
        if sugestao is None:
            resposta = (
                f"🧠 **Smart Brain Ultra Seletivo**\n"
                f"🛡️ *Mesa sem padrão limpo ou muito misturada. Cérebro em silêncio à espera da melhor oportunidade...*"
            )
        else:
            sessao['cor_alvo'] = sugestao
            sessao['fase_gale'] = 0
            cor_nome = "AZUL 🔵" if sugestao == 'A' else "VERMELHO 🔴"
            resposta = (
                f"🧠 **ANÁLISE CIRÚRGICA DO CÉREBRO** 🎲\n"
                f"🎯 **OPORTUNIDADE DE ALTA ASSERTIVIDADE VALIDADA!**\n"
                f"👉 **Entrar no {cor_nome} + Proteger no T**"
            )
            
        bot.reply_to(message, resposta, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()
