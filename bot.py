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
    return "Bot Bac Bo 'Camaleon Adaptive Brain' a operar 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# Base de dados em memória para gerir as sessões em tempo real
user_sessions = {}

def cerebro_camaleao_adaptativo(historico):
    """
    CÉREBRO CAMALEÃO ADAPTATIVO (MÁXIMA INTELIGÊNCIA):
    - Lê o comportamento estrutural da mesa em tempo real.
    - Identifies se a mesa está em tendência pesada, alternância limpa ou caos.
    - Se a mesa mudar de forma, o cérebro adapta a estratégia de raciocínio instantaneamente.
    - Se o cenário for de ruído total, silencia (retorna None).
    """
    puros = [x for x in historico if x in ['A', 'V']]
    
    # Exige uma amostra mínima de 10 rondas para começar a detetar a forma da mesa
    if len(puros) < 10:
        return None
        
    # Janela de análise dinâmica recente (últimas 12 rondas)
    janela = puros[-12:]
    
    total_a = janela.count('A')
    total_v = janela.count('V')
    
    # 1. ANÁLISE DE TENDÊNCIA / VANTAGEM FORTE (Mesa desequilibrada)
    # Se uma cor estiver a dominar claramente a mesa (>70% da amostra recente)
    if total_a >= 8:
        return 'A'  # Continuidade da força dominante azul
    elif total_v >= 8:
        return 'V'  # Continuidade da força dominante vermelha
        
    # 2. ANÁLISE DE ALTERNÂNCIA LIMPA (Ping-pong estruturado na cauda)
    # Se as últimas 4 rondas estiverem em alternância perfeita (ex: A V A V)
    ultimas_4 = janela[-4:]
    if (ultimas_4[0] != ultimas_4[1] and 
        ultimas_4[1] != ultimas_4[2] and 
        ultimas_4[2] != ultimas_4[3]):
        # Adapta-se à alternância: inverte o último resultado
        return 'V' if ultimas_4[-1] == 'A' else 'A'
        
    # 3. ANÁLISE DE EXAUSTÃO / REVERSÃO DE CICLO (Mesa esticada)
    # Se a cauda imediata tiver uma sequência repetida de 3 iguais (ex: V V V), a mesa costuma quebrar
    cauda_3 = janela[-3:]
    if cauda_3[0] == cauda_3[1] == cauda_3[2]:
        # O cérebro deteta que a mesa esticou e aplica a inversão inteligente
        return 'V' if cauda_3[2] == 'A' else 'A'
        
    # 4. SILÊNCIO TÁTICO (Mesa baralhada / Caos / Sem padrão claro)
    # Se a mesa estiver empatada em termos de força (ex: 6-6) e sem alternância limpa, o robô cala-se para não arriscar
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
        "🤖 **BAC BO - CAMALEON ADAPTIVE BRAIN** 🏆🔥💎\n\n"
        "• *Cérebro autónomo que estuda e adapta-se à forma da mesa em tempo real*\n"
        "• *Gestão cirúrgica: Entrada + Máximo de 1 Gale (G1)*\n"
        "• *Blindagem total e automática no Empate (T)*\n\n"
        "📜 **Envia o fluxo de resultados para o Camaleão caçar as melhores oportunidades!**"
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
        "📊 **Relatório de Desempenho (Camaleão Adaptativo):** 📈\n\n"
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
                    f"Aposta principal devolvida pela mesa. Camaleão a reanalisar a forma da mesa...", 
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
                    f"Saiu `{resultado_real}` com leitura adaptativa perfeita!", 
                    parse_mode="Markdown"
                )
                continue
                
            else:
                # Gestão rigorosa restrita estritamente a MÁXIMO DE 1 GALE (G1)
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
                        f"🛑 Limite atingido. Camaleão em silêncio à espera de nova tendência...", 
                        parse_mode="Markdown"
                    )
                    continue

    if sessao['cor_alvo'] is None:
        sugestao = cerebro_camaleao_adaptativo(sessao['history'])
        
        if sugestao is None:
            resposta = (
                f"🧠 **Camaleon Adaptive Brain**\n"
                f"🛡️ *Mesa instável ou em transição de forma. Cérebro em silêncio tático à espera de padrão limpo...*"
            )
        else:
            sessao['cor_alvo'] = sugestao
            sessao['fase_gale'] = 0
            cor_texto = "AZUL 🔵" if sugestao == 'A' else "VERMELHO 🔴"
            resposta = (
                f"🧠 **ANÁLISE CAMALEÃO VALIDADA** 🎲\n"
                f"🎯 **MESA LIDA COM SUCESSO!**\n"
                f"👉 **Entrar no {cor_texto} + Proteger no T**"
            )
            
        bot.reply_to(message, resposta, parse_mode="Markdown")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()
