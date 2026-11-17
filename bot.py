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

def cerebro_janela_dez_seguro(historico):
    """
    CÉREBRO INTELIGENTE E CAUTELOSO (JANELA DE 10 RONDAS):
    - Foco estricto em proteção de capital e Gale 1.
    - Só dispara quando há exaustão clara (respeitando inversões) ou desequilíbrio seguro.
    - Nunca segue ping-pongs cegos que possam quebrar a banca.
    """
    puros = [x for x in historico if x in ['A', 'V']]
    
    # Exige o bloco de 10 rondas para análise
    if len(puros) < 10:
        return None
        
    dez_rondas = puros[-10:]
    
    # 1. Gatilho de Exaustão Segura (Ex: 5 ou mais repetidos seguidos -> Inverter para a cor oposta)
    ultimos = puros[-5:]
    if all(x == ultimos[0] for x in ultimos):
        tendencia = ultimos[0]
        return 'V' if tendencia == 'A' else 'A'
        
    # 2. Desequilíbrio Defensivo nas últimas 10 rondas (Ex: 7 ou mais de uma cor -> Puxar a correção)
    total_a = dez_rondas.count('A')
    total_v = dez_rondas.count('V')
    
    if total_a >= 7:
        return 'V'
    elif total_v >= 7:
        return 'A'
        
    # Se a mesa estiver em ping-pong misto ou sem exaustão clara, fica calado para não perder dinheiro
    return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {
        'history': [],
        'fase_gale': 0,
        'cor_alvo': None,
        'stats': {
            'wins_cor': 0,
            'wins_empate': 0,
            'losses': 0
        }
    }
    
    texto = (
        "🤖 **BAC BO - SMART BRAIN CAUTELOSO (Foco 20/1)** 🏆🔥💎\n\n"
        "• *Análise inteligente focada em exaustões e correções seguras*\n"
        "• *Suporte estrito a GALE 1 (G1) + Proteção obrigatória no Empate (T)*\n\n"
        "📜 **Envia os resultados (`A`, `V` ou `T`) para o cérebro analisar e decidir com cautela!**"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=['stats'])
def send_stats(message):
    chat_id = message.chat.id
    if chat_id not in user_sessions:
        bot.reply_to(message, "⚠️ Nenhuma sessão ativa detetada. Usa o comando `/start`.", parse_mode="Markdown")
        return
        
    sessao = user_sessions[chat_id]
    wins_c = sessao['stats']['wins_cor']
    wins_e = sessao['stats']['wins_empate']
    losses = sessao['stats']['losses']
    total_wins = wins_c + wins_e
    total_ops = total_wins + losses
    win_rate = (total_wins / total_ops * 100) if total_ops > 0 else 0
    
    texto = (
        "📊 **Relatório de Desempenho (Seguro):** 📈\n\n"
        f"🟢 **Wins na Cor:** `{wins_c}`\n"
        f"🟡 **Wins de Empate (T):** `{wins_e}`\n"
        f"🔴 **Losses Finais (Após G1):** `{losses}`\n"
        f"🎯 **Total de Operações:** `{total_ops}`\n"
        f"📈 **Assertividade:** `{win_rate:.2f}%`\n"
        f"📜 Histórico Ativo: `{len(sessao['history'])} rondas`"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=['reset'])
def reset_session(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {
        'history': [],
        'fase_gale': 0,
        'cor_alvo': None,
        'stats': {'wins_cor': 0, 'wins_empate': 0, 'losses': 0}
    }
    bot.reply_to(message, "🔄 Sessão reiniciada do zero! Histórico limpo, Zé.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    texto_input = message.text.strip().upper()
    
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {
            'history': [], 
            'fase_gale': 0,
            'cor_alvo': None,
            'stats': {'wins_cor': 0, 'wins_empate': 0, 'losses': 0}
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
            
            # Se sair Empate (T), conta logo como vitória do empate
            if resultado_real == 'T':
                sessao['stats']['wins_empate'] += 1
                sessao['cor_alvo'] = None
                sessao['fase_gale'] = 0
                bot.reply_to(
                    message, 
                    f"🟡 **PROTEÇÃO NO EMPATE (T) COBERTA COM SUCESSO!** (+3€)\n"
                    f"Aposta principal devolvida. A aguardar próximo gatilho seguro...", 
                    parse_mode="Markdown"
                )
                continue
                
            elif resultado_real == cor_esperada:
                sessao['stats']['wins_cor'] += 1
                sessao['cor_alvo'] = None
                sessao['fase_gale'] = 0
                bot.reply_to(
                    message, 
                    f"🎉 **GREEN / VITÓRIA CONFIRMADA!** 🟢✨\n"
                    f"Saiu `{resultado_real}` com leitura segura!", 
                    parse_mode="Markdown"
                )
                continue
                
            else:
                # Sistema estrito de Gale 1 (Apenas G1 e fecho)
                if sessao['fase_gale'] == 0:
                    sessao['fase_gale'] = 1 
                    cor_nome = "AZUL 🔵" if cor_esperada == 'A' else "VERMELHO 🔴"
                    bot.reply_to(
                        message, 
                        f"⚠️ **Loss na Entrada Principal (Saiu {resultado_real})**\n\n"
                        f"🔄 **GALE 1 (G1 - ÚLTIMO NÍVEL) OBRIGATÓRIO** 🚨\n"
                        f"👉 **Entrar no {cor_nome} (6€) + Proteger no T (1€)**", 
                        parse_mode="Markdown"
                    )
                    continue
                else:
                    # Falhou o Gale 1 -> Loss Final
                    sessao['stats']['losses'] += 1
                    sessao['cor_alvo'] = None
                    sessao['fase_gale'] = 0
                    
                    aviso_loss = (
                        f"❌ **LOSS FINAL (Gale 1 Falhado - Saiu {resultado_real})**\n"
                        f"🛑 Ciclo encerrado. Cérebro em pausa de proteção..."
                    )
                    if sessao['stats']['losses'] >= 2:
                        aviso_loss += "\n\n🚨 **ATENÇÃO ZÉ! Atingiste o limite máximo de 2 losses! Cerra a mesa e respira!**"
                        
                    bot.reply_to(message, aviso_loss, parse_mode="Markdown")
                    continue

    if sessao['cor_alvo'] is None:
        sugestao = cerebro_janela_dez_seguro(sessao['history'])
        
        if sugestao is None:
            resposta = (
                f"🧠 **Smart Brain Cauteloso**\n"
                f"🛡️ *Mesa sem exaustão ou desequilíbrio seguro. Em observação inteligente...*"
            )
        else:
            sessao['cor_alvo'] = sugestao
            sessao['fase_gale'] = 0
            cor_nome = "AZUL 🔵" if sugestao == 'A' else "VERMELHO 🔴"
            resposta = (
                f"🧠 **DIRETRIZ SEGURA VALIDADA** 🎲\n"
                f"🎯 **OPORTUNIDADE DE EXAUSTÃO/CORREÇÃO!**\n"
                f"👉 **Entrar Principal: {cor_nome} (3€) + Proteger no T (1€)**"
            )
            
        bot.reply_to(message, resposta, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()
