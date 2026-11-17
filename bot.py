import os
from flask import Flask, request
import telebot

# Configurações do Bot
TOKEN = os.getenv("TELEGRAM_TOKEN", "8922303337:AAGiqzCVesRtMgy1mIR1vK3hF7SW9wsONM0")
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
    Só dispara gatilhos blindados baseados em exaustão extrema e desequilíbrios pesados.
    """
    # Filtra apenas Azul e Vermelho para calcular a tendência pura
    puros = [x for x in hist if x in ['A', 'V']]
    if len(puros) < 20:
        return f"⏳ A calibrar o Cérebro Cirúrgico... ({len(puros)}/20 rondas necessárias para análise profunda)."

    # 1. Gatilho de Exaustão Extrema (Ex: 7 ou mais repetidos seguidos -> Entrar na inversão)
    ultimos = puros[-7:]
    if all(x == ultimos[0] for x in ultimos):
        tendencia = ultimos[0]
        sinal = 'V' if tendencia == 'A' else 'A'
        nome_sinal = 'VERMELHO' if sinal == 'V' else 'AZUL'
        return f"🔥 [ALTA PRECISÃO] EXAUSTÃO DETETADA ({len(ultimos)} seguidos)!\n👉 ENTRAR COM FORÇA EM: **{nome_sinal}** (3€/1€ + G1 6€/1€)"

    # 2. Gatilho de Desequilíbrio Estrutural nas últimas 20 rondas
    bloco = puros[-20:]
    azuis = bloco.count('A')
    vermelhos = bloco.count('V')

    if azuis >= 15:
        return "⚠️ [ALTA PRECISÃO] DESEQUILÍBRIO SEVERO! 15+ Azuis em 20 rondas.\n👉 ENTRAR NA COR OPOSTA: **VERMELHO (V)**"
    elif vermelhos >= 15:
        return "⚠️ [ALTA PRECISÃO] DESEQUILÍBRIO SEVERO! 15+ Vermelhos em 20 rondas.\n👉 ENTRAR NA COR OPOSTA: **AZUL (A)**"

    return "🛡️ Mesa em zona de silêncio do Cérebro. Aguardar padrão limpo (Sem risco desnecessário)."

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 
        "🤖 **Cérebro Cirúrgico (Objetivo 20/1) Ativo, Zé!**\n\n"
        "Comandos disponíveis:\n"
        "• Envia **A**, **V** ou **T** para alimentar o histórico.\n"
        "• Envia /stats para ver o ponto da situação das wins, empates e banca.\n"
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
    bot.reply_to(message, "🔄 Sessão reiniciada! Histórico limpo, vamos à caça dos greens.")

@bot.message_handler(func=lambda message: True)
def receber_jogada(message):
    global banca_atual, stats
    texto_msg = message.text.strip().upper()
    
    # Se o utilizador mandar o resultado direto de uma operação fechada:
    if texto_msg == 'WIN':
        stats['wins_cor'] += 1
        stats['total_operacoes'] += 1
        banca_atual += 1.0  # Lucro limpo ajustado do G1 na cor (+1€)
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

    # Registo de letras (A, V ou T)
    for char in texto_msg:
        if char in ['A', 'V', 'T']:
            historico_mesa.append(char)
            
            # Se saiu Empate (T), contabiliza como vitória do empate automaticamente
            if char == 'T':
                stats['wins_empate'] += 1
                stats['total_operacoes'] += 1
                banca_atual += 3.0 # Lucro limpo seguro do empate no G1

    # Corre o cérebro cirúrgico atualizado
    analise = cerebro_cirurgico_20_1(historico_mesa)
    
    resposta = (
        f"📝 **Histórico atualizado** ({len(historico_mesa)} rondas registadas).\n\n"
        f"{analise}"
    )
    bot.reply_to(message, resposta, parse_mode="Markdown")

# Configuração do Webhook para o Render
@server.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='O_TEU_LINK_DO_RENDER/' + TOKEN)
    return "Cérebro Cirúrgico 20/1 Ativo e a Funcionar, Zé!", 200

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.getenv('PORT', 5000)))
