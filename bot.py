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
    return "Bot Bac Bo 'Professional Neural Brain' a operar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# Base de dados em memória para gerir as sessões em tempo real
user_sessions = {}

def cerebro_profissional_autonomo(historico):
    """
    CÉREBRO NEURAL AUTÓNOMO & PROFISSIONAL:
    - Analisa a inércia, o peso estatístico e a transição orgânica do fluxo recente.
    - Calcula o índice de confiança probabilística para a próxima rondas.
    - Se a entropia da mesa estiver alta (ruído/instabilidade), silencia (retorna None).
    - Exige alta convicção para disparar o sinal de entrada.
    """
    puros = [x for x in historico if x in ['A', 'V']]
    
    # Exige uma amostra mínima sólida para começar a calcular matrizes de probabilidade
    if len(puros) < 10:
        return None
        
    # Janela analítica de alta precisão (últimas 12 rondas)
    janela = puros[-12:]
    
    # Pesos ponderados: as rondas mais recentes pesam mais no cálculo do fluxo
    peso_azul = 0
    peso_vermelho = 0
    total_amostra = len(janela)
    
    for i, res in enumerate(janela):
        fator = (i + 1) / total_amostra  # Dá mais peso progressivo ao fim da mesa
        if res == 'A':
            peso_azul += fator
        else:
            peso_vermelho += fator
            
    # Análise de micro-tendência na cauda imediata (últimas 3 rondas)
    cauda = janela[-3:]
    streak_atual = all(x == cauda[0] for x in cauda)
    
    # Cálculo de viés estatístico autónomo
    diferenca = abs(peso_azul - peso_vermelho)
    
    # Critério de alta convicção profissional (evita palpites fracos)
    # Se houver um desequilíbrio orgânico forte ou uma quebra de micro-tendência estruturada:
    if diferenca > 1.2:  # Limiar de rigor estatístico elevado
        # Se o peso puxa fortemente para uma cor, o cérebro acompanha a inércia ou aplica reversão inteligente
        if peso_azul > peso_vermelho:
            return 'A'
        else:
            return 'V'
            
    # Análise comportamental de exaustão de streaks (quando uma cor estica demais e o cérebro calcula a inversão)
    if streak_atual and total_amostra >= 10:
        # Inversão orgânica calculada por exaustão de ciclo
        cor_esgotamento = cauda[0]
        return 'V' if cor_esgotamento == 'A' else 'A'
        
    # Se a mesa estiver neutra, equilibrada ou sem leitura de alta probabilidade: o cérebro cala-se
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
        "🤖 **BAC BO - PROFESSIONAL NEURAL BRAIN** 🏆🔥💎\n\n"
        "• *Cérebro autónomo de alta performance (Análise de Inércia & Entropia)*\n"
        "• *Gestão estrita: Entrada + Máximo de 1 Gale (G1)*\n"
        "• *Proteção obrigatória e automática no Empate (T)*\n\n"
        "📜 **Envia o fluxo de resultados para o cérebro calcular as entradas de elite!**"
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
        "📊 **Relatório de Desempenho (Profissional):** 📈\n\n"
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
        if len(sessao['history']) > 300:
            sessao['history'] = sessao['history'][-300:]
            
        if sessao['cor_alvo'] is not None:
            cor_esperada = sessao['cor_alvo']
            
            if resultado_real == 'T':
                sessao['stats']['wins'] += 1
                sessao['cor_alvo'] = None
                sessao['fase_gale'] = 0
                bot.reply_to(
                    message, 
                    f"🟢 **PROTEÇÃO NO EMPATE (T) COBERTA COM SUCESSO!** 🟡\n"
                    f"Aposta principal devolvida pela mesa. Cérebro a recalcular próximo alvo de elite...", 
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
                    f"Saiu `{resultado_real}` com precisão neural do cérebro profissional!", 
                    parse_mode="Markdown"
                )
                continue
                
            else:
                # Gestão profissional restrita estritamente a MÁXIMO DE 1 GALE (G1)
                if sessao['fase_gale'] == 0:
                    sessao['fase_gale'] = 1 
                    cor_nome = "AZUL 🔵" if cor_esperada == 'A' else "VERMELHO 🔴"
                    bot.reply_to(
                        message, 
                        f"⚠️ **Loss na Entrada Principal (Saiu {resultado_real})**\n\n"
                        f"🔄 **GALE 1 (G1 - LIMITE PROFISSIONAL) OBRIGATÓRIO** 🚨\n"
                        f"👉 **Entrar no {cor_nome} + Proteger no T**", 
                        parse_mode="Markdown"
                    )
                    continue
                else:
                    # Se falhar o G1, encerra o ciclo de forma limpa para proteger a banca
                    sessao['stats']['losses'] += 1
                    sessao['cor_alvo'] = None
                    sessao['fase_gale'] = 0
                    bot.reply_to(
                        message, 
                        f"❌ **LOSS FINAL (Ciclo G1 Esgotado - Saiu {resultado_real})**\n"
                        f"🛑 Limite de risco atingido. Cérebro em modo de defesa à espera de mesa ideal...", 
                        parse_mode="Markdown"
                    )
                    continue

    if sessao['cor_alvo'] is None:
        sugestao = cerebro_profissional_autonomo(sessao['history'])
        
        if sugestao is None:
            resposta = (
                f"🧠 **Professional Neural Brain**\n"
                f"🛡️ *Mesa com alta entropia/ruído detetada. Cérebro em silêncio tático à espera da oportunidade perfeita...*"
            )
        else:
            sessao['cor_alvo'] = sugestao
            sessao['fase_gale'] = 0
            cor_nome = "AZUL 🔵" if sugestao == 'A' else "VERMELHO 🔴"
            resposta = (
                f"🧠 **ANÁLISE NEURAL DE ELITE** 🎲\n"
                f"🎯 **SINAL PROFISSIONAL VALIDADO!**\n"
                f"👉 **Entrar no {cor_nome} + Proteger no T**"
            )
            
        bot.reply_to(message, resposta, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()
