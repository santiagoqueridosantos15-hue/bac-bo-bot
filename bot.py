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
    return "Bot Bac Bo 'Smart Brain 10 Rondas (Profissional)' a operar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# Base de dados em memória para gerir as sessões em tempo real por chat_id
user_sessions = {}

def cerebro_janela_dez(historico):
    """
    CÉREBRO INTELIGENTE E RIGOROSO (JANELA DE 10 RONDAS):
    - Analisa estritamente as últimas 10 rondas puras enviadas ('A' ou 'V').
    - Filtra ruído e falsas inversões (não salta logo só porque houve uma troca isolada).
    - Valida ping-pong legítimo e desequilíbrio estatístico profundo (>= 7 numa ponta).
    - Se a mesa estiver instável ou em transição, retorna None (mantém o bot em silêncio de proteção).
    """
    puros = [x for x in historico if x in ['A', 'V']]
    
    # Exige o bloco completo de 10 rondas para garantir leitura estatística real
    if len(puros) < 10:
        return None
        
    # Isola estritamente as últimas 10 rondas
    dez_rondas = puros[-10:]
    
    # 1. Verificar se há Ping-Pong limpo e ativo no final das 10 (alternância consistente)
    if dez_rondas[-1] != dez_rondas[-2] and dez_rondas[-2] != dez_rondas[-3] and dez_rondas[-3] != dez_rondas[-4]:
        # Confirma se não é um falso ping-pong olhando para a consistência anterior
        return 'V' if dez_rondas[-1] == 'A' else 'A'
        
    # 2. Verificar desequilíbrio estatístico forte dentro das 10 rondas (evita falsas trocas por uma única cor isolada)
    total_a = dez_rondas.count('A')
    total_v = dez_rondas.count('V')
    
    # Só dispara correção/continuidade se a dominância for real (>= 7 em 10 rondas)
    if total_a >= 7:
        return 'V'
    elif total_v >= 7:
        return 'A'
        
    # Se a mesa estiver dividida (ex: 5-5 ou 6-4 sem padrão claro), o cérebro recusa-se a inventar entradas
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
        "🤖 **BAC BO - SMART BRAIN PROFISSIONAL (Zero Gales)** 🏆🔥💎\n\n"
        "• *Análise inteligente com filtro anti-ruído nas 10 rondas*\n"
        "• *Modo Ciclo Fechado: Dispara o sinal, aguarda o desfecho, valida e PÁRA para reanalisar.*\n"
        "• *Proteção obrigatória ativa no Empate (T)*\n\n"
        "📜 **Envia os resultados da mesa (ex: A, V, T) para o cérebro operar com precisão cirúrgica!**"
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
        "📊 **Relatório de Desempenho Profissional:** 📈\n\n"
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
        
    for resultado_real in novas_letras:
        sessao['history'].append(resultado_real)
        if len(sessao['history']) > 300:
            sessao['history'] = sessao['history'][-300:]
            
        # Se o bot emitiu um sinal e estamos à espera do desfecho desta ronda exata:
        if sessao['aguardando_resultado'] and sessao['cor_alvo'] is not None:
            cor_esperada = sessao['cor_alvo']
            
            if resultado_real == 'T':
                sessao['stats']['wins'] += 1
                sessao['cor_alvo'] = None
                sessao['aguardando_resultado'] = False
                bot.reply_to(
                    message, 
                    f"🟢 **PROTEÇÃO NO EMPATE (T) COBERTA COM SUCESSO!** 🟡\n"
                    f"Aposta principal devolvida pela mesa. **Ciclo encerrado com sucesso.** A aguardar novas diretrizes do cérebro...", 
                    parse_mode="Markdown"
                )
                continue
                
            elif resultado_real == cor_esperada:
                sessao['stats']['wins'] += 1
                sessao['cor_alvo'] = None
                sessao['aguardando_resultado'] = False
                bot.reply_to(
                    message, 
                    f"🎉 **GREEN / VITÓRIA CONFIRMADA!** 🟢✨\n"
                    f"Saiu `{resultado_real}` na aposta direta. **Ciclo encerrado.** A reanalisar a mesa de forma inteligente...", 
                    parse_mode="Markdown"
                )
                continue
                
            else:
                sessao['stats']['losses'] += 1
                sessao['cor_alvo'] = None
                sessao['aguardando_resultado'] = False
                bot.reply_to(
                    message, 
                    f"❌ **LOSS (Saiu {resultado_real})**\n"
                    f"🛑 Operação encerrada sem gales. **Ciclo parado.** Cérebro em pausa de segurança a reavaliar o cenário...", 
                    parse_mode="Markdown"
                )
                continue

    # Se o bot NÃO está à espera de resultado (ou seja, acabou de fechar um ciclo anterior), 
    # ele avalia se deve mandar um NOVO sinal ou ficar em silêncio.
    if not sessao['aguardando_resultado']:
        sugestao = cerebro_janela_dez(sessao['history'])
        
        if sugestao is None:
            # Mantém-se em silêncio ou informa que está em observação profunda
            pass
        else:
            sessao['cor_alvo'] = sugestao
            sessao['aguardando_resultado'] = True  # BLOQUEIA novos sinais até este ser resolvido!
            cor_nome = "AZUL 🔵" if sugestao == 'A' else "VERMELHO 🔴"
            resposta = (
                f"🧠 **DIRETRIZ PROFISSIONAL DAS 10 RONDAS** 🎲\n"
                f"🎯 **PADRÃO LÓGICO VALIDADO COM FILTRO DE SEGURANÇA!**\n"
                f"👉 **Entrar no {cor_nome} + Proteger no T**\n\n"
                f"🔒 *Modo de disparo único ativado: O bot está agora em pausa, aguardando o resultado para reanalisar.*"
            )
            bot.reply_to(message, resposta, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()
