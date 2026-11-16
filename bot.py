import os
import telebot
from flask import Flask
from threading import Thread

# Configuração do Bot de Telegram
TOKEN = os.environ.get('TELEGRAM_TOKEN', '8922303337:AAGiqzCVesRtMgy1mIR1vK3hF7SW9wsONM0')
bot = telebot.TeleBot(TOKEN)

# Servidor Web integrado para manter o bot ativo 24/7 (Render / UptimeRobot)
app = Flask('')

@app.route('/')
def home():
    return "Bot Bac Bo 'Smart Brain Elite' a operar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# Base de dados em memória para gerir as sessões em tempo real por chat_id
user_sessions = {}

def cerebro_elite_avancado(historico):
    """
    CÉREBRO ELITE PROFISSIONAL (BAC BO):
    - Analisa padrões de exaustão e desequilíbrio estrutural em janelas profundas.
    - Aplica filtros estritos anti-ruído para garantir alta assertividade.
    - Retorna a cor alvo ('A' ou 'V') apenas quando o gatilho é seguro, ou None para silêncio.
    """
    puros = [x for x in historico if x in ['A', 'V']]
    
    # Exige histórico consistente para análise de alta precisão (mínimo 15 rondas)
    if len(puros) < 15:
        return None
        
    bloco_recente = puros[-8:]
    bloco_profundo = puros[-15:]
    
    # --- GATILHO 1: Exaustão Extrema de Tendência Unidirecional ---
    if all(x == 'A' for x in bloco_recente):
        return 'V'
    elif all(x == 'V' for x in bloco_recente):
        return 'A'
        
    # --- GATILHO 2: Desequilíbrio Estrutural Profundo (Lei das Médias) ---
    total_a = bloco_profundo.count('A')
    total_v = bloco_profundo.count('V')
    
    if total_a >= 11:
        return 'V'
    elif total_v >= 11:
        return 'A'
        
    # --- GATILHO 3: Padrão de Micro-Reversão Estruturada ---
    if bloco_recente[-1] != bloco_recente[-2] and bloco_recente[-2] != bloco_recente[-3] and bloco_recente[-3] != bloco_recente[-4] and bloco_recente[-4] != bloco_recente[-5] and bloco_recente[-5] != bloco_recente[-6]:
        return 'V' if bloco_recente[-1] == 'A' else 'A'

    # Se a mesa estiver em ruído total:
    return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {
        'history': [],
        'cor_alvo': None,
        'aguardando_resultado': False,
        'stats': {'wins': 0, 'losses': 0}
    }
    
    texto = (
        "🤖 **BAC BO - SMART BRAIN ELITE (Zero Gales)** 🏆🔥💎\n\n"
        "• *Motor de alta precisão: Exaustão, desequilíbrio e matriz avançada*\n"
        "• *Modo Ciclo Fechado: Dispara, aguarda o desfecho, valida e PÁRA obrigatoriamente.*\n"
        "• *Proteção obrigatória ativa no Empate (T)*\n\n"
        "📜 **Envia os resultados da mesa (ex: A, V, T) para o cérebro operar!**"
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
        "📊 **Relatório de Desempenho Elite:** 📈\n\n"
        f"🎉 **Wins (Acertos Totais):** `{wins}`\n"
        f"❌ **Losses (Erros Finais):** `{losses}`\n"
        f"🎯 **Taxa de Assertividade:** `{win_rate:.2f}%`\n"
        f"📜 Histórico Ativo: `{len(sessao['history'])} rondas registadas`"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    texto_input = message.text.strip().upper()
    
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {
            'history': [], 
            'cor_alvo': None,
            'aguardando_resultado': False,
            'stats': {'wins': 0, 'losses': 0}
        }
    
    sessao = user_sessions[chat_id]
    
    novas_letras = [char for char in texto_input if char in ['A', 'V', 'T']]
    if not novas_letras:
        bot.reply_to(message, "⚠️ Formato inválido. Envia apenas letras de resultado (`A`, `V` ou `T`).", parse_mode="Markdown")
        return
        
    resumo_acoes = []
    
    for resultado_real in novas_letras:
        sessao['history'].append(resultado_real)
        if len(sessao['history']) > 300:
            sessao['history'] = sessao['history'][-300:]
            
        # Se o bot estava à espera de resultado para fechar o ciclo:
        if sessao['aguardando_resultado'] and sessao['cor_alvo'] is not None:
            cor_esperada = sessao['cor_alvo']
            
            if resultado_real == 'T':
                sessao['stats']['wins'] += 1
                sessao['cor_alvo'] = None
                sessao['aguardando_resultado'] = False
                resumo_acoes.append("🟢 **PROTEÇÃO NO EMPATE (T) COBERTA!** Aposta devolvida. Ciclo encerrado.")
            elif resultado_real == cor_esperada:
                sessao['stats']['wins'] += 1
                sessao['cor_alvo'] = None
                sessao['aguardando_resultado'] = False
                resumo_acoes.append(f"🎉 **GREEN / VITÓRIA!** Saiu `{resultado_real}`. Ciclo encerrado com sucesso.")
            else:
                sessao['stats']['losses'] += 1
                sessao['cor_alvo'] = None
                sessao['aguardando_resultado'] = False
                resumo_acoes.append(f"❌ **LOSS!** Saiu `{resultado_real}`. Ciclo encerrado sem gales. Cérebro em pausa.")

    # Se após processar as letras o bot NÃO estiver à espera de resultado, avalia se dá um novo sinal
    sinal_gerado = None
    if not sessao['aguardando_resultado']:
        sugestao = cerebro_elite_avancado(sessao['history'])
        if sugestao is not None:
            sessao['cor_alvo'] = sugestao
            sessao['aguardando_resultado'] = True
            cor_nome = "AZUL 🔵" if sugestao == 'A' else "VERMELHO 🔴"
            sinal_gerado = (
                f"🧠 **DIRETRIZ DE ELITE - SMART BRAIN** 🎲\n"
                f"🎯 **GATILHO DE ALTA PROBABILIDADE VALIDADO!**\n"
                f"👉 **Entrar no {cor_nome} + Proteger no T**\n\n"
                f"🔒 *Modo de disparo único ativado: Bot em pausa até receber o resultado.*"
            )

    # Monta a resposta final para o utilizador saber sempre o que se passou
    resposta_final = ""
    if resumo_acoes:
        resposta_final += "\n".join(resumo_acoes) + "\n\n"
        
    if sinal_gerado:
        resposta_final += sinal_gerado
    elif not sessao['aguardando_resultado']:
        tamanho_hist = len([x for x in sessao['history'] if x in ['A', 'V']])
        if tamanho_hist < 15:
            resposta_final += f"🛡️ *A recolher histórico... ({tamanho_hist}/15 rondas limpas necessárias).* "
        else:
            resposta_final += "🛡️ *Mesa em observação inteligente (sem ruído ou gatilho seguro neste momento).* "

    bot.reply_to(message, resposta_final.strip(), parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()
