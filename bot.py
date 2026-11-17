import os
from flask import Flask, request
import telebot

# --- AS TUA CONFIGURAÇÕES DIRETAS (SEM DESCULPAS) ---
TOKEN = "AQUI_O_TEU_TOKEN_DO_BOTFATHER"
RENDER_URL = "https://o-teu-servico.onrender.com"  # Ex: https://bot-bacbo.onrender.com (sem barra no fim)
# ----------------------------------------------------

bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

# Estado Global da Sessão (Banca Inicial de 30€)
banca_inicial = 30.0
banca_atual = 30.0
stats = {
    "wins_cor": 0,
    "wins_empate": 0,
    "losses": 0,
    "total_operacoes": 0
}

# Histórico da mesa (guarda 'A', 'V', 'T')
historico_mesa = []

def cerebro_cirurgico_20_1(hist):
    """
    Cérebro de Alta Precisão (Foco: 20 Wins / Max 1 Loss).
    Focado estritamente em exaustão extrema e desequilíbrios profundos.
    """
    puros = [x for x in hist if x in ['A', 'V']]
    if len(puros) < 20:
        return f"⏳ A calibrar o Cérebro Cirúrgico... ({len(puros)}/20 rondas)."

    # Gatilho de Exaustão Extrema (7 ou mais seguidos -> Inversão)
    ultimos = puros[-7:]
    if all(x == ultimos[0] for x in ultimos):
        tendencia = ultimos[0]
        sinal = 'V' if tendencia == 'A' else 'A'
        nome_sinal = 'VERMELHO' if sinal == 'V' else 'AZUL'
        return f"🔥 [ALTA PRECISÃO] EXAUSTÃO DETETADA ({len(ultimos)} seguidos)!\n👉 ENTRAR COM FORÇA EM: **{nome_sinal}** (3€/1€ + G1 6€/1€)"

    # Gatilho de Desequilíbrio Estrutural (15+ numa cor em 20 rondas)
    bloco = puros[-20:]
    azuis = bloco.count('A')
    vermelhos = bloco.count('V')

    if azuis >= 15:
        return "⚠️ [ALTA PRECISÃO] DESEQUILÍBRIO SEVERO! 15+ Azuis em 20 rondas.\n👉 ENTRAR NA COR OPOSTA: **VERMELHO (V)**"
    elif vermelhos >= 15:
        return "⚠️ [ALTA PRECISÃO] DESEQUILÍBRIO SEVERO! 15+ Vermelhos em 20 rondas.\n👉 ENTRAR NA COR OPOSTA: **AZUL (A)**"

    return "🛡️ Mesa em zona de silêncio. Aguardar padrão limpo."

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 
        "🤖 **Cérebro Cirúrgico (Objetivo 20/1) Ativo, Zé!**\n\n"
        "Comandos disponíveis:\n"
        "• Envia **A**, **V** ou **T** para alimentar o histórico.\n"
        "• Envia /stats para ver o saldo, wins, empates e losses.\n"
        "• Envia /reset para reiniciar a sessão.",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['stats'])
def send_stats(message):
    lucro_prejuizo = banca_atual - banca_inicial
    sinal_lucro = "+" if lucro_prejuizo >= 0 else ""
    
    texto = (
        f"📊 **ESTATÍSTICAS DA SESSÃO (FOCO 20/1)** 📊\n\n"
        f"🟢 **Wins na Cor:** {stats['wins_cor']}\n"
        f"🟡 **Wins de Empate (T):** {stats['wins_empate']}\n"
        f"🔴 **Losses Finais (Após G1):** {stats['losses']}\n"
        f"🎯 **Total de Operações:** {stats['total_operacoes']}\n\n"
        f"💰 **Banca Inicial:** {banca_inicial:.2f}€\n"
        f"💵 **Banca Atual:** {banca_atual:.2f}€\n"
        f"📈 **Lucro/Prejuízo:** {sinal_lucro}{lucro_prejuizo:.2f}€"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=['reset'])
def reset_session(message):
    global banca_atual, historico_mesa, stats
    banca_atual = banca_inicial
    historico_mesa.clear()
    stats = {"wins_cor": 0, "wins_empate": 0, "losses": 0, "total_operacoes": 0}
    bot.reply_to(message, "🔄 Sessão reiniciada do zero! Histórico limpo.")

@bot.message_handler(func=lambda message: True)
def receber_jogada(message):
    global banca_atual, stats
    texto_msg = message.text.strip().upper()
    
    if texto_msg == 'WIN':
        stats['wins_cor'] += 1
        stats['total_operacoes'] += 1
        banca_atual += 1.0  # Lucro limpo do G1 na cor (+1€)
        bot.reply_to(message, f"✅ Registado: **WIN**! Banca atual: {banca_atual:.2f}€", parse_mode="Markdown")
        return
        
    if texto_msg == 'LOSS':
        stats['losses'] += 1
        stats['total_operacoes'] += 1
        banca_atual -= 11.0 # Prejuízo total do G1 falhado (-4€ principal + -7€ G1)
        
        aviso_alerta = f"❌ Registado: **LOSS TOTAL**! Banca atual: {banca_atual:.2f}€"
        if stats['losses'] >= 2:
            aviso_alerta += "\n\n🚨 **ATENÇÃO ZÉ! Atingiste o limite máximo de losses planeados! Cerra a mesa e respira!**"
            
        bot.reply_to(message, aviso_alerta, parse_mode="Markdown")
        return

    for char in texto_msg:
        if char in ['A', 'V', 'T']:
            historico_mesa.append(char)
            if char == 'T':
                stats['wins_empate'] += 1
                stats['total_operacoes'] += 1
                banca_atual += 3.0 # Lucro limpo seguro do empate no G1

    analise = cerebro_cirurgico_20_1(historico_mesa)
    
    resposta = (
        f"📝 **Histórico atualizado** ({len(historico_mesa)} rondas registadas).\n\n"
        f"{analise}"
    )
    bot.reply_to(message, resposta, parse_mode="Markdown")

@server.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@server.route("/")
def index():
    return "Cérebro Cirúrgico 20/1 Online e Operacional, Zé!", 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
    server.run(host="0.0.0.0", port=int(os.getenv('PORT', 5000)))
